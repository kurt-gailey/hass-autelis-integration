import pytest

from custom_components.autelis_pool.api import CommandNotSupported, build_command
from custom_components.autelis_pool.brands import HAYWARD, JANDY, PENTAIR


def test_circuit_command_is_the_same_on_every_brand():
    assert build_command(JANDY, "circuit", "pump", 1) == "set.cgi?name=pump&value=1"
    assert build_command(HAYWARD, "circuit", "aux5", 0) == "set.cgi?name=aux5&value=0"
    assert build_command(PENTAIR, "circuit", "circuit1", 1) == "set.cgi?name=circuit1&value=1"


def test_jandy_setpoint_uses_temp_param():
    assert build_command(JANDY, "setpoint", "poolsp", 90) == "set.cgi?name=poolsp&temp=90"


def test_hayward_setpoint_is_refused_not_sent():
    """Hayward rejects ANY temp= param with HTTP 500 -- even on a valid name.

    Sending one is not merely useless, it is an error we already know the answer to.
    """
    with pytest.raises(CommandNotSupported):
        build_command(HAYWARD, "setpoint", "poolsp", 90)


def test_hayward_heat_is_refused():
    with pytest.raises(CommandNotSupported):
        build_command(HAYWARD, "heat", "poolht", 1)


def test_jandy_heat_uses_value_param():
    assert build_command(JANDY, "heat", "poolht", 1) == "set.cgi?name=poolht&value=1"


def test_pentair_heat_uses_hval_param():
    assert build_command(PENTAIR, "heat", "poolht", 3) == "set.cgi?name=poolht&hval=3"


def test_no_command_ever_sends_temp_to_hayward():
    """The one bug that would break a real user's controller with a 500."""
    for kind, tag, value in (("circuit", "pump", 1), ("circuit", "schlor", 0)):
        assert "temp=" not in build_command(HAYWARD, kind, tag, value)
