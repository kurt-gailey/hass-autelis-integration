"""The entity manifests.

Nobody working on this has Jandy or Pentair hardware, so this file is the safety
argument: it pins EXACTLY which entities each real capture produces. A human signs
these off once; after that, any change to an existing brand's entity set has to be
deliberate enough to edit this file.

**If a manifest disagrees with the code, work out why before touching either.** The
temptation is to paste the code's output over the expected list and move on. That
converts this file from a gate into a rubber stamp, and it is the only thing standing
between a refactor and someone's pool.

Deliberately NOT "reproduce master's output exactly": master's Jandy behaviour is partly
what we are changing, so a blanket parity assertion would either block the fix or be
neutered by carving out the bug. Instead each list is explicit, and the Jandy manifest
is annotated with how it compares to master.
"""

from custom_components.autelis_pool.brands import PROFILES
from custom_components.autelis_pool.const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
)
from custom_components.autelis_pool.discovery import build_heat_sets, build_inventory
from custom_components.autelis_pool.names import parse_aux_labels_html, parse_names_xml
from tests.conftest import load_fixture, load_xml


def _manifest(status, brand, names_file=None, settings_file=None):
    """(platform, tag, name, enabled_by_default) for every entity, sorted."""
    names = {}
    if names_file:
        names = parse_names_xml(load_xml(names_file))
    if settings_file:
        names = parse_aux_labels_html(load_fixture(settings_file))

    profile = PROFILES[brand]
    root = load_xml(status)
    entities = [
        (d.platform, d.tag, d.name, d.enabled_default)
        for d in build_inventory(root, profile, names)
    ]
    entities += [
        ("climate", h.heat_tag, h.name, True) for h in build_heat_sets(root, profile)
    ]
    # One sort over everything, so the expected lists below can be written in plain
    # alphabetical order rather than mirroring an internal concatenation order.
    return sorted(entities)


