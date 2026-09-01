from uuid import UUID

from fastapi import Request

VISITOR_COOKIE = "izihata_visitor"
VISITOR_COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def visitor_key_from(request: Request) -> UUID | None:
    """Read the first-party visitor cookie, ignoring anything malformed."""
    raw = request.cookies.get(VISITOR_COOKIE)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None
