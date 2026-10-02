import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestElectricalAdvisors:
    async def test_combined_load_coordinates_cable_capacity_and_poles(
        self, client: AsyncClient
    ):
        response = await client.post(
            "/api/v1/advisors/load",
            json={"current_a": "15.2", "length_m": "20", "number_of_poles": 3},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["breaker"]["recommended_nominal_a"] == 20
        assert data["cable"]["recommended_cross_section_mm2"] == "2.5"
        assert (
            float(data["cable"]["current_capacity_a"])
            >= data["breaker"]["recommended_nominal_a"]
        )
        assert all(
            product["specs"].get("Полюси") == "3P"
            for product in data["breaker"]["products"]
        )

    async def test_advisors_do_not_share_checkout_rate_limit(self):
        from app.api.common.rate_limit import ADVISOR_RATE_LIMIT, QUOTE_RATE_LIMIT

        assert ADVISOR_RATE_LIMIT.scope != QUOTE_RATE_LIMIT.scope

    async def test_calculates_cable_size_and_returns_matching_products(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/advisors/cable-size",
            json={"power_w": "3000", "voltage_v": "230", "length_m": "10"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["recommended_cross_section_mm2"] == "1.5"
        assert any(product["sku"] == "AX-10013" for product in body["products"])
        assert body["reference_notice"]
        assert body["current_capacity_a"] == "16"
        assert body["requires_specialist"] is False

    @pytest.mark.parametrize("material", ["copper", "aluminum"])
    async def test_does_not_recommend_a_cable_outside_its_table(
        self, client: AsyncClient, material: str
    ):
        response = await client.post(
            "/api/v1/advisors/cable-size",
            json={
                "current_a": "200",
                "length_m": "20",
                "conductor_material": material,
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["recommended_cross_section_mm2"] is None
        assert body["current_capacity_a"] is None
        assert body["requires_specialist"] is True
        assert body["products"] == []

    async def test_calculates_breaker_and_detects_wire_limit_conflict(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/advisors/breaker",
            json={
                "power_w": "2500",
                "load_type": "resistive",
                "wiring_current_limit_a": "10",
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["recommended_nominal_a"] is None
        assert body["requires_specialist"] is True

    async def test_calculates_led_and_autonomy_reference_values(
        self,
        client: AsyncClient,
    ):
        led = await client.post(
            "/api/v1/advisors/led-power-supply",
            json={"length_m": "5", "watts_per_meter": "10"},
        )
        autonomy = await client.post(
            "/api/v1/advisors/autonomy",
            json={
                "load_w": "100",
                "hours": "4",
                "battery_voltage_v": "12",
            },
        )

        assert led.status_code == 200, led.text
        assert led.json()["load_w"] == "50.00"
        assert led.json()["recommended_power_w"] == "60.00"
        assert led.json()["products"] == []
        assert autonomy.status_code == 200, autonomy.text
        assert autonomy.json()["required_energy_wh"] == "400.00"
        assert autonomy.json()["recommended_inverter_power_w"] == "125.00"
        assert autonomy.json()["products"] == []

    async def test_rejects_ambiguous_electrical_load(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/advisors/cable-size",
            json={
                "power_w": "1000",
                "current_a": "5",
                "length_m": "10",
            },
        )

        assert response.status_code == 422

    async def test_matching_respects_material_and_breaker_curve(
        self, client: AsyncClient
    ):
        copper = await client.post(
            "/api/v1/advisors/cable-size",
            json={
                "current_a": "10",
                "length_m": "10",
                "conductor_material": "aluminum",
            },
        )
        assert copper.json()["products"] == []
        motor = await client.post(
            "/api/v1/advisors/breaker", json={"current_a": "10", "load_type": "motor"}
        )
        resistive = await client.post(
            "/api/v1/advisors/breaker",
            json={"current_a": "10", "load_type": "resistive"},
        )
        assert any(product["sku"] == "AX-10001" for product in motor.json()["products"])
        assert all(
            product["specs"].get("Характеристика") == "B"
            for product in resistive.json()["products"]
        )

    async def test_matches_supplier_keys_without_changing_stored_attributes(
        self, uow, product
    ):
        from sqlalchemy import select

        from app.api.modules.advisors.schema import BreakerRequest
        from app.api.modules.advisors.service import ElectricalAdvisorService
        from app.api.modules.catalog.models import ProductAttribute

        attributes = list(
            (
                await uow.session.scalars(
                    select(ProductAttribute).where(
                        ProductAttribute.product_id == product.id
                    )
                )
            ).all()
        )
        for attribute in attributes:
            if attribute.key == "Номінал":
                attribute.key = "Номінальний струм"
                attribute.value = "16 A"
            elif attribute.key == "Характеристика":
                attribute.key = "Характеристика спрацювання"
        await uow.session.flush()
        response = await ElectricalAdvisorService(uow).calculate_breaker(
            BreakerRequest(current_a="10", load_type="motor")
        )
        assert any(item.sku == product.sku for item in response.products)
