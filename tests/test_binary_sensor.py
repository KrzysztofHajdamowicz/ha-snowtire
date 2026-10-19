"""Tests for the Snowtire binary sensor."""

from datetime import timedelta
import logging
from typing import Any
from unittest.mock import MagicMock

from homeassistant.components.weather import (
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
    WeatherEntityFeature,
)
from homeassistant.const import (
    CONF_TYPE,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
    mock_restore_cache,
)

from custom_components.snowtire.const import CONF_CREATE_NOTIFICATIONS

from .conftest import (
    SENSOR_ENTITY_ID,
    mock_forecast_service,
    set_weather_state,
    setup_entry,
)


def forecast_entry(
    days_ahead: int, high: float | None, low: float | None = None
) -> dict[str, Any]:
    """Return a forecast entry as returned by the weather service."""
    return {
        ATTR_FORECAST_TIME: (dt_util.now() + timedelta(days=days_ahead)).isoformat(),
        ATTR_FORECAST_TEMP: high,
        ATTR_FORECAST_TEMP_LOW: low,
    }


async def test_winter_and_summer(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_notification: MagicMock,
) -> None:
    """Test the sensor state follows the forecast and notifies on changes."""
    await setup_entry(hass, mock_config_entry)

    # Weather entity does not exist yet: unavailable, no exception.
    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    calls = mock_forecast_service(
        hass, [forecast_entry(0, 12), forecast_entry(1, 11, 8)]
    )
    set_weather_state(hass, temperature=10)
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state.state == STATE_OFF
    assert calls[-1].data[CONF_TYPE] == "daily"
    # The first decision never creates a notification.
    mock_notification.assert_not_called()

    mock_forecast_service(hass, [forecast_entry(0, 5), forecast_entry(1, 4, -2)])
    set_weather_state(hass, temperature=3)
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state.state == STATE_ON
    mock_notification.assert_called_once_with(
        hass,
        "For area Test area it's time to change car tires to winter ones.",
        title="Change tires for Test area",
        notification_id="snowtire_test_entry",
    )

    # Same decision again: no new notification.
    set_weather_state(hass, temperature=2)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON
    assert mock_notification.call_count == 1

    mock_forecast_service(hass, [forecast_entry(0, 15), forecast_entry(1, 14, 9)])
    set_weather_state(hass, temperature=12)
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF
    assert mock_notification.call_count == 2
    assert (
        mock_notification.call_args.args[1]
        == "For area Test area it's time to change car tires to summer ones."
    )


async def test_notifications_disabled(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_notification: MagicMock,
) -> None:
    """Test no notification is created when disabled in the options."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**mock_config_entry.options, CONF_CREATE_NOTIFICATIONS: False},
    )
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    mock_forecast_service(hass, [forecast_entry(0, 12)])
    set_weather_state(hass, temperature=10)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF

    mock_forecast_service(hass, [forecast_entry(0, -3)])
    set_weather_state(hass, temperature=-1)
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON
    mock_notification.assert_not_called()


async def test_days_window(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test only the configured number of forecast days is analyzed."""
    await setup_entry(hass, mock_config_entry)

    # Freezing temperatures in the past and beyond the window are ignored.
    mock_forecast_service(
        hass,
        [
            forecast_entry(-1, -10, -15),
            forecast_entry(0, 12),
            forecast_entry(1, 11, 8),
            forecast_entry(2, 10, 7),
            forecast_entry(3, -5, -10),
            {ATTR_FORECAST_TIME: None, ATTR_FORECAST_TEMP: -20},
        ],
    )
    set_weather_state(hass, temperature=10)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF

    # The last day of the window counts.
    mock_forecast_service(
        hass,
        [forecast_entry(0, 12), forecast_entry(1, 11, 8), forecast_entry(2, 10, -1)],
    )
    set_weather_state(hass, temperature=11)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON


