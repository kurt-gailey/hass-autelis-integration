"""Autelis heaters, as Home Assistant climate entities.

Hayward has no climate entity: it exposes no setpoint to write OR read, so a
target temperature could never be shown. See the spec.
"""

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from .const import _LOGGER, DOMAIN, MAX_TEMP, MIN_TEMP, STATE_AUTO

# 0 = Off, 1 = Enabled (not firing), 2 = On (firing).
# 3 = solar-only, Pentair only. Upstream's map stops at 2 and KeyErrors on it.
_HEAT_MODES = {
    0: (HVACMode.OFF, HVACAction.OFF),
    1: (HVACMode.HEAT, HVACAction.IDLE),
    2: (HVACMode.HEAT, HVACAction.HEATING),
    3: (HVACMode.HEAT, HVACAction.IDLE),
}


def heat_mode_to_hvac(value: int):
    """Map an Autelis heat value to (HVACMode, HVACAction)."""
    return _HEAT_MODES.get(value, (HVACMode.OFF, HVACAction.OFF))


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a climate entity per heat set discovery found (none on Hayward)."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [AutelisHeater(data, heat_set) for heat_set in data.heat_sets], True
    )


class AutelisHeater(ClimateEntity):
    """One heater."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP

    def __init__(self, data, heat_set):
        self.data = data
        self.heat_set = heat_set
        _LOGGER.debug("adding heater %s", heat_set.name)

    @property
    def name(self):
        return self.heat_set.name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.heat_set.current_tag}"

    @property
    def available(self):
        return self.data.mode == STATE_AUTO

    @property
    def temperature_unit(self):
        if self.data.sensors.get("tempunits") == "C":
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    def _heat_value(self) -> int:
        """Read the heat mode from wherever this brand keeps it.

        Jandy puts poolht/spaht in <equipment>; Pentair puts them in <temp>.
        """
        section = (
            self.data.equipment
            if self.data.profile.heat_section == "equipment"
            else self.data.sensors
        )
        try:
            return int(section.get(self.heat_set.heat_tag, 0))
        except (TypeError, ValueError):
            return 0

    def _temp(self, tag):
        try:
            return int(self.data.sensors.get(tag))
        except (TypeError, ValueError):
            return None

    @property
    def current_temperature(self):
        return self._temp(self.heat_set.current_tag)

    @property
    def target_temperature(self):
        return self._temp(self.heat_set.setpoint_tag)

    @property
    def hvac_mode(self):
        return heat_mode_to_hvac(self._heat_value())[0]

    @property
    def hvac_action(self):
        return heat_mode_to_hvac(self._heat_value())[1]

    async def async_set_hvac_mode(self, hvac_mode):
        # Heaters accept only 0 (Off) and 1 (Enabled); the controller decides when
        # to actually fire, based on the setpoint.
        value = 1 if hvac_mode == HVACMode.HEAT else 0
        await self.data.api.send(
            self.data.profile, "heat", self.heat_set.heat_tag, value
        )
        await self.data.async_refresh()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        target = max(MIN_TEMP, min(MAX_TEMP, int(temperature)))
        await self.data.api.send(
            self.data.profile, "setpoint", self.heat_set.setpoint_tag, target
        )
        await self.data.async_refresh()

    async def async_update(self):
        await self.data.update()
