import asyncio

import pytest

from app.api.common.exceptions import ServiceUnavailableError
from app.api.modules.delivery.enums import NOVA_POSHTA_LOCKER_TYPE_REF
from app.api.modules.delivery.utils import (
    CitySearchIndex,
    PointSearchIndex,
    bounded_lookup,
    match_points,
    normalized_address,
)
from app.clients.nova_poshta import NovaPoshtaCity, NovaPoshtaPoint


def test_city_matching_prefers_exact_names_and_supports_aliases():
    cities = (
        NovaPoshtaCity("suburb", "Київське", "с. Київське"),
        NovaPoshtaCity("capital", "Київ", "м. Київ, Київська обл.", ("Киев",)),
    )
    index = CitySearchIndex(cities)
    assert index.search("  КИЕВ  ")[0].ref == "capital"
    assert index.search("Київ")[0].ref == "capital"
    index.search("Київ").clear()
    assert index.search("Київ")[0].ref == "capital"
    assert index.search("") == []
    assert index.search("неіснуюче") == []
    assert normalized_address("  вул.  Осокорська, 2А ") == "вул осокорська 2а"


@pytest.mark.asyncio
async def test_lookup_deadline_becomes_a_public_service_error():
    with pytest.raises(ServiceUnavailableError) as error:
        await bounded_lookup(asyncio.sleep(1), seconds=0.01)
    assert error.value.code == "delivery_provider_unavailable"


def test_point_matching_filters_kind_before_pagination_and_skips_forbidden_points():
    def branch(number, **kwargs):
        return NovaPoshtaPoint(
            str(number),
            f"Відділення №{number}: Осокорська, {number}",
            f"Осокорська, {number}",
            str(number),
            "branch",
            **kwargs,
        )

    points = (
        NovaPoshtaPoint(
            "locker", "Поштомат №390", "", "390", NOVA_POSHTA_LOCKER_TYPE_REF
        ),
        branch(0, selectable=False),
        *(branch(number) for number in range(1, 101)),
    )
    assert [item.number for item in match_points(points, "", None, 2, 50)] == [
        str(number) for number in range(51, 101)
    ]
    assert [item.number for item in match_points(points, "39", None, 1, 50)] == ["39"]
    assert len(match_points(points, "осокорська", None, 1, 50)) == 50
    assert len(match_points(points, "", NOVA_POSHTA_LOCKER_TYPE_REF, 1, 50)) == 1


def test_point_index_keeps_cities_separate_and_matches_numbers_and_streets():
    points = (
        NovaPoshtaPoint(
            "a", "Відділення №1", "вул. Миру, 2", "1", "branch", city_ref="a"
        ),
        NovaPoshtaPoint(
            "b", "Відділення №1", "вул. Миру, 3", "1", "branch", city_ref="b"
        ),
        NovaPoshtaPoint(
            "c", "Відділення №11", "вул. Миру, 4", "11", "branch", city_ref="a"
        ),
    )
    index = PointSearchIndex(points)
    assert [item.ref for item in index.search("a", "1", None, 1, 50)] == ["a"]
    assert [item.ref for item in index.search("b", " 1 ", None, 1, 50)] == ["b"]
    assert [item.ref for item in index.search("a", "МИРУ", None, 1, 1)] == ["a"]
    assert [item.ref for item in index.search("a", "МИРУ", None, 2, 1)] == ["c"]
    assert index.search("a", "2", None, 1, 50) == []
    assert index.search("missing", "1", None, 1, 50) is None
