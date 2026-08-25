import re
from urllib.parse import urlsplit

from app.api.common.utils import normalize_text

_SKU_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9._/-]*")
_SLUG_SEPARATORS = re.compile(r"[._/]+")
_REPEATED_DASHES = re.compile(r"-+")
_EMAIL_PATTERN = re.compile(
    r"(?=.{3,254}$)[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


def normalize_sku(value: object) -> str:
    sku = normalize_text(value).upper()
    if _SKU_PATTERN.fullmatch(sku) is None:
        raise ValueError(
            "SKU may contain only Latin letters, digits, '.', '_', '/' and '-'"
        )
    return sku


def product_slug_from_sku(sku: str) -> str:
    slug = _SLUG_SEPARATORS.sub("-", sku.lower())
    return _REPEATED_DASHES.sub("-", slug).strip("-")


def normalize_image_url(value: object | None) -> str | None:
    if value is None:
        return None
    image_url = normalize_text(value)
    if any(character.isspace() for character in image_url) or "\\" in image_url:
        raise ValueError("Image URL cannot contain spaces or backslashes")
    if image_url.startswith("/") and not image_url.startswith("//"):
        return image_url

    parsed = urlsplit(image_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "Image URL must be an absolute HTTP(S) URL or an absolute path"
        )
    return image_url


def normalize_email(value: object) -> str:
    email = normalize_text(value).lower()
    if _EMAIL_PATTERN.fullmatch(email) is None:
        raise ValueError("Email address is invalid")
    return email


def normalize_product_specs(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("Specifications must be an object")

    normalized: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = normalize_text(raw_key)
        spec_value = normalize_text(raw_value)
        if not key or not spec_value:
            raise ValueError("Specification names and values cannot be empty")
        if len(key) > 120 or len(spec_value) > 160:
            raise ValueError("Specification name or value is too long")
        if key in normalized:
            raise ValueError("Specification names must be unique")
        normalized[key] = spec_value
    return normalized
