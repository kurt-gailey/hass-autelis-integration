"""Per-brand schema and capability profiles for Autelis pool controllers.

Autelis speaks a different XML dialect per controller family. This module is the
single place that knows the differences.

Two ideas keep it honest:

* The profile declares what a tag *is* (its role). Discovery decides whether that
  equipment is *installed*. A tag no profile knows is ignored, never guessed at —
  guessing produces switches that silently do nothing.
* Brand detection requires a positive marker. There is no fall-through default,
  because a disconnected controller emits sparse XML and would be misdetected,
  then persist a wrong entity set into the registry.

See docs/superpowers/specs/2026-07-14-hayward-support-design.md for the evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, NamedTuple
from xml.etree.ElementTree import Element

from .const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
    AUTELIS_UNKNOWN,
)

ROLE_CIRCUIT = "circuit"          # controllable on/off -> switch
ROLE_READONLY = "readonly"        # reports state, refuses writes -> binary_sensor
ROLE_HEAT = "heat"                # owned by the climate entity
ROLE_SETPOINT = "setpoint"        # owned by the climate entity
ROLE_TEMPERATURE = "temperature"  # -> sensor
ROLE_IGNORE = "ignore"            # deliberately not exposed


class HeatSet(NamedTuple):
    """One climate entity: a current temp, a setpoint, and a heat-mode tag."""

    name: str
    current_tag: str
    setpoint_tag: str
    heat_tag: str


@dataclass(frozen=True)
class BrandProfile:
    """Everything that differs between controller families."""

    brand: int
    key: str
    names_endpoint: str | None   # where the owner's labels live
    names_format: str | None     # "xml" (names.xml) or "html" (Hayward's settings.htm)
    setpoint_param: str | None   # "temp", or None where setpoints don't exist
    heat_section: str | None     # which status.xml section holds poolht/spaht
    heat_param: str | None       # "value" (Jandy) or "hval" (Pentair)
    heat_max_mode: int           # highest valid heat mode value
    solar_temp_tag: str | None
    supports_climate: bool
    roles: Mapping[str, str]
    heat_sets: tuple[HeatSet, ...] = ()
    default_names: Mapping[str, str] = field(default_factory=dict)

    def role(self, tag: str) -> str:
        """Role of a tag. Unknown tags are ignored, never guessed at."""
        return self.roles.get(tag, ROLE_IGNORE)


def _roles(**groups: tuple[str, ...]) -> dict[str, str]:
    """Build a tag -> role map from role -> tags groups."""
    return {tag: role for role, tags in groups.items() for tag in tags}


# These reproduce the entity names upstream's TEMP_SENSORS dict produced ("Pool
# Temperature", not "pooltemp"). Without them the refactor would silently rename
# every existing user's temperature sensors.
_TEMP_NAMES = {
    "pooltemp": "Pool Temperature",
    "spatemp": "Spa Temperature",
    "airtemp": "Air Temperature",
    "solartemp": "Solar Temperature",
    "soltemp": "Solar Temperature",   # Pentair spells it differently
}

_JANDY_AUX = tuple(f"aux{n}" for n in range(1, 24))   # docs say 15; real RS16 emits 23
_JANDY_MACRO = tuple(f"macro{n}" for n in range(1, 7))

JANDY = BrandProfile(
    brand=AUTELIS_JANDY,
    key="jandy",
    names_endpoint="names.xml",
    names_format="xml",
    setpoint_param="temp",
    heat_section="equipment",
    heat_param="value",
    heat_max_mode=2,          # 0=Off 1=Enabled 2=On
    solar_temp_tag="solartemp",
    supports_climate=True,
    roles=_roles(
        circuit=("pump", "spa", "waterfall", "cleaner", "solarht", *_JANDY_AUX),
        heat=("poolht", "poolht2", "spaht"),
        setpoint=("poolsp", "poolsp2", "spasp"),
        temperature=("pooltemp", "spatemp", "airtemp", "solartemp"),
        # pumplo/htpmp/auxx: undocumented, always empty in every capture.
        # macroN: status.xml exposes them, but no doc or capture proves what name
        # set.cgi accepts (the wiki only ever documents "1tch3"). Exposing them
        # would ship switches that silently do nothing.
        ignore=("pumplo", "htpmp", "auxx", "tempunits", *_JANDY_MACRO),
    ),
    heat_sets=(
        HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"),
        HeatSet("Spa Heat", "spatemp", "spasp", "spaht"),
    ),
    # Preserves the exact entity names upstream's CIRCUITS and TEMP_SENSORS produced.
    # The aux fallbacks are only reached when names.xml is absent (older firmware);
    # a real Jandy names.xml always wins.
    default_names={
        **_TEMP_NAMES,
        "pump": "Pool",
        "spa": "Spa",
        "solarht": "Solar Heating",
        "cleaner": "Cleaner",
        "waterfall": "Waterfall",
        **{f"aux{n}": f"Aux {n}" for n in range(1, 24)},
    },
)

_PENTAIR_CIRCUITS = tuple(f"circuit{n}" for n in range(1, 21))
_PENTAIR_FEATURES = tuple(f"feature{n}" for n in range(1, 11))

PENTAIR = BrandProfile(
    brand=AUTELIS_PENTAIR,
    key="pentair",
    names_endpoint="names.xml",
    names_format="xml",
    setpoint_param="temp",
    heat_section="temp",      # NOT equipment -- this is the Pentair trap
    heat_param="hval",        # NOT value=
    heat_max_mode=3,          # 3 = solar-only; upstream's 0/1/2 map KeyErrors here
    solar_temp_tag="soltemp",  # NOT solartemp
    supports_climate=True,
    roles=_roles(
        circuit=(*_PENTAIR_CIRCUITS, *_PENTAIR_FEATURES),
        heat=("poolht", "spaht"),
        setpoint=("poolsp", "spasp"),
        temperature=("pooltemp", "spatemp", "airtemp", "soltemp"),
        ignore=("htstatus", "htpump", "maxplsp", "tempunits"),
    ),
    heat_sets=(
        HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"),
        HeatSet("Spa Heat", "spatemp", "spasp", "spaht"),
    ),
    default_names=dict(_TEMP_NAMES),
)

_HAYWARD_AUX = tuple(f"aux{n}" for n in range(1, 16))

HAYWARD = BrandProfile(
    brand=AUTELIS_HAYWARD,
    key="hayward",
    # names.xml 404s, but the owner's aux labels are NOT unavailable -- they live on
    # the Autelis Setup page, editable and persisted on the unit, and the device
    # renders them into the HTML it serves. Rename an aux there and it flows into
    # Home Assistant, exactly as names.xml does for Jandy.
    names_endpoint="settings.htm",
    names_format="html",
    setpoint_param=None,      # any temp= param returns HTTP 500, even on a valid name
    heat_section=None,
    heat_param=None,
    heat_max_mode=0,
    solar_temp_tag="solartemp",
    supports_climate=False,   # no setpoint can be written OR read; see the spec
    roles=_roles(
        # aux5 is a normal circuit. It refused a write during testing only because
        # the pool was in a scheduled spa window and a cleaner cannot run with the
        # valves diverted. Interlocked != read-only.
        circuit=("pump", "spa", "valve3", "valve4", "schlor", *_HAYWARD_AUX),
        # Confirmed read-only by write-and-poll: poolht held 100 polls, waterfall 60.
        # poolht reports RUNNING, not ENABLED.
        readonly=("poolht", "waterfall"),
        temperature=("pooltemp", "spatemp", "airtemp", "solartemp"),
        ignore=("tempunits",),
    ),
    # FALLBACK ONLY. The real aux labels come from settings.htm (see names.py) --
    # they are the owner's, not ours. These are used solely when that scrape fails,
    # so a parse problem degrades to generic names instead of breaking setup.
    #
    # The fixed circuits below are genuinely static: they are the labels the Autelis
    # firmware prints for its own non-aux equipment, and the Setup page offers no way
    # to change them.
    default_names={
        **_TEMP_NAMES,
        "pump": "Filter Pump",
        "spa": "Spa",
        "waterfall": "Waterfall",
        "valve3": "Valve 3",
        "valve4": "Valve 4",
        "poolht": "Heater",
        "schlor": "SuperChlorinate",
        **{f"aux{n}": f"Aux {n}" for n in range(1, 16)},
    },
)

PROFILES: dict[int, BrandProfile] = {
    AUTELIS_JANDY: JANDY,
    AUTELIS_PENTAIR: PENTAIR,
    AUTELIS_HAYWARD: HAYWARD,
}


def _tags(root: Element, section: str) -> set[str]:
    node = root.find(section)
    return set() if node is None else {child.tag for child in node}


def detect_brand(root: Element) -> int:
    """Identify the controller family from the shape of status.xml.

    Never branch on <model>: it is the *pool controller's* model, not the Autelis
    unit's. Pentair documents an enum 0-5 yet real EasyTouch units report 13; Jandy
    reports 4-digit strings (6520, 6525); a disconnected Jandy reports 0.

    Returns AUTELIS_UNKNOWN when no positive marker is found. Callers must treat
    that as "not ready", never as a default brand.
    """
    equipment = _tags(root, "equipment")

    if "circuit1" in equipment:
        return AUTELIS_PENTAIR
    if equipment & {"valve3", "schlor"}:
        return AUTELIS_HAYWARD
    if "cleaner" in equipment:
        return AUTELIS_JANDY

    system = _tags(root, "system")
    if system & {"dip", "vbat", "lowbat"}:
        return AUTELIS_JANDY
    if system & {"haddr", "systime"}:
        return AUTELIS_PENTAIR

    return AUTELIS_UNKNOWN
