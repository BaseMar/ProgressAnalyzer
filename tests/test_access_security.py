"""Reproduce Supabase default grants and prove the API roles lose access without data loss."""

import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from data_manager import DataManager
from db.access_security import API_ROLES, APPLICATION_TABLES
from db.bootstrap import bootstrap_database
from db.migrate import ledger, migrate
from db.migrations import v010_application_access_security


@pytest.fixture
def exposed_database():
    value = os.getenv("TEST_POSTGRES_URL")
    if not value:
        pytest.skip("Set TEST_POSTGRES_URL for PostgreSQL API privilege acceptance")
    admin = create_engine(value, isolation_level="AUTOCOMMIT")
    name = "access_security_" + uuid4().hex
    created_roles = []
    engine = None
    try:
        with admin.connect() as connection:
            for role in API_ROLES:
                if not connection.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
                ).scalar():
                    connection.exec_driver_sql(f'CREATE ROLE "{role}" NOLOGIN')
                    created_roles.append(role)
            connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
        engine = create_engine(admin.url.set(database=name))
        bootstrap_database(engine, demo=True)
        with engine.begin() as connection:
            connection.execute(
                ledger.delete().where(
                    ledger.c.revision == v010_application_access_security.REVISION
                )
            )
            for table in sorted(APPLICATION_TABLES):
                connection.exec_driver_sql(
                    f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY'
                )
            for objects in ("TABLES", "SEQUENCES"):
                connection.exec_driver_sql(
                    f"GRANT ALL ON ALL {objects} IN SCHEMA public TO PUBLIC, anon, authenticated, service_role"
                )
                connection.exec_driver_sql(
                    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON {objects} "
                    "TO PUBLIC, anon, authenticated, service_role"
                )
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with admin.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
            for role in reversed(created_roles):
                connection.exec_driver_sql(f'DROP ROLE "{role}"')
        admin.dispose()


def snapshot(engine):
    with engine.connect() as connection:
        return {
            table: sorted(
                json.dumps(tuple(row), default=str)
                for row in connection.exec_driver_sql(f'SELECT * FROM "{table}"')
            )
            for table in sorted(APPLICATION_TABLES - {"schema_migrations"})
        }


def assert_closed(engine):
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
            SELECT c.relname,c.relrowsecurity,
                   has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE') AS anon,
                   has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE') AS signed_in,
                   has_table_privilege('service_role',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE') AS service
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname
        """)
        ).all()
        assert {row[0] for row in rows} == APPLICATION_TABLES
        assert all(
            rls and not anon and not signed_in and not service
            for _, rls, anon, signed_in, service in rows
        )
        assert not connection.execute(
            text("""
            SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind='S'
            AND CASE WHEN c.relkind='S'
                THEN has_sequence_privilege('anon',c.oid,'USAGE,SELECT,UPDATE') ELSE false END)
        """)
        ).scalar_one()
    for role in API_ROLES:
        with pytest.raises(DBAPIError) as denied, engine.begin() as connection:
            connection.exec_driver_sql(f'SET LOCAL ROLE "{role}"')
            connection.exec_driver_sql("SELECT * FROM public.training_plans")
        assert denied.value.orig.pgcode == "42501"


def test_migration_closes_api_roles_preserves_rows_and_keeps_backend_writes(exposed_database):
    engine = exposed_database
    before = snapshot(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE anon")
        assert connection.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM training_plans)"
        ).scalar_one()
    assert migrate(engine, apply=True) == [v010_application_access_security.REVISION]
    assert snapshot(engine) == before
    assert_closed(engine)
    assert len(DataManager(engine=engine).load_sets_ui()) == len(before["workout_sets"]) > 0
    assert DataManager(engine=engine).add_exercise("Chest Dip")


def test_later_migrations_recheck_existing_tables_and_new_defaults(exposed_database):
    engine = exposed_database
    migrate(engine, apply=True)
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE training_plans DISABLE ROW LEVEL SECURITY")
        connection.exec_driver_sql("GRANT SELECT ON training_plans TO anon")
    assert migrate(engine, apply=True) == []
    assert_closed(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE future_private_records (id SERIAL PRIMARY KEY, note TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO future_private_records (note) VALUES ('Not public')"
        )
        assert not connection.exec_driver_sql(
            "SELECT has_table_privilege('anon','future_private_records','SELECT')"
        ).scalar_one()
        assert not connection.exec_driver_sql(
            "SELECT has_sequence_privilege('anon','future_private_records_id_seq','USAGE')"
        ).scalar_one()


def test_security_ddl_rolls_back_with_the_migration_transaction(exposed_database):
    engine = exposed_database
    before = snapshot(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        v010_application_access_security.apply(connection)
        transaction.rollback()
    assert snapshot(engine) == before
    with engine.begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE anon")
        assert connection.exec_driver_sql("SELECT count(*) FROM training_plans").scalar_one() == 1


def test_sqlite_bootstrap_records_security_revision_without_postgres_ddl(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'local.sqlite3'}")
    try:
        result = bootstrap_database(engine, demo=True)
        assert result["migrations"][-1] == v010_application_access_security.REVISION
        assert len(inspect(engine).get_table_names()) == 20
        assert migrate(engine, apply=True) == []
        assert (
            len(DataManager(engine=engine).load_sets_ui()) == result["counts"]["workout_sets"] > 0
        )
    finally:
        engine.dispose()
