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


class _PumpApi:
    def __init__(self):
        self.calls = []

    async def send(self, profile, kind, tag, value):
        self.calls.append((profile, kind, tag, value))


class _PumpData(_Data):
    def __init__(self, controller_response):
        super().__init__({"pump": "1"})
        self.api = _PumpApi()
        self.controller_response = controller_response

    async def async_refresh(self):
        self.equipment["pump"] = self.controller_response


@pytest.mark.parametrize(
    ("controller_response", "expected_running"), [("1", True), ("0", False)]
)
async def test_hayward_filter_switch_off_tracks_the_controller_after_each_downstep(
    controller_response, expected_running
):
    """High -> Low returns on; Low -> Off remains off after the status refresh."""
    data = _PumpData(controller_response)
    switch = AutelisCircuit(data, "pump", "Filter Pump")

    await switch.async_turn_off()

    assert data.api.calls == [(None, "circuit", "pump", 0)]
    assert switch.is_on is expected_running
