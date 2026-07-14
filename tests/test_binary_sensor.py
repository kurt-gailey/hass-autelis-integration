from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.autelis_pool.binary_sensor import AutelisReadOnly


class _Data:
    def __init__(self, equipment):
        self.equipment = equipment
        self.host = "1.2.3.4"
        self.mode = "auto"


def test_heater_reports_running_state():
    entity = AutelisReadOnly(_Data({"poolht": "1"}), "poolht", "Heater")
    assert entity.is_on is True
    assert entity.device_class == BinarySensorDeviceClass.HEAT


def test_heater_off():
    assert AutelisReadOnly(_Data({"poolht": "0"}), "poolht", "Heater").is_on is False


def test_name_says_running_so_nobody_mistakes_it_for_a_control():
    """poolht reports whether the heater is RUNNING, not whether it is ENABLED.

    Hayward can toggle heat only via the panel keypad, and the enabled state cannot
    be read back at all -- so this must never look like a switch.
    """
    assert AutelisReadOnly(_Data({"poolht": "0"}), "poolht", "Heater").name == "Heater Running"


def test_non_heat_readonly_has_no_heat_device_class():
    entity = AutelisReadOnly(_Data({"waterfall": "1"}), "waterfall", "Waterfall")
    assert entity.device_class is None
    assert entity.name == "Waterfall"
