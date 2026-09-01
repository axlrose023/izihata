import pytest
from httpx import AsyncClient

from app.api.common.visitor import VISITOR_COOKIE


@pytest.mark.asyncio
class TestVisitorActivity:
    endpoint = "/api/v1/activity/visits"
    admin_endpoint = "/api/v1/admin/activity/visitors"

    async def test_first_visit_issues_a_cookie(self, client: AsyncClient):
        response = await client.post(self.endpoint, json={"path": "/catalog"})

        assert response.status_code == 204, response.text
        assert VISITOR_COOKIE in response.cookies
        client.cookies.clear()

    async def test_repeat_visits_accumulate_on_one_visitor(
        self,
        client: AsyncClient,
        authenticated_user,
    ):
        first = await client.post(self.endpoint, json={"path": "/"})
        key = first.cookies[VISITOR_COOKIE]
        client.cookies.set(VISITOR_COOKIE, key)
        await client.post(self.endpoint, json={"path": "/catalog"})

        listing = await client.get(
            self.admin_endpoint,
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert listing.status_code == 200, listing.text
        visitor = listing.json()["items"][0]
        assert visitor["page_views"] >= 2
        assert visitor["last_path"] == "/catalog"
        assert visitor["is_registered"] is False
        client.cookies.clear()

    async def test_lead_attaches_contact_details_to_the_visitor(
        self,
        client: AsyncClient,
        authenticated_user,
    ):
        visit = await client.post(self.endpoint, json={"path": "/"})
        key = visit.cookies[VISITOR_COOKIE]

        client.cookies.set(VISITOR_COOKIE, key)
        lead = await client.post(
            "/api/v1/leads",
            json={
                "type": "callback",
                "name": "Активний Гість",
                "phone": "+380671110022",
            },
        )
        assert lead.status_code == 201, lead.text

        listing = await client.get(
            self.admin_endpoint,
            params={"search": "+380671110022"},
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert listing.status_code == 200, listing.text
        items = listing.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Активний Гість"
        assert items[0]["leads_count"] == 1
        client.cookies.clear()

    async def test_unknown_cookie_is_ignored(self, client: AsyncClient):
        client.cookies.set(VISITOR_COOKIE, "not-a-uuid")
        response = await client.post(self.endpoint, json={"path": "/"})

        assert response.status_code == 204
        client.cookies.clear()

    async def test_listing_requires_staff_authentication(self, client: AsyncClient):
        response = await client.get(self.admin_endpoint)

        assert response.status_code == 401
