"""Autelis circuit switches."""

from homeassistant.components.switch import SwitchEntity

from .const import _LOGGER, DOMAIN, STATE_AUTO

# 0 = Off. 1 = On. 2 = On (tri-state heat: "enabled" vs "actively heating").
# 25/50/75/100 = a dimmer's level, which also means On -- upstream compares only
# against "1"/"2", so every dimmable Jandy aux currently reads as Off.
_OFF_VALUES = {"", "0"}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a switch for each controllable circuit discovery found."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AutelisCircuit(data, item.tag, item.name, item.enabled_default)
            for item in data.inventory
            if item.platform == "switch"
        ],
        True,
    )


class AutelisCircuit(SwitchEntity):
    """One controllable circuit."""

    def __init__(self, data, equipment_name, friendly_name, enabled_default=True):
        self.data = data
        self.equipment_name = equipment_name
        self.friendly_name = friendly_name
        # An installed-but-unassigned relay ("AUX5") is registered and left disabled:
        # it clutters nothing for an owner who never wired it, and is one click away
        # for an owner who did.
        self._attr_entity_registry_enabled_default = enabled_default
        _LOGGER.debug("adding circuit %s (%s)", equipment_name, friendly_name)

    @property
    def available(self):
        return self.data.mode == STATE_AUTO

    @property
    def name(self):
        return self.friendly_name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.equipment_name}"

    @property
    def is_on(self):
        return self.data.equipment.get(self.equipment_name, "0") not in _OFF_VALUES

    async def async_turn_on(self, **kwargs):
        await self._set(1)

    async def async_turn_off(self, **kwargs):
        await self._set(0)

    async def _set(self, value):
        """Send the command, then let the next poll tell us what really happened.

        The panel can refuse a circuit for interlock reasons -- a cleaner will not
        start while the valves are diverted to the spa -- and set.cgi answers "1"
        regardless. So we do not assume the write landed.
        """
        await self.data.api.send(self.data.profile, "circuit", self.equipment_name, value)
        await self.data.async_refresh()

    async def async_update(self):
        await self.data.update()
