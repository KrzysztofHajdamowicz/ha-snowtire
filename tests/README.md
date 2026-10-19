# Tests

The tests use [pytest](https://docs.pytest.org/) together with [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component), which provides the same fixtures as the Home Assistant core test suite (`hass`, `freezer`, `issue_registry`, ...).

## Getting started

```bash
./scripts/setup
```

## Useful commands

Command | Description
------- | -----------
`uv run pytest` | Run all tests and print a coverage summary of the integration.
`uv run pytest tests/test_binary_sensor.py -k test_days_window` | Run a single test.
`uv run pytest --no-cov -x` | Stop at the first failure, without coverage.
`uv run pytest -m regression --no-cov` | Run the pre-release regression scenarios.

## Pre-release regression scenarios

`test_regressions.py` guards the behavior corrected after the code review. These
tests run as part of the normal suite and are not marked `xfail`.

- Python 3.13 syntax compatibility for the advertised Home Assistant 2026.1 minimum.
  The grammar check complements the full runtime suite in CI on HA 2026.1.0 and
  Python 3.13, using `pytest-homeassistant-custom-component==0.13.305`.
- Unavailable state when no usable forecast exists, even with a current temperature.
- No summer notification when a forecast disappears, followed by normal recovery.
- Filtering elapsed hourly forecasts while retaining upcoming frost today.
- Including the low of an explicitly upcoming twice-daily night period.
  `test_binary_sensor.py` also checks that today's daily minimum is included.
- Forecast-only updates through a real `WeatherEntity` and the HA weather service,
  allowing a subscription or a periodic refresh within an hour.
- Migration of an old empty YAML import entry, preserving the sensor's entity ID
  and customized name, including configurations with an explicit legacy `unique_id`.

`test_migration.py` also checks shared YAML entries with multiple sensors, disabled
entities, interrupted migrations, and an actionable error when the original YAML
is missing. Periodic forecast refreshes must stop when the sensor is unloaded.
