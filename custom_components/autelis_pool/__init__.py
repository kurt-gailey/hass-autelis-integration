"""Autelis pool controller integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import Throttle

from .api import AutelisPoolAPI
from .brands import PROFILES, detect_brand
from .const import AUTELIS_UNKNOWN, DOMAIN, PLATFORMS, STATE_AUTO, STATE_SERVICE
from .discovery import build_heat_sets, build_inventory, snapshot
from .names import parse_aux_labels_html, parse_names_xml

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)


async def async_setup_entry(hass, entry):
    """Set up one Autelis controller."""
    host = entry.data[CONF_HOST]
    password = entry.data[CONF_PASSWORD]
    # The API is injected rather than built inside AutelisData, so the polling and
    # discovery logic can be tested without a running Home Assistant.
    data = AutelisData(host, AutelisPoolAPI(hass, f"http://{host}/", password))

    await data.async_refresh()

    if data.brand == AUTELIS_UNKNOWN:
        # Sparse or unreachable XML. Guessing a brand here would build a wrong
        # entity set and persist it into the registry, so refuse and retry later.
        raise ConfigEntryNotReady(
            f"Could not identify the pool controller at {data.host}. "
            "It may be disconnected or still starting up."
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    """Unload one controller, leaving any others alone."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


class AutelisData:
    """Polls one controller and holds its latest snapshot."""

    def __init__(self, host, api):
        self.host = host
        self.api = api

        self.brand = AUTELIS_UNKNOWN
        self.profile = None
        self.names: dict[str, str] = {}
        self.inventory = []
        self.heat_sets = []
        self.equipment: dict[str, str] = {}
        self.sensors: dict[str, str] = {}
        self.system: dict[str, str] = {}
        self.mode = STATE_SERVICE

    async def async_refresh(self):
        """Poll status.xml and rebuild the snapshot from scratch."""
        status = await self.api.get("status.xml")
        if status is None:
            return

        if self.profile is None:
            # Brand and inventory are resolved ONCE, at setup. Re-running discovery
            # every poll would let a transient sparse response churn the entity
            # registry.
            self.brand = detect_brand(status)
            if self.brand == AUTELIS_UNKNOWN:
                return
            self.profile = PROFILES[self.brand]
            self.names = await self._async_load_names()
            self.inventory = build_inventory(status, self.profile, self.names)
            self.heat_sets = build_heat_sets(status, self.profile)
            _LOGGER.info(
                "Detected %s controller at %s: %d entities",
                self.profile.key,
                self.host,
                len(self.inventory),
            )

        snap = snapshot(status, self.profile)
        self.system, self.equipment, self.sensors = (
            snap["system"],
            snap["equipment"],
            snap["temp"],
        )

        opmode = self.system.get("opmode")
        self.mode = STATE_AUTO if opmode == "0" else STATE_SERVICE

    async def _async_load_names(self) -> dict[str, str]:
        """Fetch the owner's equipment labels, in whichever form this brand keeps them.

        Jandy and Pentair serve names.xml. Hayward 404s that, but keeps its aux labels
        on the Setup page -- editable, persisted on the unit, and rendered into the
        HTML it serves. Either way, these are the OWNER's names, not ours.

        Failure is never fatal: we fall back to generic labels.
        """
        endpoint = self.profile.names_endpoint
        if not endpoint:
            return {}

        if self.profile.names_format == "html":
            return parse_aux_labels_html(
                await self.api.get_text(endpoint, optional=True)
            )
        return parse_names_xml(await self.api.get(endpoint, optional=True))

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update(self):
        """Throttled refresh, called by entities during their update."""
        await self.async_refresh()
