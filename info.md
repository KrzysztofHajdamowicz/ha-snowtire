{% if prerelease %}
### NB!: This is a Beta version!
{% endif %}
{% if installed and (version_installed.split(".")[0] | int) < 2 %}
### ATTENTION! Breaking changes!

Version 2.0.0 requires Home Assistant 2026.1 or newer, drops the `binary_sensor: - platform: snowtire` configuration and deprecates the `snowtire:` YAML section in favour of the UI. See the [documentation][component] for details.
{% endif %}

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacs-shield]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

_This integration checks the weather forecast for several days in advance and concludes whether it is time to change car tires from summer to winter ones and vice versa._

![Example](https://github.com/KrzysztofHajdamowicz/ha-snowtire/raw/dev/example.jpg)

## Features:

- Works with any weather provider;
- One sensor per area, configured via the UI;
- Optional notification when it is time to change tires.

{% if not installed %}
## Installation

1. Click install.
1. Restart Home Assistant.
1. In the Home Assistant UI go to _Settings_ → _Devices & services_ → _Add integration_ and search for "Snowtire".

{% endif %}
## Useful Links

- [Documentation][component]
- [Report a Bug][report_bug]
- [Suggest an idea][suggest_idea]

***

[component]: https://github.com/KrzysztofHajdamowicz/ha-snowtire
[commits-shield]: https://img.shields.io/github/commit-activity/y/KrzysztofHajdamowicz/ha-snowtire.svg?style=popout
[commits]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/commits/dev
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=popout
[hacs]: https://hacs.xyz
[license]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/blob/dev/LICENSE.md
[license-shield]: https://img.shields.io/badge/license-Creative_Commons_BY--NC--SA_License-lightgray.svg?style=popout
[maintenance-shield]: https://img.shields.io/badge/maintainer-Krzysztof%20Hajdamowicz-blue.svg?style=popout
[releases-shield]: https://img.shields.io/github/release/KrzysztofHajdamowicz/ha-snowtire.svg?style=popout
[releases]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/releases
[user_profile]: https://github.com/KrzysztofHajdamowicz
[report_bug]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/issues/new/choose
[suggest_idea]: https://github.com/KrzysztofHajdamowicz/ha-snowtire/issues/new/choose
