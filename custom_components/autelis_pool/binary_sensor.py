"""Read-only Autelis equipment.

Hayward's poolht and waterfall accept writes and silently ignore them (set.cgi
answers "1" either way -- that response only means the NAME was recognised). They
are reported, never controlled.

poolht reports whether the heater is RUNNING, not whether it is ENABLED. The enabled
state can only be read by pressing the panel's heat toggle, which changes it. So no
honest switch is possible; this is a sensor, and its name says so.
"""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .const import _LOGGER, DOMAIN, STATE_AUTO

_HEAT_TAGS = {"poolht", "poolht2", "spaht"}
_OFF_VALUES = {"", "0"}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a binary sensor for each read-only item discovery found."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AutelisReadOnly(data, item.tag, item.name)
            for item in data.inventory
            if item.platform == "binary_sensor"
        ],
        True,
    )


class AutelisReadOnly(BinarySensorEntity):
    """One piece of equipment we can see but not command."""

    def __init__(self, data, equipment_name, friendly_name):
        self.data = data
        self.equipment_name = equipment_name
        self.friendly_name = friendly_name
        _LOGGER.debug("adding read-only %s (%s)", equipment_name, friendly_name)

    @property
    def name(self):
        # "Running", not "Heater" -- this reports the burner firing, not a mode you
        # can set. Naming it like a control would misrepresent what it knows.
        if self.equipment_name in _HEAT_TAGS:
            return f"{self.friendly_name} Running"
        return self.friendly_name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.equipment_name}"

    @property
    def device_class(self):
        if self.equipment_name in _HEAT_TAGS:
            return BinarySensorDeviceClass.HEAT
        return None

    @property
    def available(self):
        return self.data.mode == STATE_AUTO

    @property
    def is_on(self):
        return self.data.equipment.get(self.equipment_name, "0") not in _OFF_VALUES

    async def async_update(self):
        await self.data.update()
