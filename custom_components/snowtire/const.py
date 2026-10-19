"""Constants for the Snowtire integration."""

from typing import Final

from homeassistant.const import Platform

NAME: Final = "Snowtire Sensor"
DOMAIN: Final = "snowtire"
ISSUE_URL: Final = "https://github.com/KrzysztofHajdamowicz/ha-snowtire/issues"

PLATFORMS: Final = [Platform.BINARY_SENSOR]

# Configuration and options
CONF_WEATHER: Final = "weather"
CONF_DAYS: Final = "days"
CONF_CREATE_NOTIFICATIONS: Final = "create_notifications"
CONF_LEGACY_ENTITY_ID: Final = "legacy_entity_id"

DEFAULT_DAYS: Final = 7
MIN_DAYS: Final = 1
MAX_DAYS: Final = 30
DEFAULT_CREATE_NOTIFICATIONS: Final = True

# Decision thresholds (degrees Celsius)
TEMP_FREEZE: Final = 0.5
"""Any forecast temperature at or below this value means winter tires."""
TEMP_CHANGE: Final = 7.0
"""Average temperature below this value means winter tires."""
TEMP_ERROR: Final = 0.5
"""Hysteresis around TEMP_CHANGE to avoid flapping."""

BREAKS_IN_HA_VERSION: Final = "2027.1.0"
"""Home Assistant version in which YAML configuration support will be removed."""
