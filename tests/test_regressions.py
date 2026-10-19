"""Regression tests for the issues found during the pre-release review."""

import ast
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

from homeassistant.components.weather import (
    ATTR_FORECAST_IS_DAYTIME,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    DOMAIN as WEATHER_DOMAIN,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntryState
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

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
    mock_forecast_service,
    set_weather_state,
    setup_entry,
)

pytestmark = pytest.mark.regression

COMPONENT_PATH = Path(__file__).resolve().parents[1] / "custom_components" / DOMAIN


@pytest.mark.parametrize(
    "source", sorted(COMPONENT_PATH.rglob("*.py")), ids=lambda source: source.name
)
def test_python_313_syntax(source: Path) -> None:
    """Accept the Python grammar supported by the advertised minimum HA version."""
    ast.parse(
        source.read_text(encoding="utf-8"),
        filename=str(source),
        feature_version=(3, 13),
    )


@pytest.mark.parametrize(
    "forecast_case",
    ["empty", "missing_temperature", "expired", "beyond_window", "invalid_time"],
)
async def test_no_usable_forecast_is_unavailable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_notification: MagicMock,
    forecast_case: str,
) -> None:
    """A warm current observation alone must not become a summer recommendation."""
    await setup_entry(hass, mock_config_entry)
    tomorrow = dt_util.now() + timedelta(days=1)
    forecasts = {
        "empty": [],
        "missing_temperature": [{ATTR_FORECAST_TIME: tomorrow.isoformat()}],
        "expired": [
            {
                ATTR_FORECAST_TIME: (dt_util.now() - timedelta(days=1)).isoformat(),
                ATTR_FORECAST_TEMP: 14,
            }
        ],
        "beyond_window": [
            {
                ATTR_FORECAST_TIME: (
                    dt_util.now() + timedelta(days=DAYS + 1)
                ).isoformat(),
                ATTR_FORECAST_TEMP: 14,
            }
        ],
        "invalid_time": [{ATTR_FORECAST_TIME: "invalid", ATTR_FORECAST_TEMP: 14}],
    }
    mock_forecast_service(hass, forecasts[forecast_case])
    set_weather_state(hass, temperature=14)
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE
    mock_notification.assert_not_called()


async def test_forecast_loss_does_not_notify_summer(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_notification: MagicMock,
) -> None:
    """Losing a forecast must not notify; a real change after recovery must notify."""
    await setup_entry(hass, mock_config_entry)
    tomorrow = (dt_util.now() + timedelta(days=1)).isoformat()
    mock_forecast_service(
        hass,
        [
            {
                ATTR_FORECAST_TIME: tomorrow,
                ATTR_FORECAST_TEMP: 4,
                ATTR_FORECAST_TEMP_LOW: -3,
            }
        ],
    )
    set_weather_state(hass, temperature=10)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON
    mock_notification.assert_not_called()

    mock_forecast_service(hass, [])
    set_weather_state(hass, temperature=11)
    await hass.async_block_till_done()

    mock_notification.assert_not_called()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_UNAVAILABLE

    mock_forecast_service(
        hass, [{ATTR_FORECAST_TIME: tomorrow, ATTR_FORECAST_TEMP: 14}]
    )
    set_weather_state(hass, temperature=12)
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF
    mock_notification.assert_called_once_with(
        hass,
        "For area Test area it's time to change car tires to summer ones.",
        title="Change tires for Test area",
        notification_id="snowtire_test_entry",
    )


@pytest.mark.parametrize(
    ("hours_ahead", "expected"),
    [(-4, STATE_OFF), (4, STATE_ON)],
    ids=["elapsed_frost", "upcoming_frost"],
)
async def test_hourly_forecast_uses_future_hours(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer,
    hours_ahead: int,
    expected: str,
) -> None:
    """Ignore elapsed hours, but retain upcoming frost on the same local date."""
    freezer.move_to("2026-10-19T12:00:00+00:00")
    await hass.config.async_set_time_zone("Europe/Warsaw")
    await setup_entry(hass, mock_config_entry)
    mock_forecast_service(
        hass,
        [
            {
                ATTR_FORECAST_TIME: (
                    dt_util.now() + timedelta(hours=hours_ahead)
                ).isoformat(),
                ATTR_FORECAST_TEMP: -3,
            },
            {
                ATTR_FORECAST_TIME: (dt_util.now() + timedelta(hours=6)).isoformat(),
                ATTR_FORECAST_TEMP: 14,
            },
        ],
    )
    set_weather_state(
        hass, temperature=14, features=WeatherEntityFeature.FORECAST_HOURLY
    )
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == expected


async def test_upcoming_twice_daily_low_counts_today(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, freezer
) -> None:
    """Do not discard a low belonging to an explicitly upcoming night period."""
    freezer.move_to("2026-10-19T12:00:00+00:00")
    await hass.config.async_set_time_zone("Europe/Warsaw")
    await setup_entry(hass, mock_config_entry)
    mock_forecast_service(
        hass,
        [
            {
                ATTR_FORECAST_TIME: (dt_util.now() + timedelta(hours=6)).isoformat(),
                ATTR_FORECAST_IS_DAYTIME: False,
                ATTR_FORECAST_TEMP: 10,
                ATTR_FORECAST_TEMP_LOW: -3,
            }
        ],
    )
    set_weather_state(
        hass, temperature=14, features=WeatherEntityFeature.FORECAST_TWICE_DAILY
    )
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON


