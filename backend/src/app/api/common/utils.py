import re
from urllib.parse import urlsplit

_PHONE_SEPARATORS = re.compile(r"[\s()-]+")
_PHONE_PATTERN = re.compile(r"\+[1-9]\d{7,14}")
_EMAIL_PATTERN = re.compile(
    r"(?=.{3,254}$)[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Value must be a string")
    return " ".join(value.split())


def normalize_optional_text(value: object | None) -> str | None:
    return normalize_text(value) if value is not None else None


def normalize_phone(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Phone number must be a string")
    normalized = _PHONE_SEPARATORS.sub("", value)
    if normalized.startswith("0") and len(normalized) == 10:
        normalized = f"+38{normalized}"
    elif normalized.startswith("380") and len(normalized) == 12:
        normalized = f"+{normalized}"
    if _PHONE_PATTERN.fullmatch(normalized) is None:
        raise ValueError("Phone number must use international or Ukrainian format")
    return normalized


def normalize_email(value: object) -> str:
    email = normalize_text(value).lower()
    if _EMAIL_PATTERN.fullmatch(email) is None:
        raise ValueError("Email address is invalid")
    return email


def normalize_resource_url(value: object | None) -> str | None:
    if value is None:
        return None
    resource_url = normalize_text(value)
    if any(character.isspace() for character in resource_url) or "\\" in resource_url:
        raise ValueError("URL cannot contain spaces or backslashes")
    if resource_url.startswith("/") and not resource_url.startswith("//"):
        return resource_url

    parsed = urlsplit(resource_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute HTTP(S) URL or an absolute path")
    return resource_url
