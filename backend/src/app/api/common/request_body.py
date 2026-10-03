from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.common.limits import MAX_JSON_BYTES, MAX_MULTIPART_BYTES


class RequestBodyLimitMiddleware:
    """Bound the body before JSON/multipart parsing, including chunked uploads."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        limit = (
            MAX_MULTIPART_BYTES
            if headers.get("content-type", "").lower().startswith("multipart/form-data")
            else MAX_JSON_BYTES
        )

        async def reject() -> None:
            await JSONResponse(
                {
                    "code": "request_body_too_large",
                    "detail": "Request body exceeds the supported size",
                },
                status_code=413,
            )(scope, receive, send)

        try:
            length = int(headers.get("content-length", "0"))
        except ValueError:
            length = 0
        if length > limit:
            await reject()
            return
        buffer = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(buffer) + len(chunk) > limit:
                await reject()
                return
            buffer.extend(chunk)
            if not message.get("more_body", False):
                break
        payload = bytes(buffer)
        del buffer
        consumed = False

        async def replay() -> Message:
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {"type": "http.request", "body": payload, "more_body": False}

        await self.app(scope, replay, send)
