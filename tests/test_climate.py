import pytest
from homeassistant.components.climate import HVACAction, HVACMode

from custom_components.autelis_pool.brands import HeatSet, JANDY, PENTAIR
from custom_components.autelis_pool.climate import AutelisHeater, heat_mode_to_hvac


class _Data:
    def __init__(self, profile, equipment, sensors):
        self.profile = profile
        self.equipment = equipment
        self.sensors = sensors
        self.host = "1.2.3.4"
        self.mode = "auto"
        self.api = None


@pytest.mark.parametrize(
    ("value", "mode", "action"),
    [
        (0, HVACMode.OFF, HVACAction.OFF),
        (1, HVACMode.HEAT, HVACAction.IDLE),     # enabled, not firing
        (2, HVACMode.HEAT, HVACAction.HEATING),  # actively heating
        (3, HVACMode.HEAT, HVACAction.IDLE),     # Pentair: solar-only. Upstream KeyErrors.
    ],
)
def test_heat_mode_mapping_covers_pentairs_full_range(value, mode, action):
    assert heat_mode_to_hvac(value) == (mode, action)


def test_jandy_reads_heat_from_equipment():
    data = _Data(JANDY, {"poolht": "2"}, {"pooltemp": "86", "poolsp": "90", "tempunits": "F"})
    entity = AutelisHeater(data, HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"))
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.hvac_action == HVACAction.HEATING
    assert entity.current_temperature == 86
    assert entity.target_temperature == 90


def test_pentair_reads_heat_from_temp_section():
    """Pentair puts poolht under <temp>. Reading <equipment> would KeyError."""
    data = _Data(PENTAIR, {}, {"poolht": "0", "pooltemp": "86", "poolsp": "68", "tempunits": "F"})
    entity = AutelisHeater(data, HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"))
    assert entity.hvac_mode == HVACMode.OFF
    assert entity.current_temperature == 86
