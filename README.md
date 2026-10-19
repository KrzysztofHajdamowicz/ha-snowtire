*Please :star: this repo if you find it useful*

# Snowtire Binary Sensor for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]
[![CI][ci-shield]][ci]

[![hacs][hacs-shield]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

_This integration checks the weather forecast for several days in advance and concludes whether it is time to change car tires from summer to winter ones and vice versa._

![Example][exampleimg]

This is a maintained fork of the original [Limych/ha-snowtire](https://github.com/Limych/ha-snowtire) integration, updated for current Home Assistant releases.

## Breaking Changes

* Since version 2.0.0:
  * Home Assistant 2026.1 or newer is required.
  * The `binary_sensor: - platform: snowtire` configuration (deprecated since 1.6.0) has been removed.
  * The `snowtire:` section in `configuration.yaml` is deprecated. It is still imported into the UI once and a repair issue reminds you to remove it. Configure the integration via the UI instead.
  * The `unique_id` option is ignored. Every sensor is identified by its config entry.
  * The sensor remembers its last decision across restarts, so a tire change notification is also created when the decision changes right after a restart.

## Installation

### Install from HACS (recommended)

1. Have [HACS][hacs] installed, this will allow you to easily manage and track updates.
1. Add this repository (`KrzysztofHajdamowicz/ha-snowtire`) as a custom repository of type _Integration_.
1. Search for "Snowtire" and download it.
1. Restart Home Assistant.
1. In the Home Assistant UI go to _Settings_ → _Devices & services_ → _Add integration_ and search for "Snowtire".

### Manual installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `snowtire`.
1. Download file `snowtire.zip` from the [latest release section][releases-latest] in this repository.
1. Extract _all_ files from this archive you downloaded in the directory (folder) you created.
1. Restart Home Assistant.
1. In the Home Assistant UI go to _Settings_ → _Devices & services_ → _Add integration_ and search for "Snowtire".

## Configuration

The integration is configured via the UI. You can add several sensors, one per area (for example one per city you regularly drive to).

**Area name**\
  Name used in the sensor name (`Tires for <name>`) and in notifications. Defaults to your Home Assistant location name.

**Weather forecast entity for the area**\
  Weather entity providing the forecast.

> **_Note_**:\
> The sensor works with any weather provider. But please note that the sensor cannot see further than the weather provider shows. A provider with a daily forecast is preferred; twice-daily and hourly forecasts are used when no daily forecast is available.

**Forecast days to analyze** _(Default value: 7)_\
  The number of days the sensor looks ahead in the weather forecast.

**Create notifications** _(Default value: on)_\
  If enabled, the integration creates a persistent notification when it is time to change tires.

All settings except the area name can be changed later via _Configure_ on the integration entry.

### How the decision is made

The sensor looks at the current temperature and at the forecast temperatures (daily highs and lows) for the configured number of days:

* if any temperature is at or below 0.5 °C, winter tires are needed;
* otherwise, winter tires are needed when the average temperature is below 7 °C (with a hysteresis of ±0.5 °C to avoid flapping).

### Legacy YAML configuration

A `snowtire:` section in `configuration.yaml` is still imported into a config entry on startup, and a repair issue asks you to remove it:

```yaml
# Deprecated, use the UI instead
snowtire:
  - weather: weather.<YOUR_WEATHER_PROVIDER_ENTITY_ID>
    name: Home
    days: 7
    create_notifications: true
```

## Track updates

You can automatically track new versions of this component and update it by [HACS][hacs].

## Troubleshooting

To enable debug logs use this configuration:
```yaml
# Example configuration.yaml entry
logger:
  default: info
  logs:
    custom_components.snowtire: debug
```
... then restart HA. Diagnostics can be downloaded from the integration entry in the UI.

## Development

The project uses [uv](https://docs.astral.sh/uv/) for dependency management. Home Assistant itself is installed as a development dependency.

```bash
./scripts/setup          # uv sync + install git hooks (prek)
uv run pytest            # run the tests
./scripts/lint           # format and lint with ruff
./scripts/develop        # start a development Home Assistant instance on port 8123
```

See the [contribution guidelines](CONTRIBUTING.md) for details.

## Authors & contributors

The original integration was created by [Andrey "Limych" Khrolenok](https://github.com/Limych). This fork is maintained by [Krzysztof Hajdamowicz](https://github.com/KrzysztofHajdamowicz).

For a full list of all authors and contributors, check [the contributor's page][contributors].

## License

Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License

See separate [license file](LICENSE.md) for full text.

***

[component]: https://github.com/KrzysztofHajdamowicz/ha-snowtire
[ci-shield]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/actions/workflows/ci.yml/badge.svg
[ci]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/actions/workflows/ci.yml
[commits-shield]: https://img.shields.io/github/commit-activity/y/KrzysztofHajdamowicz/ha-snowtire.svg?style=popout
[commits]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/commits/dev
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=popout
[hacs]: https://hacs.xyz
[exampleimg]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/raw/dev/example.jpg
[license]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/blob/dev/LICENSE.md
[license-shield]: https://img.shields.io/badge/license-Creative_Commons_BY--NC--SA_License-lightgray.svg?style=popout
[maintenance-shield]: https://img.shields.io/badge/maintainer-Krzysztof%20Hajdamowicz-blue.svg?style=popout
[releases-shield]: https://img.shields.io/github/release/KrzysztofHajdamowicz/ha-snowtire.svg?style=popout
[releases]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/releases
[releases-latest]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/releases/latest
[user_profile]: https://github.com/KrzysztofHajdamowicz
[contributors]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/graphs/contributors
