"""Fixtures for the Snowtire tests."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant.components.weather import (
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_TEMPERATURE_UNIT,
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
    WeatherEntityFeature,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.snowtire.const import (
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_WEATHER,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"

AREA_NAME = "Test area"
WEATHER_ENTITY_ID = "weather.test"
ENTRY_ID = "test_entry"
SENSOR_ENTITY_ID = "binary_sensor.tires_for_test_area"
DAYS = 2


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for the tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=ENTRY_ID,
        title=AREA_NAME,
        data={CONF_NAME: AREA_NAME},
        options={
            CONF_WEATHER: WEATHER_ENTITY_ID,
            CONF_DAYS: DAYS,
            CONF_CREATE_NOTIFICATIONS: True,
        },
    )


@pytest.fixture
def mock_notification() -> Generator[MagicMock]:
    """Capture persistent notifications."""
    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as mock_create:
        yield mock_create


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add a config entry to Home Assistant and set it up."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def set_weather_state(
    hass: HomeAssistant,
    temperature: float | None = 10,
    unit: str = UnitOfTemperature.CELSIUS,
    features: int | str = WeatherEntityFeature.FORECAST_DAILY,
    state: str = "sunny",
) -> None:
    """Set the state of the mocked weather entity."""
    hass.states.async_set(
        WEATHER_ENTITY_ID,
        state,
        {
            ATTR_WEATHER_TEMPERATURE: temperature,
            ATTR_WEATHER_TEMPERATURE_UNIT: unit,
            ATTR_SUPPORTED_FEATURES: features,
        },
    )


def mock_forecast_service(
    hass: HomeAssistant, forecast: list[dict[str, Any]] | None = None
) -> list[ServiceCall]:
    """Replace the weather forecast service with a mock returning the forecast."""
    return async_mock_service(
        hass,
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        response={WEATHER_ENTITY_ID: {"forecast": forecast or []}},
        supports_response=SupportsResponse.ONLY,
    )
