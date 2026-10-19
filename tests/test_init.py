"""Tests for the Snowtire integration setup."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_RESTORED,
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_UNAVAILABLE,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.snowtire.const import (
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_WEATHER,
    DOMAIN,
)

from .conftest import (
    AREA_NAME,
    DAYS,
    SENSOR_ENTITY_ID,
    WEATHER_ENTITY_ID,
    set_weather_state,
    setup_entry,
)


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test a config entry can be set up and unloaded."""
    await setup_entry(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(SENSOR_ENTITY_ID) is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE
    assert state.attributes[ATTR_RESTORED] is True


async def test_setup_without_yaml(
    hass: HomeAssistant, issue_registry: ir.IssueRegistry
) -> None:
    """Test setting up the integration without YAML does not create issues."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert not hass.config_entries.async_entries(DOMAIN)
    assert not issue_registry.issues


async def test_yaml_import(
    hass: HomeAssistant, issue_registry: ir.IssueRegistry
) -> None:
    """Test YAML configuration is imported and flagged as deprecated."""
    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: [
                {
                    CONF_WEATHER: WEATHER_ENTITY_ID,
                    CONF_NAME: AREA_NAME,
                    CONF_DAYS: DAYS,
                    CONF_CREATE_NOTIFICATIONS: False,
                    # Legacy option, accepted and ignored.
                    CONF_UNIQUE_ID: "legacy",
                },
                {CONF_WEATHER: "weather.other"},
            ]
        },
    )
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    assert {entry.title for entry in entries} == {
        AREA_NAME,
        hass.config.location_name,
    }
    first = next(entry for entry in entries if entry.title == AREA_NAME)
    assert first.options == {
        CONF_WEATHER: WEATHER_ENTITY_ID,
        CONF_DAYS: DAYS,
        CONF_CREATE_NOTIFICATIONS: False,
    }

    issue = issue_registry.async_get_issue(
        HOMEASSISTANT_DOMAIN, f"deprecated_yaml_{DOMAIN}"
    )
    assert issue is not None
    assert issue.translation_key == "deprecated_yaml"
    assert issue.issue_domain == DOMAIN


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the diagnostics of a config entry."""
    set_weather_state(hass, temperature=3)
    await setup_entry(hass, mock_config_entry)

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    assert diagnostics["entry"] == {
        "title": AREA_NAME,
        "data": {CONF_NAME: AREA_NAME},
        "options": dict(mock_config_entry.options),
    }
    assert diagnostics["weather"]["entity_id"] == WEATHER_ENTITY_ID
    assert diagnostics["weather"]["attributes"]["temperature"] == 3
