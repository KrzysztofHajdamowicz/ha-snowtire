"""Binary sensor platform for the Snowtire integration."""

#  Copyright (c) 2020-2024, Andrey "Limych" Khrolenok <andrey@khrolenok.ru>
#  Copyright (c) 2026, Krzysztof Hajdamowicz
#  Creative Commons BY-NC-SA 4.0 International Public License
#  (see LICENSE.md or https://creativecommons.org/licenses/by-nc-sa/4.0/)

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any, Final

from homeassistant.components import persistent_notification
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.weather import (
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_TEMPERATURE_UNIT,
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
    WeatherEntityFeature,
)
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_TYPE,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import translation
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.start import async_at_started
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    CONF_CREATE_NOTIFICATIONS,
    CONF_DAYS,
    CONF_WEATHER,
    DEFAULT_CREATE_NOTIFICATIONS,
    DEFAULT_DAYS,
    DOMAIN,
    TEMP_CHANGE,
    TEMP_ERROR,
    TEMP_FREEZE,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from homeassistant.core import Event, EventStateChangedData
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SnowtireConfigEntry

_LOGGER = logging.getLogger(__name__)
FORECAST_REFRESH_INTERVAL: Final = timedelta(minutes=30)

# Forecast types in order of preference.
FORECAST_TYPES: Final = (
    (WeatherEntityFeature.FORECAST_DAILY, "daily"),
    (WeatherEntityFeature.FORECAST_TWICE_DAILY, "twice_daily"),
    (WeatherEntityFeature.FORECAST_HOURLY, "hourly"),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SnowtireConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Snowtire binary sensor from a config entry."""
    async_add_entities([SnowtireBinarySensor(entry)])


def calculate_winter(
    temperatures: Iterable[float], *, previous: bool | None
) -> bool | None:
    """
    Decide whether winter tires are needed.

    Winter tires are needed when any temperature is at or below the freezing
    threshold, or when the average temperature is below the change threshold.
    The change threshold has a hysteresis depending on the previous decision.
    Returns None when there is no data to decide on.
    """
    temps = list(temperatures)
    if not temps:
        return None
    if min(temps) <= TEMP_FREEZE:
        return True

    if previous is None:
        threshold = TEMP_CHANGE
    elif previous:
        threshold = TEMP_CHANGE + TEMP_ERROR
    else:
        threshold = TEMP_CHANGE - TEMP_ERROR
    return sum(temps) / len(temps) < threshold


def forecast_datetime(value: Any) -> datetime | None:
    """Return the local timestamp of a forecast entry."""
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, int | float):
        timestamp = datetime.fromtimestamp(value / 1000, tz=UTC)
    elif isinstance(value, str):
        if (timestamp := dt_util.parse_datetime(value)) is None:
            return None
    else:
        return None
    return dt_util.as_local(timestamp)


def forecast_date(value: Any) -> date | None:
    """Return the local date of a forecast entry timestamp."""
    timestamp = forecast_datetime(value)
    return timestamp.date() if timestamp is not None else None


class SnowtireBinarySensor(BinarySensorEntity, RestoreEntity):
    """Binary sensor telling whether winter tires are needed."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "snowtire"
    _attr_available = False

    def __init__(self, entry: SnowtireConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._weather_entity_id: str = entry.options[CONF_WEATHER]
        self._days: int = entry.options.get(CONF_DAYS, DEFAULT_DAYS)
        self._notify: bool = entry.options.get(
            CONF_CREATE_NOTIFICATIONS, DEFAULT_CREATE_NOTIFICATIONS
        )
        self._problem_reported = False

        self._attr_unique_id = entry.entry_id
        self._attr_translation_placeholders = {
            "name": entry.data.get(CONF_NAME, entry.title)
        }

    async def async_added_to_hass(self) -> None:
        """Restore the previous decision and subscribe to weather updates."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            self._attr_is_on = last_state.state == STATE_ON

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._weather_entity_id], self._async_weather_changed
            )
        )
        self.async_on_remove(async_at_started(self.hass, self._async_started))
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_refresh_forecast, FORECAST_REFRESH_INTERVAL
            )
        )

    @callback
    def _async_started(self, _hass: HomeAssistant) -> None:
        """Schedule the first update once Home Assistant has started."""
        self.async_schedule_update_ha_state(force_refresh=True)

    @callback
    def _async_weather_changed(self, _event: Event[EventStateChangedData]) -> None:
        """Schedule an update when the weather entity changes."""
        self.async_schedule_update_ha_state(force_refresh=True)

    @callback
    def _async_refresh_forecast(self, _now: datetime) -> None:
        """Refresh forecasts even when current weather observations do not change."""
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_update(self) -> None:
        """Update the sensor state from the weather forecast."""
        previous = self._attr_is_on
        temperatures = await self._async_get_temperatures()
        state = (
            calculate_winter(temperatures, previous=previous) if temperatures else None
        )
        if state is None:
            self._attr_available = False
            return

        self._attr_available = True
        self._attr_is_on = state
        if self._notify and previous is not None and state != previous:
            await self._async_notify(winter=state)

    async def _async_get_temperatures(self) -> list[float]:
        """Return current and forecast temperatures (Celsius) for the analyzed days."""
        weather = self.hass.states.get(self._weather_entity_id)
        if weather is None or weather.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("Weather entity %s is not available", self._weather_entity_id)
            return []

        forecast_type = self._forecast_type(weather.attributes)
        if forecast_type is None:
            self._report_problem(
                "Weather entity %s does not provide any forecast",
                self._weather_entity_id,
            )
            return []

        try:
            response = await self.hass.services.async_call(
                WEATHER_DOMAIN,
                SERVICE_GET_FORECASTS,
                {CONF_TYPE: forecast_type, CONF_ENTITY_ID: self._weather_entity_id},
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as err:
            self._report_problem(
                "Unable to get forecast from %s: %s", self._weather_entity_id, err
            )
            return []
        forecast = (response or {}).get(self._weather_entity_id, {}).get(
            "forecast"
        ) or []
        unit = (
            weather.attributes.get(ATTR_WEATHER_TEMPERATURE_UNIT)
            or self.hass.config.units.temperature_unit
        )
        now = dt_util.now()
        today = now.date()
        stop = today + timedelta(days=self._days + 1)

        temperatures: list[float] = []
        for item in forecast:
            timestamp = forecast_datetime(item.get(ATTR_FORECAST_TIME))
            if timestamp is None:
                continue
            day = timestamp.date()
            if day < today or day >= stop:
                continue
            if forecast_type == "hourly" and dt_util.as_utc(timestamp) < dt_util.as_utc(
                now
            ):
                continue
            low = item.get(ATTR_FORECAST_TEMP_LOW)
            if low is not None:
                temperatures.append(_to_celsius(low, unit))
            high = item.get(ATTR_FORECAST_TEMP)
            if high is not None:
                temperatures.append(_to_celsius(high, unit))

        if not temperatures:
            self._report_problem(
                "Weather entity %s has no usable forecast temperatures",
                self._weather_entity_id,
            )
            return []

        self._problem_reported = False
        if (current := weather.attributes.get(ATTR_WEATHER_TEMPERATURE)) is not None:
            temperatures.append(_to_celsius(current, unit))

        _LOGGER.debug(
            "Temperatures for %s from %s to %s: %s",
            self._weather_entity_id,
            today,
            stop - timedelta(days=1),
            temperatures,
        )
        return temperatures

    @staticmethod
    def _forecast_type(attributes: Mapping[str, Any]) -> str | None:
        """Return the best forecast type supported by the weather entity."""
        try:
            features = int(attributes.get(ATTR_SUPPORTED_FEATURES) or 0)
        except (TypeError, ValueError):
            return None
        return next(
            (name for feature, name in FORECAST_TYPES if features & feature), None
        )

    def _report_problem(self, message: str, *args: Any) -> None:
        """Log a problem once until the next successful update."""
        if not self._problem_reported:
            _LOGGER.warning(message, *args)
            self._problem_reported = True
        else:
            _LOGGER.debug(message, *args)

    async def _async_notify(self, *, winter: bool) -> None:
        """Create a persistent notification about the tire change."""
        translations = await translation.async_get_translations(
            self.hass, self.hass.config.language, "entity", {DOMAIN}
        )
        placeholders = self._attr_translation_placeholders or {}

        def _text(key: str) -> str:
            text = translations.get(
                f"component.{DOMAIN}.entity.notification.{key}.name", key
            )
            try:
                return text.format(**placeholders)
            except (KeyError, IndexError):
                return text

        _LOGGER.debug("Creating notification to change tires (winter=%s)", winter)
        persistent_notification.async_create(
            self.hass,
            _text("to_winter" if winter else "to_summer"),
            title=_text("title"),
            notification_id=f"{DOMAIN}_{self._entry.entry_id}",
        )


def _to_celsius(temperature: float, unit: str) -> float:
    """Convert a temperature to Celsius."""
    if unit == UnitOfTemperature.CELSIUS:
        return float(temperature)
    return TemperatureConverter.convert(
        float(temperature), unit, UnitOfTemperature.CELSIUS
    )
