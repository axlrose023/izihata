import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestElectricalAdvisors:
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
        assert autonomy.status_code == 200, autonomy.text
        assert autonomy.json()["required_energy_wh"] == "400.00"
        assert autonomy.json()["recommended_inverter_power_w"] == "125.00"

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
