"""Config flow for the Snowtire integration."""

#  Copyright (c) 2024, Andrey "Limych" Khrolenok <andrey@khrolenok.ru>
#  Copyright (c) 2026, Krzysztof Hajdamowicz
#  Creative Commons BY-NC-SA 4.0 International Public License
#  (see LICENSE.md or https://creativecommons.org/licenses/by-nc-sa/4.0/)

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from homeassistant.components.weather import DOMAIN as WEATHER_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .const import (
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_LEGACY_ENTITY_ID,
    CONF_WEATHER,
    DEFAULT_CREATE_NOTIFICATIONS,
    DEFAULT_DAYS,
    DOMAIN,
    MAX_DAYS,
    MIN_DAYS,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

OPTIONS_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_WEATHER): EntitySelector(
            EntitySelectorConfig(domain=WEATHER_DOMAIN)
        ),
        vol.Required(CONF_DAYS, default=DEFAULT_DAYS): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=MIN_DAYS,
                    max=MAX_DAYS,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="days",
                )
            ),
            vol.Coerce(int),
        ),
        vol.Required(
            CONF_CREATE_NOTIFICATIONS, default=DEFAULT_CREATE_NOTIFICATIONS
        ): BooleanSelector(),
    }
)

OPTION_KEYS: Final = (CONF_WEATHER, CONF_DAYS, CONF_CREATE_NOTIFICATIONS)


class SnowtireConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Snowtire."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SnowtireOptionsFlow:  # noqa: ARG004
        """Get the options flow for this handler."""
        return SnowtireOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self._async_create_snowtire_entry(user_input[CONF_NAME], user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=self.hass.config.location_name
                ): TextSelector(),
            }
        ).extend(OPTIONS_SCHEMA.schema)
        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import a config entry from YAML configuration."""
        name = import_data.get(CONF_NAME) or self.hass.config.location_name
        return self._async_create_snowtire_entry(name, import_data)

    @callback
    def _async_create_snowtire_entry(
        self, name: str, values: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Create a config entry, aborting if an identical one already exists."""
        options = {key: values[key] for key in OPTION_KEYS if key in values}
        self._async_abort_entries_match(
            {CONF_NAME: name, CONF_WEATHER: options[CONF_WEATHER]}
        )
        data = {CONF_NAME: name}
        if CONF_LEGACY_ENTITY_ID in values:
            data[CONF_LEGACY_ENTITY_ID] = values[CONF_LEGACY_ENTITY_ID]
        return self.async_create_entry(title=name, data=data, options=options)


class SnowtireOptionsFlow(OptionsFlowWithReload):
    """Handle the options flow for Snowtire."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
            description_placeholders={"name": self.config_entry.title},
        )
