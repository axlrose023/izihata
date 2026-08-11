import re

_PHONE_SEPARATORS = re.compile(r"[\s()-]+")
_PHONE_PATTERN = re.compile(r"\+[1-9]\d{7,14}")


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
