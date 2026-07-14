from xml.etree import ElementTree

import pytest

from custom_components.autelis_pool import AutelisData
from custom_components.autelis_pool.const import AUTELIS_HAYWARD, AUTELIS_UNKNOWN
from tests.conftest import load_xml


class _FakeAPI:
    """Stands in for AutelisPoolAPI, which needs a real hass to build a session."""

    def __init__(self, status, names=None):
        self._status, self._names = status, names
        self.available = True

    async def get(self, endpoint, optional=False):
        return self._status if endpoint == "status.xml" else self._names

    async def get_text(self, endpoint, optional=False):
        return self._names


async def test_refresh_detects_brand_and_builds_inventory():
    data = AutelisData("1.2.3.4", _FakeAPI(load_xml("hayward_1011_status.xml")))

    await data.async_refresh()

    assert data.profile.brand == AUTELIS_HAYWARD
    assert data.heat_sets == []
    assert data.equipment["aux5"] == "1"
    assert "aux8" not in data.equipment       # absent equipment stays absent


async def test_snapshot_drops_keys_that_go_empty():
    """The old code never cleared its dicts, so absent equipment looked installed."""
    data = AutelisData("1.2.3.4", _FakeAPI(load_xml("hayward_1011_status.xml")))
    await data.async_refresh()
    assert data.equipment["aux5"] == "1"

    emptied = load_xml("hayward_1011_status.xml")
    emptied.find("equipment").find("aux5").text = ""
    data.api = _FakeAPI(emptied)
    await data.async_refresh()

    assert "aux5" not in data.equipment


async def test_unknown_brand_refuses_to_guess():
    data = AutelisData("1.2.3.4", _FakeAPI(ElementTree.fromstring("<response></response>")))

    await data.async_refresh()

    assert data.brand == AUTELIS_UNKNOWN
    assert data.profile is None
    assert data.inventory == []
