"""Close public Data API access while preserving the single owner's SQL connection."""

from db.access_security import harden_application_access

REVISION = "010_application_access_security"


def apply(connection):
    harden_application_access(connection)
