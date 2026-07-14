"""Phantom entities from the names.xml era must be removed cleanly, not orphaned."""

import pytest

from custom_components.autelis_pool import async_remove_stale_entities


class _Registry:
    def __init__(self, entries):
        self.entries = dict(entries)
        self.removed = []

    def async_remove(self, entity_id):
        self.removed.append(entity_id)
        self.entries.pop(entity_id, None)


class _Entry:
    def __init__(self, unique_id):
        self.unique_id = unique_id


@pytest.mark.asyncio
async def test_removes_entities_no_longer_discovered():
    registry = _Registry(
        {
            "switch.pool": _Entry("autelis 1.2.3.4 pump"),
            "switch.polaris": _Entry("autelis 1.2.3.4 aux1"),  # phantom: aux1 is empty
        }
    )
    live = {"autelis 1.2.3.4 pump"}

    await async_remove_stale_entities(registry, live)

    assert registry.removed == ["switch.polaris"]


@pytest.mark.asyncio
async def test_leaves_entities_from_other_integrations_alone():
    registry = _Registry({"light.kitchen": _Entry("hue-1234")})
    await async_remove_stale_entities(registry, {"autelis 1.2.3.4 pump"})
    assert registry.removed == []