async def test_todays_low_is_ignored(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the low temperature of today is ignored, but tomorrow's counts."""
    await setup_entry(hass, mock_config_entry)

    mock_forecast_service(hass, [forecast_entry(0, 12, -5)])
    set_weather_state(hass, temperature=10)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF

    mock_forecast_service(hass, [forecast_entry(1, 12, -5)])
    set_weather_state(hass, temperature=11)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON


async def test_fahrenheit(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test temperatures are converted from the unit of the weather entity."""
    await setup_entry(hass, mock_config_entry)

    mock_forecast_service(hass, [forecast_entry(0, 55), forecast_entry(1, 54, 50)])
    set_weather_state(hass, temperature=50, unit=UnitOfTemperature.FAHRENHEIT)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF

    mock_forecast_service(hass, [forecast_entry(0, 40), forecast_entry(1, 38, 30)])
    set_weather_state(hass, temperature=35, unit=UnitOfTemperature.FAHRENHEIT)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON


async def test_missing_temperatures(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test missing current or forecast temperatures do not break the sensor."""
    await setup_entry(hass, mock_config_entry)

    mock_forecast_service(hass, [forecast_entry(0, None), forecast_entry(1, 12)])
    set_weather_state(hass, temperature=None)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF

    # No temperatures at all: nothing to decide on.
    mock_forecast_service(hass, [forecast_entry(0, None)])
    set_weather_state(hass, temperature=None, state="cloudy")
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("features", "expected_type"),
    [
        (
            WeatherEntityFeature.FORECAST_DAILY
            | WeatherEntityFeature.FORECAST_TWICE_DAILY
            | WeatherEntityFeature.FORECAST_HOURLY,
            "daily",
        ),
        (
            WeatherEntityFeature.FORECAST_TWICE_DAILY
            | WeatherEntityFeature.FORECAST_HOURLY,
            "twice_daily",
        ),
        (WeatherEntityFeature.FORECAST_HOURLY, "hourly"),
    ],
)
async def test_forecast_type(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    features: int,
    expected_type: str,
) -> None:
    """Test the preferred forecast type is requested."""
    await setup_entry(hass, mock_config_entry)
    calls = mock_forecast_service(hass, [forecast_entry(0, 12)])

    set_weather_state(hass, features=features)
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF
    assert calls[-1].data[CONF_TYPE] == expected_type


@pytest.mark.parametrize("features", [0, "unexpected"])
async def test_no_forecast_support(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    features: int | str,
) -> None:
    """Test a weather entity without forecast support makes the sensor unavailable."""
    await setup_entry(hass, mock_config_entry)
    calls = mock_forecast_service(hass, [forecast_entry(0, 12)])

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        set_weather_state(hass, features=features)
        await hass.async_block_till_done()
        set_weather_state(hass, temperature=11, features=features)
        await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE
    assert not calls
    # The problem is reported only once.
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "does not provide any forecast" in warnings[0].message


async def test_forecast_service_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a failing forecast service makes the sensor unavailable."""
    await setup_entry(hass, mock_config_entry)
    async_mock_service(
        hass,
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        raise_exception=HomeAssistantError("boom"),
    )

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        set_weather_state(hass)
        await hass.async_block_till_done()
        set_weather_state(hass, temperature=11)
        await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "Unable to get forecast" in warnings[0].message

    # Recovers once the service works again.
    mock_forecast_service(hass, [forecast_entry(0, 12)])
    set_weather_state(hass, temperature=12)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF


async def test_weather_unavailable(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test an unavailable weather entity makes the sensor unavailable."""
    await setup_entry(hass, mock_config_entry)
    mock_forecast_service(hass, [forecast_entry(0, 12)])

    set_weather_state(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF

    set_weather_state(hass, state=STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE


async def test_restore_state(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_notification: MagicMock,
) -> None:
    """Test the last decision is restored after a restart."""
    mock_restore_cache(hass, [State(SENSOR_ENTITY_ID, STATE_ON)])
    await setup_entry(hass, mock_config_entry)

    # Unavailable until the weather entity shows up...
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE

    # ...but the restored decision is used for the hysteresis: an average of
    # 7.2°C keeps winter tires only when the previous decision was "winter".
    mock_forecast_service(hass, [forecast_entry(0, 7.2), forecast_entry(1, 7.2, 7.2)])
    set_weather_state(hass, temperature=7.2)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON
    mock_notification.assert_not_called()

    # A change against the restored decision is notified.
    mock_forecast_service(hass, [forecast_entry(0, 15), forecast_entry(1, 14, 10)])
    set_weather_state(hass, temperature=13)
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF
    mock_notification.assert_called_once()
    assert "summer" in mock_notification.call_args.args[1]


async def test_restore_unavailable_state(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test an unavailable last state is not restored."""
    mock_restore_cache(hass, [State(SENSOR_ENTITY_ID, STATE_UNAVAILABLE)])
    await setup_entry(hass, mock_config_entry)

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE


async def test_unload_stops_updates(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the weather listener is removed when the entry is unloaded."""
    await setup_entry(hass, mock_config_entry)
    calls = mock_forecast_service(hass, [forecast_entry(0, 12)])
    set_weather_state(hass)
    await hass.async_block_till_done()
    assert len(calls) == 1

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    set_weather_state(hass, temperature=11)
    await hass.async_block_till_done()
    assert len(calls) == 1
