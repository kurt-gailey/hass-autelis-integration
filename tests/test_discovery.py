from custom_components.autelis_pool.brands import PROFILES
from custom_components.autelis_pool.const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
)
from custom_components.autelis_pool.discovery import (
    build_heat_sets,
    build_inventory,
    snapshot,
)
from custom_components.autelis_pool.names import parse_aux_labels_html, parse_names_xml
from tests.conftest import load_fixture, load_xml


def _inv(status, brand, names_file=None, settings_file=None):
    names = {}
    if names_file:
        names = parse_names_xml(load_xml(names_file))
    if settings_file:
        names = parse_aux_labels_html(load_fixture(settings_file))
    return build_inventory(load_xml(status), PROFILES[brand], names)


def _tags(inventory, platform):
    return sorted(d.tag for d in inventory if d.platform == platform)


def test_jandy_empty_aux1_produces_no_entity():
    """aux1 is blank in status.xml even though names.xml labels it 'Cleaner'.

    The circuit's state lives in <cleaner>. Building from names.xml is what
    produced the phantom switch in upstream issue #3.
    """
    inv = _inv("jandy_169_status.xml", AUTELIS_JANDY, "jandy_169_names.xml")
    switches = _tags(inv, "switch")
    assert "aux1" not in switches
    assert "cleaner" in switches


def test_jandy_phantom_is_name_independent():
    """The upstream fix keys off the literal name 'Cleaner'. Ours must not."""
    names = {"aux1": "Polaris", "aux2": "Waterfall"}
    inv = build_inventory(
        load_xml("jandy_169_status.xml"), PROFILES[AUTELIS_JANDY], names
    )
    assert "aux1" not in _tags(inv, "switch")


def test_jandy_absent_equipment_is_skipped():
    inv = _inv("jandy_169_status.xml", AUTELIS_JANDY, "jandy_169_names.xml")
    switches = _tags(inv, "switch")
    for absent in ("pumplo", "waterfall", "aux8", "aux23"):
        assert absent not in switches


def test_jandy_macros_are_never_switches():
    """macroN is non-empty in 1.6.17, but no one has verified its set.cgi name."""
    inv = _inv("jandy_1617_status.xml", AUTELIS_JANDY)
    switches = _tags(inv, "switch")
    assert not [t for t in switches if t.startswith("macro")]
    assert "htpmp" not in switches
    assert "auxx" not in switches


def test_hayward_readonly_equipment_becomes_binary_sensor():
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    assert _tags(inv, "binary_sensor") == ["poolht", "waterfall"]
    assert "poolht" not in _tags(inv, "switch")


def test_hayward_aux5_is_a_switch():
    """Interlocked during testing, not read-only. See the spec."""
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    assert "aux5" in _tags(inv, "switch")


def test_hayward_has_no_climate():
    root = load_xml("hayward_1011_status.xml")
    assert build_heat_sets(root, PROFILES[AUTELIS_HAYWARD]) == []


def test_hayward_empty_solartemp_produces_no_sensor():
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    assert _tags(inv, "sensor") == ["airtemp", "pooltemp", "spatemp"]


def test_hayward_uses_the_owners_labels_from_the_setup_page():
    """Hayward has no names.xml, but the owner's labels live on the Setup page."""
    inv = _inv(
        "hayward_1011_status.xml",
        AUTELIS_HAYWARD,
        settings_file="hayward_1011_settings.htm",
    )
    by_tag = {d.tag: d.name for d in inv}
    assert by_tag["aux1"] == "Pool Lights"
    assert by_tag["aux5"] == "Cleaner"
    assert by_tag["schlor"] == "SuperChlorinate"   # fixed circuit, not an aux


def test_hayward_degrades_to_defaults_if_the_scrape_fails():
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    by_tag = {d.tag: d.name for d in inv}
    assert by_tag["aux1"] == "Aux 1"
    assert by_tag["pump"] == "Filter Pump"


def test_unassigned_relays_are_created_but_disabled():
    """aux6/aux7 are real relays -- the panel has the buttons -- but unassigned.

    Not hidden (someone else may use theirs) and not enabled (this owner does not).
    """
    inv = _inv(
        "hayward_1011_status.xml",
        AUTELIS_HAYWARD,
        settings_file="hayward_1011_settings.htm",
    )
    enabled = {d.tag: d.enabled_default for d in inv if d.platform == "switch"}

    assert enabled["aux6"] is False   # label is still the placeholder "AUX5"
    assert enabled["aux7"] is False
    assert enabled["aux1"] is True    # "Pool Lights"
    assert enabled["aux5"] is True    # "Cleaner"
    assert enabled["pump"] is True


def test_our_own_fallback_names_do_not_count_as_placeholders():
    """A tag with no DEVICE label tells us nothing -- status.xml says it exists."""
    inv = _inv("jandy_1617_status.xml", AUTELIS_JANDY)   # no names.xml for this unit
    enabled = {d.tag: d.enabled_default for d in inv if d.platform == "switch"}
    assert enabled["aux1"] is True


def test_pentair_unassigned_circuits_are_disabled():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    enabled = {d.tag: d.enabled_default for d in inv if d.platform == "switch"}
    assert enabled["circuit3"] is False   # "AUX 2" -- a placeholder, with a space
    assert enabled["circuit1"] is True    # "SPA"
    assert enabled["circuit20"] is True   # "AUX EXTRA" -- named, just oddly


def test_pentair_heat_is_found_under_temp():
    heat = build_heat_sets(load_xml("pentair_1611_status.xml"), PROFILES[AUTELIS_PENTAIR])
    assert [h.name for h in heat] == ["Pool Heat", "Spa Heat"]


def test_pentair_uses_soltemp_not_solartemp():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    # soltemp is empty in the capture, so no solar sensor at all.
    assert _tags(inv, "sensor") == ["airtemp", "pooltemp", "spatemp"]


def test_pentair_circuits_and_features_are_switches():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    switches = _tags(inv, "switch")
    assert "circuit1" in switches
    assert "feature8" in switches
    assert "circuit10" not in switches   # empty => not installed
    assert "htstatus" not in switches    # ignored role


def test_names_xml_only_labels_it_does_not_create():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    by_tag = {d.tag: d.name for d in inv}
    assert by_tag["circuit1"] == "SPA"
    assert by_tag["circuit6"] == "POOL"


def test_snapshot_drops_absent_keys():
    """A tag that empties must vanish from the snapshot, not keep its old value."""
    snap = snapshot(load_xml("hayward_1011_status.xml"), PROFILES[AUTELIS_HAYWARD])
    assert "aux8" not in snap["equipment"]
    assert snap["equipment"]["aux5"] == "1"
    assert "solartemp" not in snap["temp"]
    assert snap["temp"]["tempunits"] == "F"
