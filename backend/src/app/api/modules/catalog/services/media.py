import asyncio
import hashlib
import io
import os
import tempfile
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

from app.api.common.exceptions import UnprocessableError

MEDIA_URL_PREFIX = "/api/v1/media"
# The browser downscales pictures before sending them, so anything arriving
# here is small. The cap is generous enough for a client that could not decode
# the file and had to send the original.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
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

        return await asyncio.to_thread(self._store_payload, payload)

    def _store_payload(self, payload: bytes) -> str:
        try:
            with Image.open(io.BytesIO(payload)) as image:
                extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}.get(
                    image.format or ""
                )
                if extension is None or image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Unsupported image format or dimensions")
                image.verify()
            with Image.open(io.BytesIO(payload)) as image:
                image.load()
        except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
            raise UnprocessableError(
                "Invalid image or image exceeds 20 million pixels",
                code="invalid_media_image",
            ) from exc

        # Content addressing keeps re-uploads idempotent and names unguessable.
        name = f"{hashlib.sha256(payload).hexdigest()[:32]}{extension}"
        self._media_root.mkdir(parents=True, exist_ok=True)
        destination = self._media_root / name
        if not destination.exists():
            with tempfile.NamedTemporaryFile(
                dir=self._media_root, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                try:
                    temporary.write(payload)
                    temporary.close()
                    os.replace(temporary_path, destination)
                finally:
                    temporary_path.unlink(missing_ok=True)
        return f"{MEDIA_URL_PREFIX}/{name}"
