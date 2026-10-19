"""Tests for migration of the legacy shared YAML config entry."""

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.snowtire.const import (
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_WEATHER,
    DOMAIN,
)

from .conftest import (
    DAYS,
    WEATHER_ENTITY_ID,
    mock_forecast_service,
    set_weather_state,
)
from .test_binary_sensor import forecast_entry


@pytest.mark.parametrize("interrupted", [False, True])
@pytest.mark.parametrize("disabled", [False, True])
@pytest.mark.parametrize("custom_unique_id", [None, "custom_work_id"])
async def test_shared_yaml_migration(
    hass: HomeAssistant,
    *,
    interrupted: bool,
    disabled: bool,
    custom_unique_id: str | None,
) -> None:
    """Split multiple sensors, preserve customizations, and resume after interruption."""
    configurations = [
        {
            CONF_NAME: name,
            CONF_WEATHER: WEATHER_ENTITY_ID,
            CONF_DAYS: DAYS,
            CONF_CREATE_NOTIFICATIONS: False,
        }
        for name in ("Home", "Work")
    ]
    if custom_unique_id is not None:
        configurations[1][CONF_UNIQUE_ID] = custom_unique_id
    first_options = {
        key: value for key, value in configurations[0].items() if key != CONF_NAME
    }
    legacy_entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="legacy_shared_entry",
        source=SOURCE_IMPORT,
        title="Home" if interrupted else "configuration.yaml",
        data={CONF_NAME: "Home"} if interrupted else {},
        options=first_options if interrupted else {},
        version=2 if interrupted else 1,
    )
    legacy_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    first = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        legacy_entry.entry_id if interrupted else f"{legacy_entry.entry_id}-0",
        suggested_object_id="existing_home_tires",
        config_entry=legacy_entry,
    )
    second = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        custom_unique_id or f"{legacy_entry.entry_id}-1",
        suggested_object_id="existing_work_tires",
        config_entry=legacy_entry,
        disabled_by=er.RegistryEntryDisabler.USER if disabled else None,
    )
    registry.async_update_entity(second.entity_id, name="Tires for my commute")
    assert await async_setup_component(hass, "weather", {})
    mock_forecast_service(hass, [forecast_entry(1, 14, 10)])
    set_weather_state(hass, temperature=12)

    assert await async_setup_component(hass, DOMAIN, {DOMAIN: configurations})
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    assert all(entry.version == 2 for entry in entries)
    assert all(entry.state is ConfigEntryState.LOADED for entry in entries)
    assert all(set(entry.data) == {CONF_NAME} for entry in entries)
    assert hass.states.get(first.entity_id).state == STATE_OFF
    work = next(entry for entry in entries if entry.title == "Work")
    migrated = registry.async_get(second.entity_id)
    assert migrated.unique_id == work.entry_id
    assert migrated.config_entry_id == work.entry_id
    assert migrated.name == "Tires for my commute"
    if disabled:
        assert migrated.disabled_by is er.RegistryEntryDisabler.USER
        assert hass.states.get(second.entity_id) is None
    else:
        assert hass.states.get(second.entity_id).state == STATE_OFF
    assert {
        entity.entity_id
        for entity in registry.entities.values()
        if entity.platform == DOMAIN
    } == {first.entity_id, second.entity_id}

    assert await hass.config_entries.async_reload(work.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(second.entity_id).config_entry_id == work.entry_id
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=configurations[1]
    )
    assert result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2


async def test_missing_legacy_yaml_preserves_registry(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Explain missing migration input without dropping the old registered entity."""
    entry = MockConfigEntry(
        domain=DOMAIN, source=SOURCE_IMPORT, title="configuration.yaml", data={}
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    original = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        f"{entry.entry_id}-0",
        suggested_object_id="existing_tires",
        config_entry=entry,
    )

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert registry.async_get(original.entity_id) is not None
    assert "Restore the legacy snowtire:" in caplog.text
    assert "KeyError" not in caplog.text
