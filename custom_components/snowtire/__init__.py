"""
The Snowtire integration.

Decides whether it is time to change car tires between summer and winter ones
based on the weather forecast.

For more details about this integration, please refer to the documentation at
https://github.com/KrzysztofHajdamowicz/ha-snowtire
"""

#  Copyright (c) 2020-2024, Andrey "Limych" Khrolenok <andrey@khrolenok.ru>
#  Copyright (c) 2026, Krzysztof Hajdamowicz
#  Creative Commons BY-NC-SA 4.0 International Public License
#  (see LICENSE.md or https://creativecommons.org/licenses/by-nc-sa/4.0/)

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.weather import DOMAIN as WEATHER_DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv, issue_registry as ir
import voluptuous as vol

from .const import (
    BREAKS_IN_HA_VERSION,
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_WEATHER,
    DEFAULT_CREATE_NOTIFICATIONS,
    DEFAULT_DAYS,
    DOMAIN,
    MAX_DAYS,
    MIN_DAYS,
    NAME,
    PLATFORMS,
)
from .migration import async_migrate_yaml_entity, async_prepare_yaml_imports

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

type SnowtireConfigEntry = ConfigEntry

YAML_ENTRY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_WEATHER): cv.entity_domain(WEATHER_DOMAIN),
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_DAYS, max=MAX_DAYS)
        ),
        vol.Optional(
            CONF_CREATE_NOTIFICATIONS, default=DEFAULT_CREATE_NOTIFICATIONS
        ): cv.boolean,
        # Used only to locate existing registry records during legacy migration.
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [YAML_ENTRY_SCHEMA])}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import YAML configuration into config entries (deprecated)."""
    if (yaml_entries := config.get(DOMAIN)) is None:
        return True

    for yaml_entry in async_prepare_yaml_imports(hass, yaml_entries):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=yaml_entry
            )
        )

    ir.async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        breaks_in_ha_version=BREAKS_IN_HA_VERSION,
        is_fixable=False,
        is_persistent=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={
            "domain": DOMAIN,
            "integration_title": NAME,
        },
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: SnowtireConfigEntry) -> bool:
    """Set up Snowtire from a config entry."""
    if CONF_WEATHER not in entry.options:
        message = (
            "Restore the legacy snowtire: YAML configuration and restart Home "
            "Assistant to migrate this entry before removing the YAML section."
        )
        raise ConfigEntryError(message)
    async_migrate_yaml_entity(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: SnowtireConfigEntry) -> bool:
    """Upgrade config entries; legacy YAML is converted during integration setup."""
    if entry.version == 1:
        hass.config_entries.async_update_entry(entry, version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SnowtireConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
