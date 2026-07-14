from homeassistant.helpers import aiohttp_client
from aiohttp import BasicAuth
import asyncio

from xml.etree import ElementTree

from .brands import BrandProfile
from .const import _LOGGER, AUTELIS_USERNAME


class CommandNotSupported(Exception):
    """The brand has no wire format for this command (e.g. Hayward setpoints)."""


def build_command(profile: BrandProfile, kind: str, tag: str, value) -> str:
    """Build a set.cgi query for one command, in this brand's dialect.

    Pure and synchronous so the wire format can be tested without HTTP -- which
    matters, because we cannot exercise Jandy or Pentair hardware.

    Note that a `1` response from set.cgi means the NAME was recognised, not that
    the write took effect. Callers must re-read status.xml; never infer state here.
    """
    if kind == "circuit":
        return f"set.cgi?name={tag}&value={value}"

    if kind == "setpoint":
        if profile.setpoint_param is None:
            raise CommandNotSupported(
                f"{profile.key} has no setpoints; a temp= param returns HTTP 500"
            )
        return f"set.cgi?name={tag}&{profile.setpoint_param}={value}"

    if kind == "heat":
        if profile.heat_param is None:
            raise CommandNotSupported(f"{profile.key} cannot set heat mode via set.cgi")
        return f"set.cgi?name={tag}&{profile.heat_param}={value}"

    raise CommandNotSupported(f"unknown command kind: {kind}")


class AutelisPoolAPI:
    """Simple XML wrapper for Autelis's API."""

    def __init__(self,hass, api_url, password):
        """Initialize Autelis API and set params needed later."""
        self.api_url = api_url
        self.password = password
        self.available = False
        self.error_logged = False
        self.session = aiohttp_client.async_get_clientsession(hass)

    async def get(self, endpoint, optional: bool = False):
        """GET an endpoint and return parsed XML, or None.

        `optional=True` means a 404 is an expected answer, not an error: names.xml,
        chem.xml, pumps.xml and lights.xml are later firmware additions and are
        absent on Hayward and on older Jandy units.
        """
        kwargs = {}
        if self.password is not None:
            kwargs = {"auth": BasicAuth(AUTELIS_USERNAME, password=self.password)}

        url = self.api_url + endpoint
        try:
            response = await self.session.get(url, **kwargs)
            if optional and response.status == 404:
                return None
            response.raise_for_status()

            self.available = True
            self.error_logged = False
            return ElementTree.fromstring(await response.text())
        except Exception as conn_exc:  # pylint: disable=broad-except
            if not self.error_logged:
                _LOGGER.error(
                    "Failed to get Autelis status from %s: %s", endpoint, conn_exc
                )
            self.error_logged = True
            self.available = False
            return None

    async def get_text(self, endpoint, optional: bool = False):
        """GET an endpoint as raw text. Hayward keeps its aux labels in HTML, not XML."""
        kwargs = {}
        if self.password is not None:
            kwargs = {"auth": BasicAuth(AUTELIS_USERNAME, password=self.password)}

        try:
            response = await self.session.get(self.api_url + endpoint, **kwargs)
            if optional and response.status == 404:
                return None
            response.raise_for_status()
            return await response.text()
        except Exception as conn_exc:  # pylint: disable=broad-except
            # Labels are a nicety; never let them break setup.
            _LOGGER.debug("Could not fetch %s: %s", endpoint, conn_exc)
            return None

    async def send(self, profile, kind, tag, value):
        """Send one command. Returns True only if the device accepted the NAME.

        It does NOT mean the write took effect -- Hayward returns 1 for read-only
        equipment, and any panel may refuse a circuit for interlock reasons. State
        must come from the next status.xml poll.
        """
        endpoint = build_command(profile, kind, tag, value)

        kwargs = {}
        if self.password is not None:
            kwargs = {"auth": BasicAuth(AUTELIS_USERNAME, password=self.password)}

        try:
            response = await self.session.get(self.api_url + endpoint, **kwargs)
            response.raise_for_status()
            self.available = True
            self.error_logged = False
        except Exception as conn_exc:  # pylint: disable=broad-except
            if not self.error_logged:
                _LOGGER.error("Failed to send Autelis command %s: %s", endpoint, conn_exc)
            self.error_logged = True
            self.available = False
            return False

        return (await response.text()).strip() == "1"

