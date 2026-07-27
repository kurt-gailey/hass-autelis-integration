from types import SimpleNamespace

import pytest

from custom_components.autelis_pool.brands import HAYWARD, JANDY
from custom_components.autelis_pool.button import AutelisFilterPumpLowOrOff, async_setup_entry
from custom_components.autelis_pool.const import DOMAIN, STATE_AUTO


class _Api:
    def __init__(self):
        self.calls = []

    async def send(self, profile, kind, tag, value):
        self.calls.append((profile, kind, tag, value))
        return True


class _Data:
    def __init__(self, profile):
        self.profile = profile
        self.host = "1.2.3.4"
        self.mode = STATE_AUTO
        self.api = _Api()
        self.refreshes = 0

    async def async_refresh(self):
        self.refreshes += 1


@pytest.mark.asyncio
async def test_low_or_off_button_sends_haywards_non_idempotent_down_command():
    """One press asks a dual-speed Hayward to move High -> Low or Low -> Off."""
    data = _Data(HAYWARD)
    button = AutelisFilterPumpLowOrOff(data)

    await button.async_press()

    assert data.api.calls == [(HAYWARD, "circuit", "pump", 0)]
    assert data.refreshes == 1
    assert button.name == "Filter Pump Low / Off"
    assert button.unique_id == "autelis 1.2.3.4 filter-pump-low-off"


@pytest.mark.asyncio
async def test_button_is_created_only_for_hayward():
    entry = SimpleNamespace(entry_id="entry")
    added = []

    def add_entities(entities, update_before_add):
        added.extend(entities)
        assert update_before_add is True

    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: _Data(HAYWARD)}})
    await async_setup_entry(hass, entry, add_entities)
    assert len(added) == 1
    assert isinstance(added[0], AutelisFilterPumpLowOrOff)

    added.clear()
    hass.data[DOMAIN][entry.entry_id] = _Data(JANDY)
    await async_setup_entry(hass, entry, add_entities)
    assert added == []
