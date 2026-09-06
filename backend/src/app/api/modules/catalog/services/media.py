import hashlib
from pathlib import Path

from fastapi import UploadFile

from app.api.common.exceptions import UnprocessableError

MEDIA_URL_PREFIX = "/api/v1/media"
# The browser downscales pictures before sending them, so anything arriving
# here is small. The cap is generous enough for a client that could not decode
# the file and had to send the original.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
# SVG is deliberately excluded: it is served from our own origin and can carry
# scripts, so it would be a stored-XSS vector.
ALLOWED_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


class MediaStorageService:
    """Stores staff uploads on a persistent volume served by the API."""

    def __init__(self, media_root: Path):
        self._media_root = media_root

    async def store(self, upload: UploadFile) -> str:
        extension = ALLOWED_TYPES.get(upload.content_type or "")
        if extension is None:
            raise UnprocessableError(
                f"Unsupported image type '{upload.content_type or 'unknown'}'."
                " Use PNG, JPEG or WebP.",
                code="unsupported_media_type",
            )

        payload = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(payload) > MAX_UPLOAD_BYTES:
            raise UnprocessableError(
                "Image must be 8 MB or smaller",
                code="media_too_large",
            )
        if not payload:
            raise UnprocessableError("Image is empty", code="media_empty")

        # Content addressing keeps re-uploads idempotent and names unguessable.
        name = f"{hashlib.sha256(payload).hexdigest()[:32]}{extension}"
        self._media_root.mkdir(parents=True, exist_ok=True)
        destination = self._media_root / name
        if not destination.exists():
            destination.write_bytes(payload)
        return f"{MEDIA_URL_PREFIX}/{name}"
