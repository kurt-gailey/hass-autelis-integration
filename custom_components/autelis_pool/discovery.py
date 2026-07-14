"""Presence-discovery: which equipment does this controller actually have?

The brand profile says what a tag *is*. This module says whether it *exists*, by
reading status.xml exactly the way the Autelis firmware's own web UI does: a tag
with an empty value is equipment that is not installed.

names.xml is a LABEL SIDE-TABLE. It never creates an entity. On Jandy, a cleaner
assigned to AUX1 leaves <aux1> empty and routes state through <cleaner>, while
names.xml still calls aux1 "Cleaner" -- so building entities from names.xml keys
produces phantom switches backed by nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree.ElementTree import Element

from .brands import (
    ROLE_CIRCUIT,
    ROLE_READONLY,
    ROLE_TEMPERATURE,
    BrandProfile,
    HeatSet,
)
from .names import is_placeholder

_SECTIONS = ("system", "equipment", "temp")


@dataclass(frozen=True)
class EntityDescriptor:
    """One entity to create."""

    platform: str   # "switch" | "sensor" | "binary_sensor"
    tag: str
    name: str
    enabled_default: bool = True


def _present(node: Element | None) -> bool:
    """True when the tag exists AND carries a value. Empty => not installed."""
    return node is not None and node.text is not None and node.text.strip() != ""


def snapshot(root: Element, profile: BrandProfile) -> dict[str, dict[str, str]]:
    """Build a fresh state snapshot. Absent tags are absent -- never stale.

    The previous implementation updated dicts in place and never cleared them, so a
    tag that went empty kept its old value and absent equipment still looked
    installed. Discovery reads presence from here, so that had to go.

    Note `is not None` rather than a truth test: an Element with no children is falsy
    today, but Python deprecated that and will make Elements always truthy. `find(x)
    or []` therefore works by accident and is scheduled to break.
    """
    snap: dict[str, dict[str, str]] = {}
    for section in _SECTIONS:
        node = root.find(section)
        snap[section] = (
            {}
            if node is None
            else {
                child.tag: child.text.strip()
                for child in node
                if child.text is not None and child.text.strip() != ""
            }
        )
    return snap


def _label(tag: str, profile: BrandProfile, names: dict[str, str]) -> tuple[str, bool]:
    """Return (name, enabled_default) for a tag.

    A relay can be installed but unassigned -- the owner never wired it to anything --
    in which case the device still hands back a placeholder label ("AUX5", "AUX 2").
    Pools differ wildly: one owner uses no aux at all, another uses every one. So we
    neither hide these nor clutter everyone's dashboard with them. They are created
    DISABLED, one click from being switched on.

    An important asymmetry: only a placeholder that came FROM THE DEVICE means
    "unassigned". Our own fallback names are not evidence of anything, so a tag with no
    device label stays enabled -- status.xml says the equipment is installed, and that
    is all we know.
    """
    if tag in names:
        label = names[tag]
        return label, not is_placeholder(label)

    # Some circuits are opt-in: the controller reports them whether or not the owner
    # uses them, so presence proves nothing and only a name does. Jandy always returns
    # macro1-macro6. Without this, every Jandy user grows six switches that do nothing.
    if tag in profile.requires_label:
        return profile.default_names.get(tag, tag), False

    return profile.default_names.get(tag, tag), True


def build_inventory(
    root: Element, profile: BrandProfile, names: dict[str, str]
) -> list[EntityDescriptor]:
    """Every entity this controller should expose, from what it actually reports."""
    inventory: list[EntityDescriptor] = []

    equipment = root.find("equipment")
    if equipment is not None:
        for child in equipment:
            if not _present(child):
                continue                      # not installed
            role = profile.role(child.tag)
            if role == ROLE_CIRCUIT:
                platform = "switch"
            elif role == ROLE_READONLY:
                platform = "binary_sensor"
            else:
                continue                      # heat/setpoint are climate's; ignore the rest
            name, enabled = _label(child.tag, profile, names)
            inventory.append(EntityDescriptor(platform, child.tag, name, enabled))

    temp = root.find("temp")
    if temp is not None:
        for child in temp:
            if not _present(child):
                continue
            if profile.role(child.tag) != ROLE_TEMPERATURE:
                continue                      # setpoints belong to climate
            name, _ = _label(child.tag, profile, names)
            inventory.append(EntityDescriptor("sensor", child.tag, name))

    return inventory


def build_heat_sets(root: Element, profile: BrandProfile) -> list[HeatSet]:
    """Climate entities, only where the brand and the hardware both support them."""
    if not profile.supports_climate or profile.heat_section is None:
        return []

    heat_node = root.find(profile.heat_section)
    temp_node = root.find("temp")
    if heat_node is None or temp_node is None:
        return []

    return [
        hs
        for hs in profile.heat_sets
        if _present(heat_node.find(hs.heat_tag))
        and _present(temp_node.find(hs.setpoint_tag))
        and _present(temp_node.find(hs.current_tag))
    ]
