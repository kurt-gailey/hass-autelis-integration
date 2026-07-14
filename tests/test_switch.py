import pytest

from custom_components.autelis_pool.switch import AutelisCircuit


class _Data:
    def __init__(self, equipment, profile=None):
        self.equipment = equipment
        self.profile = profile
        self.host = "1.2.3.4"
        self.mode = "auto"
        self.api = None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", False),
        ("1", True),
        ("2", True),      # tri-state: solar heat "on"
        ("25", True),     # dimmer levels are ON -- upstream reads these as Off
        ("50", True),
        ("75", True),
        ("100", True),
    ],
)
def test_is_on_handles_dimmers_and_tristate(value, expected):
    switch = AutelisCircuit(_Data({"aux3": value}), "aux3", "Air Blower")
    assert switch.is_on is expected


def test_missing_equipment_reads_off_not_keyerror():
    """Equipment can vanish from a snapshot; that must not raise."""
    switch = AutelisCircuit(_Data({}), "aux3", "Air Blower")
    assert switch.is_on is False


def test_unique_id_matches_the_existing_scheme():
    """Changing this silently breaks every user's dashboard."""
    switch = AutelisCircuit(_Data({"pump": "1"}), "pump", "Pool")
    assert switch.unique_id == "autelis 1.2.3.4 pump"
