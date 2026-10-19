"""Diagnostics support for the Snowtire integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import CONF_WEATHER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import SnowtireConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SnowtireConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    weather_state = hass.states.get(entry.options[CONF_WEATHER])
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "weather": weather_state.as_dict() if weather_state is not None else None,
    }
