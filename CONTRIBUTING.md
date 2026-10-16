# Contributing

Thanks for helping to improve the Ökofen Pellematic integration. Bug reports, test data, ideas and
pull requests are all welcome.

## The most valuable contribution: data from your heater

The integration builds every entity from the heater's JSON response, and every firmware version,
language and hardware combination looks a little different. An anonymized `/all?` response of your
heater ([how to get it](https://github.com/dominikamann/oekofen-pellematic-compact/discussions/150))
becomes a test fixture and keeps your setup working in future releases. For the diagnostics, real
cases help most: what went wrong with your heater, and how did it show up in the values?

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
pytest tests/
```

Run a local Home Assistant with the integration against `./config`:

```bash
scripts/start_homeassistant.sh
```

## Guidelines

- **No hard-coded entity lists.** Entities are discovered from the API metadata
  (`dynamic_discovery.py`). Support for new values belongs into the discovery logic.
- **Entity IDs are stable.** `tests/entity_id_snapshot.json` fails when entity IDs change. Update it
  only when the change is intended, and mention it in the pull request.
- **Every parsing fix gets a fixture.** Add the anonymized response to `tests/fixtures/` and a test
  that fails without the fix.
- **No external Python dependencies.** The integration uses only the standard library and Home
  Assistant; blocking I/O runs in the executor.
- **Diagnostic checks** live in `diagnosis.py` as plain Python and must state where their thresholds
  come from (manufacturer documentation, field studies or measured data).
- Keep pull requests focused on one change and describe how you tested it.

## Reporting security issues

Please do not open public issues for security problems. See [SECURITY.md](SECURITY.md).
