"""Preserve entities when converting the legacy shared YAML entry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_LEGACY_ENTITY_ID,
    CONF_WEATHER,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@callback
def async_prepare_yaml_imports(
    hass: HomeAssistant, yaml_entries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reuse the old entry for its first sensor and prepare the remaining imports."""
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.source == SOURCE_IMPORT
    ]
    legacy_entry = next(
        (entry for entry in entries if not entry.data and not entry.options), None
    )
    registry = er.async_get(hass)
    imports = []
    for index, yaml_entry in enumerate(yaml_entries):
        # Look up old registry IDs on every startup, so an interrupted migration
        # can resume even after its first entry has already been converted.
        entity_id = _legacy_entity_id(registry, entries, yaml_entry, index)
        if legacy_entry is not None and index == 0:
            name = yaml_entry.get(CONF_NAME) or hass.config.location_name
            hass.config_entries.async_update_entry(
                legacy_entry,
                title=name,
                data={CONF_NAME: name},
                options={
                    key: yaml_entry[key]
                    for key in (CONF_WEATHER, CONF_DAYS, CONF_CREATE_NOTIFICATIONS)
                    if key in yaml_entry
                },
                version=2,
            )
            if entity_id is not None:
                registry.async_update_entity(
                    entity_id, new_unique_id=legacy_entry.entry_id
                )
            continue

        import_data = dict(yaml_entry)
        if entity_id is not None:
            import_data[CONF_LEGACY_ENTITY_ID] = entity_id
        imports.append(import_data)
    return imports


@callback
def _legacy_entity_id(
    registry: er.EntityRegistry,
    entries: list[ConfigEntry],
    yaml_entry: dict[str, Any],
    index: int,
) -> str | None:
    """Find the sensor created at this YAML index by the old shared entry."""
    for entry in entries:
        unique_id = yaml_entry.get(CONF_UNIQUE_ID, f"{entry.entry_id}-{index}")
        entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
        if entity_id is not None and (
            registry.async_get(entity_id).config_entry_id == entry.entry_id
        ):
            return entity_id
    return None


@callback
def async_migrate_yaml_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move an old registry record before the new entry creates its sensor."""
    if (entity_id := entry.data.get(CONF_LEGACY_ENTITY_ID)) is None:
        return
    registry = er.async_get(hass)
    if (registered := registry.async_get(entity_id)) is not None and (
        registered.platform == DOMAIN
    ):
        registry.async_update_entity(
            entity_id,
            config_entry_id=entry.entry_id,
            new_unique_id=entry.entry_id,
        )
    data = dict(entry.data)
    data.pop(CONF_LEGACY_ENTITY_ID)
    hass.config_entries.async_update_entry(entry, data=data)
