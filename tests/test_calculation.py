"""Tests for the tire decision logic."""

from datetime import UTC, date, datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest

from custom_components.snowtire.binary_sensor import calculate_winter, forecast_date


@pytest.mark.parametrize(
    ("temperatures", "previous", "expected"),
    [
        ([], None, None),
        ([10, 12], None, False),
        ([6, 7], None, True),
        ([7, 7], None, False),
        ([10, 0.5], False, True),
        ([14, 0.6], False, False),
        # Hysteresis around the change threshold (7°C ± 0.5°C).
        ([7.2], None, False),
        ([7.2], True, True),
        ([7.2], False, False),
        ([6.8], None, True),
        ([6.8], True, True),
        ([6.8], False, False),
        ([7.6], True, False),
        ([6.4], False, True),
    ],
)
def test_calculate_winter(temperatures, previous, expected) -> None:
    """Test the winter tires decision."""
    assert calculate_winter(temperatures, previous=previous) is expected


async def test_forecast_date(hass: HomeAssistant) -> None:
    """Test forecast timestamps of different types are converted to local dates."""
    await hass.config.async_set_time_zone("Europe/Warsaw")
    timestamp = datetime(2026, 10, 19, 23, 30, tzinfo=UTC)

    assert forecast_date(timestamp) == date(2026, 10, 20)
    assert forecast_date(timestamp.isoformat()) == date(2026, 10, 20)
    assert forecast_date(int(timestamp.timestamp() * 1000)) == date(2026, 10, 20)
    assert forecast_date(dt_util.as_local(timestamp)) == date(2026, 10, 20)
    assert forecast_date("not a date") is None
    assert forecast_date(None) is None
