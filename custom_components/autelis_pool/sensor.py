"""Autelis temperature sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

from .const import _LOGGER, DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a sensor for each temperature reading discovery found."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AutelisTemperature(data, item.tag, item.name)
            for item in data.inventory
            if item.platform == "sensor"
        ],
        True,
    )


class AutelisTemperature(SensorEntity):
    """One temperature reading."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, data, sensor_name, friendly_name):
        self.data = data
        self.sensor_name = sensor_name
        self.friendly_name = friendly_name
        _LOGGER.debug("adding sensor %s (%s)", sensor_name, friendly_name)

    @property
    def name(self):
        return self.friendly_name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.sensor_name}"

    @property
    def native_unit_of_measurement(self):
        if self.data.sensors.get("tempunits") == "C":
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    @property
    def native_value(self):
        """The reading, verbatim.

        The old code divided by 10, which is wrong for this API -- <pooltemp>88</>
        means 88 degrees. It was dead code only because `self.type == "temperature"`
        never matched the capitalised "Temperature" it was given. Fixing the
        capitalisation without removing the division would have broken every reading.
        """
        raw = self.data.sensors.get(self.sensor_name)
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    async def async_update(self):
        await self.data.update()
