"""Shared bounded image downloads and Bunny S3 transport."""

import asyncio
import hashlib
import hmac
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote, urlparse

import httpx

MAX_IMAGE_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class BunnyS3Config:
    endpoint: str
    storage_zone: str
    password: str
    public_base_url: str

    def __post_init__(self) -> None:
        endpoint = urlparse(self.endpoint)
        public_url = urlparse(self.public_base_url)
        if endpoint.scheme != "https" or not endpoint.netloc:
            raise ValueError("Bunny S3 endpoint must be an absolute HTTPS URL")
        if public_url.scheme != "https" or not public_url.netloc:
            raise ValueError("Bunny public media URL must be an absolute HTTPS URL")
        if not self.storage_zone or not self.password:
            raise ValueError("Bunny Storage zone and password are required")


def s3_signature(
    *,
    config: BunnyS3Config,
    method: str,
    object_key: str,
    payload: bytes,
) -> tuple[str, dict[str, str]]:
    parsed = urlparse(config.endpoint)
    host = parsed.netloc
    canonical_uri = (
        "/"
        + quote(config.storage_zone, safe="")
        + "/"
        + quote(
            object_key,
            safe="/-_.~",
        )
    )
    timestamp = datetime.now(UTC)
    amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = timestamp.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(payload).hexdigest()
    canonical_headers = (
        f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    credential_scope = f"{date_stamp}/de/s3/aws4_request"
    canonical_request = "\n".join(
        (
            method,
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        )
    )
    string_to_sign = "\n".join(
        (
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        )
    )

    def sign(key: bytes, value: str) -> bytes:
        return hmac.new(key, value.encode(), hashlib.sha256).digest()

    signing_key = sign(
        sign(sign(sign(f"AWS4{config.password}".encode(), date_stamp), "de"), "s3"),
        "aws4_request",
    )
    signature = hmac.new(
        signing_key,
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={config.storage_zone}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return (
        f"{config.endpoint.rstrip('/')}{canonical_uri}",
        {
            "Authorization": authorization,
            "Host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        },
    )


async def download_image(client: httpx.AsyncClient, url: str) -> tuple[bytes, str]:
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise ValueError(f"Photo exceeds {MAX_IMAGE_BYTES // 1024 // 1024} MB")
            chunks.append(chunk)
        if not chunks:
            raise ValueError("Photo response is empty")
        return b"".join(chunks), response.headers.get("content-type", "image/webp")


async def object_exists(
    client: httpx.AsyncClient,
    config: BunnyS3Config,
    object_key: str,
) -> bool:
    url, headers = s3_signature(
        config=config,
        method="HEAD",
        object_key=object_key,
        payload=b"",
    )
    response = await client.head(url, headers=headers)
    if response.status_code == 404:
        return False
    response.raise_for_status()
    return True


async def put_object(
    client: httpx.AsyncClient,
    config: BunnyS3Config,
    object_key: str,
    content: bytes,
    content_type: str,
) -> None:
    url, headers = s3_signature(
        config=config,
        method="PUT",
        object_key=object_key,
        payload=content,
    )
    response = await client.put(
        url,
        content=content,
        headers={**headers, "Content-Type": content_type.split(";", 1)[0]},
    )
    response.raise_for_status()


async def with_retries[T](operation: Callable[[], Awaitable[T]]) -> T:
    for attempt in range(3):
        try:
            return await operation()
        except (httpx.HTTPError, ValueError):
            if attempt == 2:
                raise
            await asyncio.sleep(0.4 * (2**attempt))
    raise RuntimeError("Retry loop exhausted")
