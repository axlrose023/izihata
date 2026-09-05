from fastapi import FastAPI


def test_openapi_contains_only_confirmed_business_routes(app: FastAPI):
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method != "parameters"
    }
    assert actual == {
        ("POST", "/api/v1/activity/visits"),
        ("POST", "/api/v1/advisors/autonomy"),
        ("POST", "/api/v1/advisors/breaker"),
        ("POST", "/api/v1/advisors/cable-size"),
        ("POST", "/api/v1/advisors/led-power-supply"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/customer-auth/login"),
        ("POST", "/api/v1/customer-auth/logout"),
        ("POST", "/api/v1/customer-auth/refresh"),
        ("POST", "/api/v1/customer-auth/register"),
        ("GET", "/api/v1/catalog/categories"),
        ("GET", "/api/v1/catalog/sections"),
        ("GET", "/api/v1/catalog/products"),
        ("GET", "/api/v1/catalog/products/{product_slug}"),
        ("POST", "/api/v1/catalog/products/{product_slug}/reviews"),
        (
            "POST",
            "/api/v1/catalog/products/{product_slug}/stock-subscriptions",
        ),
        ("GET", "/api/v1/catalog/brands"),
        ("GET", "/api/v1/catalog/brands/{brand_slug}"),
        ("GET", "/api/v1/catalog/recommendations"),
        ("GET", "/api/v1/catalog/reviews/featured"),
        ("POST", "/api/v1/checkout/quote"),
        ("GET", "/api/v1/delivery/cities"),
        ("GET", "/api/v1/delivery/points"),
        ("GET", "/api/v1/custom-boards/portfolio"),
        ("POST", "/api/v1/custom-boards/estimate"),
        ("POST", "/api/v1/custom-boards/requests"),
        ("GET", "/api/v1/customer/me"),
        ("POST", "/api/v1/customer/company"),
        ("GET", "/api/v1/customer/orders"),
        ("POST", "/api/v1/orders"),
        ("POST", "/api/v1/leads"),
        ("GET", "/api/v1/admin/dashboard"),
        ("GET", "/api/v1/admin/custom-boards/requests"),
        ("PATCH", "/api/v1/admin/custom-boards/requests/{request_id}"),
        ("POST", "/api/v1/admin/custom-boards/portfolio"),
        ("PATCH", "/api/v1/admin/custom-boards/portfolio/{item_id}"),
        ("GET", "/api/v1/admin/customers/companies"),
        ("PATCH", "/api/v1/admin/customers/companies/{company_id}"),
        ("POST", "/api/v1/admin/catalog/media"),
        ("GET", "/api/v1/admin/catalog/brands"),
        ("PATCH", "/api/v1/admin/catalog/brands/{brand_id}"),
        ("GET", "/api/v1/admin/catalog/attributes"),
        ("POST", "/api/v1/admin/catalog/attributes"),
        ("GET", "/api/v1/admin/catalog/categories/{category_id}/attributes"),
        ("PUT", "/api/v1/admin/catalog/categories/{category_id}/attributes"),
        ("PATCH", "/api/v1/admin/catalog/categories/{category_id}/section"),
        ("GET", "/api/v1/admin/activity/visitors"),
        ("POST", "/api/v1/admin/catalog/products"),
        ("GET", "/api/v1/admin/catalog/products/{product_id}"),
        ("PATCH", "/api/v1/admin/catalog/products/{product_id}"),
        ("GET", "/api/v1/admin/catalog/reviews"),
        ("PATCH", "/api/v1/admin/catalog/reviews/{review_id}"),
        ("POST", "/api/v1/admin/catalog/sections"),
        ("PATCH", "/api/v1/admin/catalog/sections/{section_id}"),
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
