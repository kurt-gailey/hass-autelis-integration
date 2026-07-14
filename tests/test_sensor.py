from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature

from custom_components.autelis_pool.sensor import AutelisTemperature


class _Data:
    def __init__(self, sensors):
        self.sensors = sensors
        self.host = "1.2.3.4"


def test_temperature_is_reported_verbatim_not_divided_by_ten():
    """<pooltemp>88</pooltemp> means 88 degrees. Upstream divides by 10."""
    sensor = AutelisTemperature(_Data({"pooltemp": "88", "tempunits": "F"}), "pooltemp", "Pool")
    assert sensor.native_value == 88


def test_device_class_is_actually_set():
    """Upstream does `self.type in (SensorDeviceClass.TEMPERATURE)` -- a SUBSTRING
    test against a string -- so no temperature sensor ever had a device class."""
    sensor = AutelisTemperature(_Data({"pooltemp": "88", "tempunits": "F"}), "pooltemp", "Pool")
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE


def test_celsius_units_are_honoured():
    sensor = AutelisTemperature(_Data({"pooltemp": "30", "tempunits": "C"}), "pooltemp", "Pool")
    assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS


def test_missing_reading_is_none_not_a_crash():
    sensor = AutelisTemperature(_Data({"tempunits": "F"}), "solartemp", "Solar")
    assert sensor.native_value is None
