"""Keep single-owner application tables inaccessible to public Data API roles."""

from sqlalchemy import inspect, text

APPLICATION_TABLES = frozenset(
    (
        "body_composition",
        "body_measurements",
        "exercise_history_load_settings",
        "exercise_muscle_map",
        "exercises",
        "recommendation_starting_loads",
        "schema_migrations",
        "training_plan_days",
        "training_plan_exercise_lineage",
        "training_plan_exercise_matches",
        "training_plan_exercises",
        "training_plan_progression",
        "training_plan_session_links",
        "training_plan_versions",
        "training_plans",
        "workout_exercises",
        "workout_sessions",
        "workout_set_classifications",
        "workout_set_loads",
        "workout_sets",
    )
)
API_ROLES = ("anon", "authenticated", "service_role")


def harden_application_access(connection):
    """Apply transactional PostgreSQL ACL/RLS changes without changing stored records.

    Only known application tables in the current schema and their sequences are
    touched. Future tables/sequences created by the migration role lose automatic
    public grants. SQLite has no external Data API and needs no equivalent DDL.
    """
    if connection.dialect.name != "postgresql":
        return
    schema, role, bypass = connection.execute(
        text("""
        SELECT current_schema(), current_user, rolsuper OR rolbypassrls
        FROM pg_roles WHERE rolname=current_user
    """)
    ).one()
    tables = sorted(APPLICATION_TABLES & set(inspect(connection).get_table_names(schema=schema)))
    if not tables:
        return
    if not bypass:
        owners = connection.execute(
            text("""
            SELECT c.relname,pg_get_userbyid(c.relowner) FROM pg_class c
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=:schema AND c.relkind IN ('r','p')
        """),
            {"schema": schema},
        ).all()
        if any(owner != role for name, owner in owners if name in tables):
            raise RuntimeError("The migration role must own the application tables or bypass RLS")
    existing_roles = set(
        connection.execute(
            text(
                "SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role')"
            )
        ).scalars()
    )
    quote = connection.dialect.identifier_preparer.quote
    targets = "PUBLIC" + "".join(", " + quote(name) for name in API_ROLES if name in existing_roles)
    for table in tables:
        qualified = quote(schema) + "." + quote(table)
        connection.exec_driver_sql(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY")
        connection.exec_driver_sql(f"REVOKE ALL PRIVILEGES ON TABLE {qualified} FROM {targets}")
    sequences = connection.execute(
        text("""
        SELECT DISTINCT s.relname,t.relname AS table_name FROM pg_class s
        JOIN pg_namespace n ON n.oid=s.relnamespace
        JOIN pg_depend d ON d.objid=s.oid AND d.classid='pg_class'::regclass
            AND d.refclassid='pg_class'::regclass AND d.deptype IN ('a','i')
        JOIN pg_class t ON t.oid=d.refobjid
        WHERE n.nspname=:schema AND s.relkind='S'
    """),
        {"schema": schema},
    ).all()
    for sequence, table in sequences:
        if table in tables:
            qualified = quote(schema) + "." + quote(sequence)
            connection.exec_driver_sql(
                f"REVOKE ALL PRIVILEGES ON SEQUENCE {qualified} FROM {targets}"
            )
    for kind in ("TABLES", "SEQUENCES"):
        connection.exec_driver_sql(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {quote(role)} IN SCHEMA {quote(schema)} "
            f"REVOKE ALL PRIVILEGES ON {kind} FROM {targets}"
        )
