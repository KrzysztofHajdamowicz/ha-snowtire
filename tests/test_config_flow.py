"""Tests for the Snowtire config and options flows."""

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.snowtire.const import (
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_WEATHER,
    DEFAULT_CREATE_NOTIFICATIONS,
    DEFAULT_DAYS,
    DOMAIN,
)

from .conftest import AREA_NAME, WEATHER_ENTITY_ID, setup_entry


async def test_user_flow(hass: HomeAssistant) -> None:
    """Test creating an entry via the UI."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: AREA_NAME,
            CONF_WEATHER: WEATHER_ENTITY_ID,
            CONF_DAYS: 3.0,
            CONF_CREATE_NOTIFICATIONS: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == AREA_NAME
    assert result["data"] == {CONF_NAME: AREA_NAME}
    assert result["options"] == {
        CONF_WEATHER: WEATHER_ENTITY_ID,
        CONF_DAYS: 3,
        CONF_CREATE_NOTIFICATIONS: False,
    }
    assert isinstance(result["options"][CONF_DAYS], int)
    assert result["result"].state is config_entries.ConfigEntryState.LOADED


async def test_user_flow_duplicate(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that an identical entry cannot be created twice."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: AREA_NAME,
            CONF_WEATHER: WEATHER_ENTITY_ID,
            CONF_DAYS: 5,
            CONF_CREATE_NOTIFICATIONS: True,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_flow(hass: HomeAssistant) -> None:
    """Test importing a YAML configuration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={CONF_WEATHER: WEATHER_ENTITY_ID},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == hass.config.location_name
    assert result["data"] == {CONF_NAME: hass.config.location_name}
    assert result["options"] == {CONF_WEATHER: WEATHER_ENTITY_ID}

    # Importing the same configuration again (e.g. after a restart) is a no-op.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={CONF_WEATHER: WEATHER_ENTITY_ID},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_import_flow_full(hass: HomeAssistant) -> None:
    """Test importing a YAML configuration with all options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_NAME: AREA_NAME,
            CONF_WEATHER: WEATHER_ENTITY_ID,
            CONF_DAYS: DEFAULT_DAYS,
            CONF_CREATE_NOTIFICATIONS: DEFAULT_CREATE_NOTIFICATIONS,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == AREA_NAME
    assert result["options"] == {
        CONF_WEATHER: WEATHER_ENTITY_ID,
        CONF_DAYS: DEFAULT_DAYS,
        CONF_CREATE_NOTIFICATIONS: DEFAULT_CREATE_NOTIFICATIONS,
    }


async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test changing the options of an existing entry reloads it."""
    await setup_entry(hass, mock_config_entry)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["description_placeholders"] == {"name": AREA_NAME}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_WEATHER: "weather.other",
            CONF_DAYS: 10,
            CONF_CREATE_NOTIFICATIONS: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {
        CONF_WEATHER: "weather.other",
        CONF_DAYS: 10,
        CONF_CREATE_NOTIFICATIONS: False,
    }
    assert mock_config_entry.state is config_entries.ConfigEntryState.LOADED
