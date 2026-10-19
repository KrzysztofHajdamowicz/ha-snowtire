# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Development environment

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and the dependencies. Home Assistant is installed as a development dependency, so its source code is available in `.venv` for reference.

```bash
./scripts/setup          # creates .venv, installs dependencies and git hooks
uv run pytest            # runs the tests
./scripts/lint           # formats and lints the code with ruff
./scripts/develop        # starts a development Home Assistant on http://localhost:8123
```

The git hooks (run by [prek](https://prek.j178.dev/), a drop-in replacement for pre-commit) format the code, keep `uv.lock` up to date and sync `manifest.json` with `const.py`.

A [devcontainer](.devcontainer.json) with everything preinstalled is available for Visual Studio Code.

## Pull requests

1. Fork the repo and create your branch from `dev`.
2. Follow the current [Home Assistant developer documentation](https://developers.home-assistant.io/) for integrations.
3. Add or update tests for your change and make sure `uv run pytest` passes.
4. Make sure `./scripts/lint` reports no issues.
5. If you've changed behaviour, update the documentation.
6. Open the pull request against `dev`.

## Report bugs using GitHub's [issues](../../issues)

GitHub issues are used to track public bugs. Report a bug by [opening a new issue](../../issues/new/choose).

**Great bug reports** tend to have:

- A quick summary and/or background
- Steps to reproduce (be specific, give sample configuration if you can)
- What you expected would happen
- What actually happens
- Debug logs (`logger: logs: custom_components.snowtire: debug`) and the diagnostics download of the integration entry

## License

By contributing, you agree that your contributions will be licensed under the same [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](LICENSE.md) that covers the project.
