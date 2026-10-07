"""Small HTML error responses for storefront requests without loading the app."""

from fastapi.responses import HTMLResponse

PUBLIC_PAGE_ROUTE_NAME = "public_catalog_page"


def public_error_response(
    status_code: int, headers: dict[str, str] | None = None
) -> HTMLResponse:
    title, message = {
        429: ("Забагато запитів", "Зачекайте трохи та оновіть сторінку."),
        503: (
            "Сайт тимчасово недоступний",
            "Спробуйте відкрити сторінку трохи пізніше.",
        ),
    }.get(
        status_code, ("Помилка відкриття сторінки", "Спробуйте ще раз трохи пізніше.")
    )
    return HTMLResponse(
        '<!doctype html><html lang="uk"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex">'
        f"<title>{title} | IZI HATA</title>"
        "<style>body{margin:0;background:#f3f4f6;color:#12161b;font:16px/1.5 system-ui;"
        "min-height:100dvh;display:grid;place-items:center}main{box-sizing:border-box;"
        "width:min(100%,32rem);padding:24px}h1{font-size:1.6rem}a{display:inline-block;"
        "background:#f5a900;color:#12161b;padding:12px 20px;border-radius:6px;"
        "text-decoration:none;font-weight:600}</style></head>"
        f"<body><main><h1>{title}</h1><p>{message}</p>"
        '<a href="">Оновити сторінку</a></main></body></html>',
        status_code=status_code,
        headers={**(headers or {}), "Cache-Control": "no-store"},
    )
