from types import SimpleNamespace

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature

from custom_components.autelis_pool.const import DOMAIN
from custom_components.autelis_pool.sensor import (
    AutelisOpMode,
    AutelisTemperature,
)
from custom_components.autelis_pool.sensor import async_setup_entry as sensor_setup


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


class _Controller:
    def __init__(self, opmode, connected=True):
        self.system = {} if opmode is None else {"opmode": opmode}
        self.connected = connected
        self.host = "1.2.3.4"


@pytest.mark.parametrize(
    ("opmode", "expected"),
    [("0", "auto"), ("1", "service"), ("2", "timeout"), ("7", "7"), (None, None)],
)
def test_mode_sensor_names_the_controller_opmode(opmode, expected):
    assert AutelisOpMode(_Controller(opmode)).native_value == expected


def test_mode_sensor_is_unavailable_when_the_reading_cannot_be_current():
    """A dead controller's last mode is stale. It must not read as still in service."""
    assert AutelisOpMode(_Controller("1", connected=True)).available is True
    assert AutelisOpMode(_Controller("1", connected=False)).available is False


async def test_setup_adds_the_mode_sensor():
    data = _Controller("0")
    data.inventory = []
    added = []
    hass = SimpleNamespace(data={DOMAIN: {"entry": data}})

    await sensor_setup(hass, SimpleNamespace(entry_id="entry"), lambda e, _: added.extend(e))

    assert [entity.unique_id for entity in added] == ["autelis 1.2.3.4 opmode"]
    assert added[0].name == "Pool Controller Mode"
