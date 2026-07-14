"""Constants for the autelis integration."""
import logging
from homeassistant.const import Platform

_LOGGER = logging.getLogger(__package__)

DOMAIN = "autelis_pool"
AUTELIS_HOST = "host"
AUTELIS_PASSWORD = "password"

AUTELIS_USERNAME = "admin"

AUTELIS_PLATFORMS = ["sensor", "switch", "climate"] # ["binary_sensor", "climate", "sensor", "weather"]

# Which type of pool controller the Autelis unit is bridged to.
# Jandy/Pentair values match upstream's feature/pentair-support branch.
AUTELIS_JANDY = 0
AUTELIS_PENTAIR = 1
AUTELIS_HAYWARD = 2
AUTELIS_UNKNOWN = -1

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
]

STATE_SERVICE = "service"
STATE_AUTO = "auto"

MAX_TEMP = 104
MIN_TEMP = 34