class ForecastWeather(WeatherEntity):
    """Weather entity using HA's actual forecast service and push mechanism."""

    _attr_name = "Forecast test"
    _attr_should_poll = False
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_temperature = 12
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
    _attr_condition = "sunny"

    def __init__(self) -> None:
        """Start with a warm forecast and constant current observations."""
        self.entity_id = WEATHER_ENTITY_ID
        self.forecast: list[Forecast] = []
        self.set_forecast(high=14, low=10)

    def set_forecast(self, *, high: float, low: float) -> None:
        """Replace the forecast without changing the entity's state attributes."""
        self.forecast = [
            {
                ATTR_FORECAST_TIME: (dt_util.now() + timedelta(days=1)).isoformat(),
                ATTR_FORECAST_NATIVE_TEMP: high,
                ATTR_FORECAST_NATIVE_TEMP_LOW: low,
            }
        ]

    async def async_forecast_daily(self) -> list[Forecast]:
        """Return the forecast through the real weather service."""
        return self.forecast


async def test_forecast_refresh_without_weather_state_change(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_notification: MagicMock,
    freezer,
) -> None:
    """Observe forecast-only changes via a subscription or periodic refresh."""
    freezer.move_to("2026-10-19T12:00:00+00:00")
    assert await async_setup_component(hass, WEATHER_DOMAIN, {})
    weather = ForecastWeather()
    await hass.data[WEATHER_DOMAIN].async_add_entities([weather])
    await setup_entry(hass, mock_config_entry)
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF
    original_weather = hass.states.get(WEATHER_ENTITY_ID)

    weather.set_forecast(high=4, low=-4)
    await weather.async_update_listeners(["daily"])
    weather.async_write_ha_state()
    await hass.async_block_till_done()
    assert (
        hass.states.get(WEATHER_ENTITY_ID).last_updated == original_weather.last_updated
    )

    # Also allow a polling implementation, without manually refreshing Snowtire.
    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_ON
    mock_notification.assert_called_once()
    assert "winter" in mock_notification.call_args.args[1]


async def test_unload_stops_periodic_refresh(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, freezer
) -> None:
    """Remove periodic refreshes along with the sensor's weather listener."""
    freezer.move_to("2026-10-19T12:00:00+00:00")
    await setup_entry(hass, mock_config_entry)
    calls = mock_forecast_service(
        hass,
        [
            {
                ATTR_FORECAST_TIME: (dt_util.now() + timedelta(days=1)).isoformat(),
                ATTR_FORECAST_TEMP: 14,
            }
        ],
    )
    set_weather_state(hass, temperature=12)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR_ENTITY_ID).state == STATE_OFF
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    call_count = len(calls)

    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    assert len(calls) == call_count


@pytest.mark.parametrize("custom_unique_id", [None, "my_tires"])
async def test_legacy_yaml_upgrade_preserves_entity(
    hass: HomeAssistant, custom_unique_id: str | None
) -> None:
    """Replace the old empty import entry without orphaning its registered sensor."""
    legacy_entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="legacy_yaml_entry",
        source=SOURCE_IMPORT,
        title="configuration.yaml",
        data={},
        options={},
    )
    legacy_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    original = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        custom_unique_id or f"{legacy_entry.entry_id}-0",
        suggested_object_id="my_existing_tires",
        config_entry=legacy_entry,
    )
    # A user's customized name and entity ID must survive the upgrade.
    registry.async_update_entity(original.entity_id, name="My car tires")
    yaml_entry = {
        CONF_NAME: AREA_NAME,
        CONF_WEATHER: WEATHER_ENTITY_ID,
        CONF_DAYS: DAYS,
        CONF_CREATE_NOTIFICATIONS: False,
    }
    if custom_unique_id is not None:
        yaml_entry[CONF_UNIQUE_ID] = custom_unique_id
    assert await async_setup_component(hass, WEATHER_DOMAIN, {})
    mock_forecast_service(
        hass,
        [
            {
                ATTR_FORECAST_TIME: (dt_util.now() + timedelta(days=1)).isoformat(),
                ATTR_FORECAST_TEMP: 14,
            }
        ],
    )
    set_weather_state(hass, temperature=12)

    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [yaml_entry]})
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED
    sensor = hass.states.get(original.entity_id)
    assert sensor is not None
    assert sensor.state == STATE_OFF
    registered = registry.async_get(original.entity_id)
    assert registered.name == "My car tires"
    assert registered.config_entry_id == entries[0].entry_id
    assert [
        entity.entity_id
        for entity in registry.entities.values()
        if entity.platform == DOMAIN
    ] == [original.entity_id]

    # Keeping deprecated YAML until the next restart must not create duplicates.
    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=yaml_entry
    )
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
