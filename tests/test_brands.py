from xml.etree import ElementTree

import pytest

from custom_components.autelis_pool.brands import (
    PROFILES,
    ROLE_CIRCUIT,
    ROLE_HEAT,
    ROLE_IGNORE,
    ROLE_READONLY,
    ROLE_SETPOINT,
    ROLE_TEMPERATURE,
    detect_brand,
)
from custom_components.autelis_pool.const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
    AUTELIS_UNKNOWN,
)
from tests.conftest import load_xml


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("jandy_169_status.xml", AUTELIS_JANDY),
        ("jandy_1617_status.xml", AUTELIS_JANDY),
        ("pentair_1611_status.xml", AUTELIS_PENTAIR),
        ("hayward_1011_status.xml", AUTELIS_HAYWARD),
    ],
)
def test_detect_brand_from_real_captures(fixture, expected):
    assert detect_brand(load_xml(fixture)) == expected


def test_sparse_xml_is_unknown_not_jandy():
    """A disconnected controller must NOT fall through to Jandy."""
    root = ElementTree.fromstring(
        "<response><system><runstate>1</runstate><model>0</model></system>"
        "<equipment></equipment><temp></temp></response>"
    )
    assert detect_brand(root) == AUTELIS_UNKNOWN


def test_empty_document_is_unknown():
    assert detect_brand(ElementTree.fromstring("<response></response>")) == AUTELIS_UNKNOWN


def test_jandy_roles():
    p = PROFILES[AUTELIS_JANDY]
    assert p.role("pump") == ROLE_CIRCUIT
    assert p.role("cleaner") == ROLE_CIRCUIT
    assert p.role("solarht") == ROLE_CIRCUIT      # upstream exposes this as a switch
    assert p.role("aux23") == ROLE_CIRCUIT        # docs say 15; real RS16 emits 23
    assert p.role("poolht") == ROLE_HEAT
    assert p.role("poolsp") == ROLE_SETPOINT
    assert p.role("pooltemp") == ROLE_TEMPERATURE
    # Macros are real circuits -- upstream turns a named macro into a working switch --
    # but Jandy reports all six whether or not any are configured, so they are only
    # ENABLED once the owner has named one. See requires_label.
    assert p.role("macro1") == ROLE_CIRCUIT
    assert "macro1" in p.requires_label
    assert "aux1" not in p.requires_label         # presence IS proof for an aux relay
    assert p.role("htpmp") == ROLE_IGNORE
    assert p.role("auxx") == ROLE_IGNORE
    assert p.role("tempunits") == ROLE_IGNORE
    assert p.role("nonsense") == ROLE_IGNORE      # unknown tags are ignored, not guessed


def test_hayward_roles_and_capabilities():
    p = PROFILES[AUTELIS_HAYWARD]
    assert p.supports_climate is False
    assert p.setpoint_param is None               # temp= is rejected with HTTP 500
    # names.xml 404s, but the owner's labels DO exist -- on the Setup page.
    assert p.names_endpoint == "settings.htm"
    assert p.names_format == "html"
    assert p.role("poolht") == ROLE_READONLY      # accepts writes, ignores them
    assert p.role("waterfall") == ROLE_READONLY
    assert p.role("aux5") == ROLE_CIRCUIT         # interlocked, NOT read-only
    assert p.role("schlor") == ROLE_CIRCUIT
    assert p.role("valve3") == ROLE_CIRCUIT
    assert p.solar_temp_tag == "solartemp"


def test_pentair_capabilities():
    p = PROFILES[AUTELIS_PENTAIR]
    assert p.heat_section == "temp"               # NOT equipment, unlike Jandy
    assert p.heat_param == "hval"                 # NOT value=
    assert p.heat_max_mode == 3                   # 3 = solar-only; Jandy tops out at 2
    assert p.solar_temp_tag == "soltemp"          # NOT solartemp
    assert p.role("circuit1") == ROLE_CIRCUIT
    assert p.role("feature10") == ROLE_CIRCUIT


def test_jandy_and_hayward_heat_live_in_equipment():
    assert PROFILES[AUTELIS_JANDY].heat_section == "equipment"
    assert PROFILES[AUTELIS_JANDY].heat_param == "value"
    assert PROFILES[AUTELIS_JANDY].heat_max_mode == 2
