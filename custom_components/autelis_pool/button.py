"""Hayward-only actions that are not safely representable as switches."""

from homeassistant.components.button import ButtonEntity

from .brands import HAYWARD
from .const import DOMAIN, STATE_AUTO


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create the Hayward filter-pump downshift action when supported."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    if data.profile == HAYWARD:
        async_add_entities([AutelisFilterPumpLowOrOff(data)], True)


class AutelisFilterPumpLowOrOff(ButtonEntity):
    """Advance a Hayward two-speed filter pump from High to Low, or Low to Off."""

    _attr_icon = "mdi:fan-chevron-down"

    def __init__(self, data):
        self.data = data

    @property
    def available(self):
        """The panel accepts circuit commands only while it is in automatic mode."""
        return self.data.mode == STATE_AUTO

    @property
    def name(self):
        """Return the intentionally explicit action label shown in Home Assistant."""
        return "Filter Pump Low / Off"

    @property
    def unique_id(self):
        """Keep this entity stable if the integration reloads."""
        return f"autelis {self.data.host} filter-pump-low-off"

    async def async_press(self):
        """Send Hayward's non-idempotent pump-down command and refresh actual state.

        On the verified Hayward controller, `pump=0` transitions High to Low, then Low
        to Off. The controller only reports whether the pump is running, so this is a
        button rather than a false three-state select.
        """
        await self.data.api.send(self.data.profile, "circuit", "pump", 0)
        await self.data.async_refresh()
