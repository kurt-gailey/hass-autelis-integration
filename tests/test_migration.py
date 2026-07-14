"""Phantom entities from the names.xml era must be removed cleanly, not orphaned.

These tests drive the REAL Home Assistant entity registry, not a hand-rolled fake.
An earlier version used a fake whose attribute happened to be `.entries` -- the same
name the buggy code reached for -- so the mock agreed with the bug and it shipped
(`AttributeError: 'EntityRegistry' object has no attribute 'entries'` on a live install).
A fake that mirrors the implementation proves nothing; exercise the real API.
"""

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autelis_pool import async_remove_stale_entities


async def test_removes_only_the_entities_discovery_no_longer_produces(hass):
    entry = MockConfigEntry(domain="autelis_pool")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)

    pump = registry.async_get_or_create(
        "switch", "autelis_pool", "autelis 1.2.3.4 pump", config_entry=entry
    )
    # Phantom: names.xml labelled aux1, but its status.xml tag is empty -- the owner
    # has no such circuit. Not in the live set, so it must be removed.
    phantom = registry.async_get_or_create(
        "switch", "autelis_pool", "autelis 1.2.3.4 aux1", config_entry=entry
    )

    live = {"autelis 1.2.3.4 pump"}
    async_remove_stale_entities(registry, entry.entry_id, live)

    assert registry.async_get(pump.entity_id) is not None       # kept
    assert registry.async_get(phantom.entity_id) is None        # removed


async def test_never_touches_another_config_entrys_entities(hass):
    """Scoped by config entry, so a second Autelis controller -- or any other
    integration -- is out of reach even if its unique_id set does not overlap."""
    ours = MockConfigEntry(domain="autelis_pool")
    ours.add_to_hass(hass)
    other = MockConfigEntry(domain="autelis_pool")
    other.add_to_hass(hass)
    registry = er.async_get(hass)

    theirs = registry.async_get_or_create(
        "switch", "autelis_pool", "autelis 9.9.9.9 pump", config_entry=other
    )

    # An empty live set for OUR entry would delete everything we own -- but nothing of
    # the other entry's.
    async_remove_stale_entities(registry, ours.entry_id, set())

    assert registry.async_get(theirs.entity_id) is not None
