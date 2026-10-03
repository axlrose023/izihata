import json

import pytest

from app.services.public_pages import PublicPage, image_preload, render_page


@pytest.mark.parametrize(
    ("path", "module"),
    [
        ("/catalog", "catalog-page"),
        ("/catalog/lowvoltage", "catalog-page"),
        ("/products/example", "product-page"),
        ("/brands", "brand-pages"),
        ("/brands/hager", "brand-products-page"),
        ("/", "home-page"),
        ("/sections/energy", "section-page"),
    ],
)
def test_only_current_route_and_dependencies_are_preloaded(path, module):
    mapping = {
        name: [f"/assets/{name}.js", "/assets/shared.js"]
        for name in [
            "catalog-page",
            "product-page",
            "brand-pages",
            "brand-products-page",
            "home-page",
            "section-page",
        ]
    }
    template = (
        '<head><script id="public-route-preloads" type="application/json">'
        + json.dumps(mapping)
        + '</script></head><div id="root"></div>'
    )
    html = render_page(template, PublicPage("Page"), "https://example.com" + path)
    assert f'href="/assets/{module}.js"' in html
    assert html.count('href="/assets/shared.js"') == 1
    assert 'id="public-route-preloads"' not in html
    assert html.count('rel="modulepreload"') == 2


def test_preload_uses_same_responsive_candidate_range_as_product_visual():
    variants = {
        str(width): f"https://example.com/{width}.webp"
        for width in [80, 160, 320, 640, 960, 1600]
    }
    html = image_preload(
        "https://example.com/original.png", variants, "(max-width: 820px) 50vw, 400px"
    )
    assert 'href="https://example.com/960.webp"' in html
    assert "1600.webp" not in html
    assert (
        'imagesrcset="' in html
        and 'imagesizes="(max-width: 820px) 50vw, 400px"' in html
    )
    assert image_preload(None, {}, "400px") == ""
    assert "imagesrcset" not in image_preload("/original.png", {}, "400px")
    assert 'href="https://example.com/1600.webp"' in image_preload(
        "/original.png", variants, "50vw", maximum_width=1600
    )


def test_invalid_template_map_does_not_break_html_or_load_foreign_assets():
    for mapping in [
        "null",
        '"broken"',
        "{bad",
        '{"catalog-page":null}',
        '{"catalog-page":["https://evil.example/x.js", "/assets/valid.js", {}]}',
    ]:
        template = (
            '<head><script id="public-route-preloads" type="application/json">'
            + mapping
            + '</script></head><div id="root"></div>'
        )
        html = render_page(template, PublicPage("Page"), "https://example.com/catalog")
        assert "<h1>Page</h1>" in html
        assert "evil.example" not in html