# ---------------------------------------------------------------------------
# Jandy Aqualink RS, firmware 1.6.9 (upstream issue #3).
#
# THE REGRESSION GATE. This switch set is IDENTICAL to what master produces today.
#
# Master arrives at it by a different route: it builds aux switches from names.xml and
# leans on a startswith("Cleaner") filter to skip aux1. We arrive at it from status.xml,
# where aux1 is simply empty because the cleaner's state lives in <cleaner>.
#
# Same answer -- but ours does not depend on what the owner called the circuit. Name it
# "Polaris" and master grows a phantom switch backed by nothing; we do not.
# ---------------------------------------------------------------------------
JANDY_169 = [
    ("climate", "poolht", "Pool Heat", True),
    ("climate", "spaht", "Spa Heat", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "solartemp", "Solar Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    ("switch", "aux2", "Waterfall", True),
    ("switch", "aux3", "Air Blower", True),
    ("switch", "aux4", "SPA Light", True),
    ("switch", "aux5", "Pool Light", True),
    ("switch", "aux6", "Not Used", True),   # a deliberate label, not a placeholder
    ("switch", "aux7", "Not Used", True),
    ("switch", "cleaner", "Cleaner", True),
    ("switch", "pump", "Pool", True),
    ("switch", "solarht", "Solar Heating", True),
    ("switch", "spa", "Spa", True),
]

# ---------------------------------------------------------------------------
# Jandy Aqualink RS, firmware 1.6.17 (upstream issue #6).
#
# htpmp and auxx are ignored: undocumented, and empty in every capture we have.
#
# macro1-6 ARE exposed. Upstream supports macros -- a macro the owner names becomes a
# working switch -- so dropping them would delete a documented feature. But Jandy reports
# all six whether or not any are configured, so presence proves nothing and only a name
# does. This unit has no names.xml, so all six are registered DISABLED rather than
# cluttering the dashboard with switches that do nothing.
#
# The aux fallback labels below are OURS, not the device's. That is not evidence the
# relays are unassigned, so they stay enabled: status.xml says they are installed, and
# that is all we know.
# ---------------------------------------------------------------------------
JANDY_1617 = [
    ("climate", "poolht", "Pool Heat", True),
    ("climate", "spaht", "Spa Heat", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "solartemp", "Solar Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    ("switch", "aux1", "Aux 1", True),
    ("switch", "aux2", "Aux 2", True),
    ("switch", "aux3", "Aux 3", True),
    ("switch", "aux4", "Aux 4", True),
    ("switch", "aux5", "Aux 5", True),
    ("switch", "aux6", "Aux 6", True),
    ("switch", "aux7", "Aux 7", True),
    ("switch", "macro1", "Macro 1", False),   # unnamed => unconfigured OneTouch slot
    ("switch", "macro2", "Macro 2", False),
    ("switch", "macro3", "Macro 3", False),
    ("switch", "macro4", "Macro 4", False),
    ("switch", "macro5", "Macro 5", False),
    ("switch", "macro6", "Macro 6", False),
    ("switch", "pump", "Pool", True),
    ("switch", "spa", "Spa", True),
]

# ---------------------------------------------------------------------------
# Pentair EasyTouch, firmware 1.6.11 (upstream issue #5).
#
# Entirely NEW -- master crashes on Pentair, so there is no prior behaviour to preserve.
# Circuits still carrying a placeholder label ("AUX 2") are registered disabled.
# ---------------------------------------------------------------------------
PENTAIR_1611 = [
    ("climate", "poolht", "Pool Heat", True),
    ("climate", "spaht", "Spa Heat", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    ("switch", "circuit1", "SPA", True),
    ("switch", "circuit2", "LIGHTS", True),
    ("switch", "circuit20", "AUX EXTRA", True),   # named, just oddly
    ("switch", "circuit3", "AUX 2", False),       # placeholder => unassigned
    ("switch", "circuit4", "AUX 3", False),
    ("switch", "circuit5", "AUX 4", False),
    ("switch", "circuit6", "POOL", True),
    ("switch", "circuit7", "AUX 5", False),
    ("switch", "circuit8", "AUX 6", False),
    ("switch", "circuit9", "POOL HIGH", True),
    ("switch", "feature1", "FEATURE 1", True),
    ("switch", "feature2", "FEATURE 2", True),
    ("switch", "feature3", "FEATURE 3", True),
    ("switch", "feature4", "FEATURE 4", True),
    ("switch", "feature5", "FEATURE 5", True),
    ("switch", "feature6", "FEATURE 6", True),
    ("switch", "feature7", "FEATURE 7", True),
    ("switch", "feature8", "FEATURE 8", True),
]

# ---------------------------------------------------------------------------
# Hayward, model 512, firmware 1.0.11 (live device).
#
# Entirely NEW. No climate entity: there is no setpoint to write AND none to read.
# Names are the OWNER's, read from the Autelis Setup page -- not firmware constants.
# aux6/aux7 are real relays (the panel has AUX 5 / AUX 6 buttons) but still carry
# placeholder labels, so they are registered disabled.
# ---------------------------------------------------------------------------
HAYWARD_1011 = [
    ("binary_sensor", "poolht", "Heater", True),
    ("binary_sensor", "waterfall", "Waterfall", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    ("switch", "aux1", "Pool Lights", True),
    ("switch", "aux2", "Spa Lights", True),
    ("switch", "aux3", "Blower", True),
    ("switch", "aux4", "Waterfall", True),
    ("switch", "aux5", "Cleaner", True),
    ("switch", "aux6", "AUX5", False),      # installed but unassigned
    ("switch", "aux7", "AUX6", False),
    ("switch", "pump", "Filter Pump", True),
    ("switch", "schlor", "SuperChlorinate", True),
    ("switch", "spa", "Spa", True),
    ("switch", "valve3", "Valve 3", True),
    ("switch", "valve4", "Valve 4", True),
]


def test_jandy_169_manifest():
    assert (
        _manifest("jandy_169_status.xml", AUTELIS_JANDY, "jandy_169_names.xml")
        == JANDY_169
    )


def test_jandy_1617_manifest():
    assert _manifest("jandy_1617_status.xml", AUTELIS_JANDY) == JANDY_1617


def test_pentair_1611_manifest():
    assert (
        _manifest("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
        == PENTAIR_1611
    )


def test_hayward_1011_manifest():
    assert (
        _manifest(
            "hayward_1011_status.xml",
            AUTELIS_HAYWARD,
            settings_file="hayward_1011_settings.htm",
        )
        == HAYWARD_1011
    )


def test_jandy_keeps_every_switch_master_created():
    """The regression gate, stated as a claim rather than a diff."""
    master_switches = {
        "pump", "spa", "solarht", "cleaner",             # upstream's CIRCUITS dict
        "aux2", "aux3", "aux4", "aux5", "aux6", "aux7",  # survive upstream's name filters
    }
    ours = {tag for platform, tag, _, _ in JANDY_169 if platform == "switch"}
    assert master_switches == ours


def test_no_existing_jandy_entity_is_disabled():
    """Discovery must not quietly disable an entity a Jandy user already has."""
    assert all(enabled for _, _, _, enabled in JANDY_169)


def test_jandy_entity_names_are_unchanged():
    """Renaming an entity changes its display name in every existing dashboard.

    Upstream's TEMP_SENSORS produced "Pool Temperature"; its CIRCUITS produced "Pool",
    "Spa", "Solar Heating", "Cleaner". Discovery must reproduce those exact strings, or
    every current user's UI labels quietly change under them.
    """
    names = {tag: name for _, tag, name, _ in JANDY_169}
    assert names["pooltemp"] == "Pool Temperature"
    assert names["spatemp"] == "Spa Temperature"
    assert names["airtemp"] == "Air Temperature"
    assert names["solartemp"] == "Solar Temperature"
    assert names["pump"] == "Pool"
    assert names["spa"] == "Spa"
    assert names["solarht"] == "Solar Heating"
    assert names["cleaner"] == "Cleaner"


def test_jandy_cleaner_on_aux1_produces_no_phantom():
    """<aux1> is empty while names.xml calls it "Cleaner"; the state lives in <cleaner>."""
    tags = {tag for _, tag, _, _ in JANDY_169}
    assert "aux1" not in tags
    assert "cleaner" in tags


def test_jandy_macro_support_is_preserved_but_opt_in():
    """Upstream's readme documents working Macro support; dropping it would be a
    regression for the maintainer's own pool. But Jandy reports all six macros whether
    configured or not, so an unnamed one is registered disabled rather than shipping six
    dead switches to every user."""
    macros = {tag: enabled for _, tag, _, enabled in JANDY_1617 if tag.startswith("macro")}
    assert len(macros) == 6
    assert not any(macros.values())


def test_jandy_undocumented_tags_are_ignored():
    tags = {tag for _, tag, _, _ in JANDY_1617}
    assert "htpmp" not in tags
    assert "auxx" not in tags


def test_hayward_has_no_climate_entity():
    """Not a choice. There is no setpoint to write and none to read."""
    assert not [e for e in HAYWARD_1011 if e[0] == "climate"]


def test_hayward_heater_is_a_sensor_not_a_switch():
    """poolht reports RUNNING, not ENABLED, and the enabled state cannot be read back."""
    poolht = [e for e in HAYWARD_1011 if e[1] == "poolht"]
    assert poolht == [("binary_sensor", "poolht", "Heater", True)]


def test_hayward_names_are_the_owners_not_ours():
    """Read from settings.htm. An earlier draft hardcoded these as firmware constants."""
    names = {tag: name for _, tag, name, _ in HAYWARD_1011}
    assert names["aux1"] == "Pool Lights"
    assert names["aux3"] == "Blower"
    assert names["aux5"] == "Cleaner"


def test_hayward_aux5_is_a_switch_not_read_only():
    """It refused a write during testing -- but only because the pool was in a scheduled
    spa window, and a cleaner cannot run with the valves diverted. Interlocked, not
    read-only."""
    aux5 = [e for e in HAYWARD_1011 if e[1] == "aux5"]
    assert aux5 == [("switch", "aux5", "Cleaner", True)]
