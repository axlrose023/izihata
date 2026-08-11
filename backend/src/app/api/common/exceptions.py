from dataclasses import dataclass


@dataclass(slots=True)
class ApplicationError(Exception):
    detail: str
    status_code: int
    code: str = "request_failed"
    headers: dict[str, str] | None = None


class NotFoundError(ApplicationError):
    def __init__(self, detail: str, code: str = "not_found"):
        super().__init__(detail=detail, status_code=404, code=code)


class ConflictError(ApplicationError):
    def __init__(self, detail: str, code: str = "conflict"):
        super().__init__(detail=detail, status_code=409, code=code)


class UnauthorizedError(ApplicationError):
    def __init__(
        self,
        detail: str = "Could not validate credentials",
        code: str = "unauthorized",
    ):
        super().__init__(detail=detail, status_code=401, code=code)


class UnprocessableError(ApplicationError):
    def __init__(self, detail: str, code: str = "unprocessable"):
        super().__init__(detail=detail, status_code=422, code=code)


class TooManyRequestsError(ApplicationError):
    def __init__(self, retry_after: int):
        super().__init__(
            detail="Too many requests",
            status_code=429,
            code="rate_limit_exceeded",
            headers={"Retry-After": str(max(retry_after, 1))},
        )


class ServiceUnavailableError(ApplicationError):
    def __init__(
        self,
        detail: str = "Service temporarily unavailable",
        code: str = "service_unavailable",
    ):
        super().__init__(detail=detail, status_code=503, code=code)
