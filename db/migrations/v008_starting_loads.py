"""Remember manual starting loads separately from recorded performances."""
from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, func

REVISION = "008_starting_loads"


def define_table(metadata):
    return Table("recommendation_starting_loads", metadata,
        Column("context_key", String(64), primary_key=True),
        Column("loads_json", Text, nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False,
               server_default=func.current_timestamp()),
    )


def apply(connection):
    define_table(MetaData()).create(connection)
