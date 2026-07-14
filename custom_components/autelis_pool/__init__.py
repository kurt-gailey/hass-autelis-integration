"""Autelis pool controller integration."""

from __future__ import annotations

import logging
import re
from datetime import timedelta

from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.util import Throttle

from .api import AutelisPoolAPI
from .brands import PROFILES, detect_brand
from .const import AUTELIS_UNKNOWN, DOMAIN, PLATFORMS, STATE_AUTO, STATE_SERVICE
from .discovery import build_heat_sets, build_inventory, snapshot
from .names import parse_aux_labels_html, parse_names_xml

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

_SCHEME = re.compile(r"^https?://", re.IGNORECASE)


def clean_host(host: str) -> str:
    """The host with any scheme and trailing slash removed.

    Used for unique_ids and log lines, and kept stable whether or not the user typed
    'http://'. A bare IP or 'ip:port' passes through unchanged, so existing users'
    entity identities do not move.
    """
    return _SCHEME.sub("", host.strip()).rstrip("/")


def base_url(host: str) -> str:
    """A well-formed base URL ending in '/', whatever the user pasted in.

    People routinely paste 'http://1.2.3.4' into the host field. Without this the code
    built 'http://http://1.2.3.4/', and aiohttp tried to resolve a host literally named
    'http' on port 80 -- the "Cannot connect to host http:80" DNS timeout. An explicit
    https:// is preserved; anything else gets http://.
    """
    host = host.strip()
    if not _SCHEME.match(host):
        host = f"http://{host}"
    return host.rstrip("/") + "/"


async def async_setup_entry(hass, entry):
    """Set up one Autelis controller."""
    raw_host = entry.data[CONF_HOST]
    password = entry.data[CONF_PASSWORD]
    # Normalise here rather than only in the config flow, so an entry already saved with
    # a scheme in the host (e.g. "http://172.16.20.27") is repaired on the next load
    # without the user having to remove and re-add it.
    data = AutelisData(
        clean_host(raw_host), AutelisPoolAPI(hass, base_url(raw_host), password)
    )

    await data.async_refresh()

    if data.brand == AUTELIS_UNKNOWN:
        # Sparse or unreachable XML. Guessing a brand here would build a wrong
        # entity set and persist it into the registry, so refuse and retry later.
        raise ConfigEntryNotReady(
            f"Could not identify the pool controller at {data.host}. "
            "It may be disconnected or still starting up."
        )

    live = {f"autelis {data.host} {item.tag}" for item in data.inventory}
    live |= {f"autelis {data.host} {hs.current_tag}" for hs in data.heat_sets}
    async_remove_stale_entities(er.async_get(hass), entry.entry_id, live)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def async_remove_stale_entities(registry, config_entry_id, live_unique_ids: set[str]) -> None:
    """Remove Autelis entities that discovery no longer produces.

    Building switches from names.xml created entities for aux circuits whose
    status.xml tag was empty -- equipment the owner does not have. They rendered as
    permanently-off switches. Discovery does not produce them, so they must be retired
    rather than left orphaned in the registry.

    Scoped to this config entry via async_entries_for_config_entry, so it only ever
    touches this integration's own entities -- no unique_id prefix guessing, and no
    reaching into registry internals.
    """
    for entry in er.async_entries_for_config_entry(registry, config_entry_id):
        if entry.unique_id not in live_unique_ids:
            _LOGGER.info(
                "Removing stale Autelis entity %s (%s)", entry.entity_id, entry.unique_id
            )
            registry.async_remove(entry.entity_id)


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
