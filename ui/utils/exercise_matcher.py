import re


def normalize(name: str) -> str:
    """
    Normalize exercise names for matching.
    """
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    return name.strip()
