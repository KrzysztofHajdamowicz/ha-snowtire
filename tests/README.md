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
