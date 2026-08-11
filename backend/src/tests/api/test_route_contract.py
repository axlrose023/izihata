from fastapi import FastAPI


def test_openapi_contains_only_confirmed_business_routes(app: FastAPI):
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method != "parameters"
    }
    assert actual == {
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/refresh"),
        ("GET", "/api/v1/catalog/categories"),
        ("GET", "/api/v1/catalog/products"),
        ("GET", "/api/v1/catalog/products/{product_slug}"),
        ("GET", "/api/v1/catalog/reviews/featured"),
        ("POST", "/api/v1/checkout/quote"),
        ("GET", "/api/v1/delivery/cities"),
        ("GET", "/api/v1/delivery/points"),
        ("POST", "/api/v1/orders"),
        ("POST", "/api/v1/leads"),
        ("GET", "/api/v1/admin/dashboard"),
        ("POST", "/api/v1/admin/catalog/products"),
        ("PATCH", "/api/v1/admin/catalog/products/{product_id}"),
        ("GET", "/api/v1/admin/orders"),
        ("PATCH", "/api/v1/admin/orders/{order_id}/status"),
        ("GET", "/api/v1/admin/leads"),
        ("PATCH", "/api/v1/admin/leads/{lead_id}/status"),
    }


def test_openapi_exposes_frontend_session_and_bulk_restore_contract(app: FastAPI):
    paths = app.openapi()["paths"]
    login = paths["/api/v1/auth/login"]["post"]
    refresh = paths["/api/v1/auth/refresh"]["post"]
    logout = paths["/api/v1/auth/logout"]["post"]
    product_list = paths["/api/v1/catalog/products"]["get"]
    parameters = {
        parameter["name"]: parameter for parameter in product_list["parameters"]
    }

    assert "204" in logout["responses"]
    assert "requestBody" in login
    assert "requestBody" not in refresh
    assert "requestBody" not in logout
    assert refresh["parameters"][0]["in"] == "cookie"
    assert refresh["parameters"][0]["name"] == "izihata_refresh"
    assert parameters["id"]["schema"]["type"] == "array"
    assert parameters["id"]["schema"]["maxItems"] == 100
