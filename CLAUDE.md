# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Home Assistant **custom component** (`domain: oekofen_pellematic_compact`) that talks locally to Ökofen Pellematic Compact heaters via their TCP/JSON interface (`http://<ip>:<port>/<password>/all`). Distributed via HACS. The component lives entirely in `custom_components/oekofen_pellematic_compact/`.

## Commands

```bash
# Activate the local dev environment (Home Assistant is pre-installed here)
source .venv/bin/activate

# Run Home Assistant against the test config (uses ./config and serves on :8123)
./start_homeassistant.sh
# or:   hass -c config --debug

# Tests
pytest tests/                                  # all tests
pytest tests/test_discovery.py -v              # one file
pytest tests/test_discovery.py::test_name -v   # one test
pytest tests/unit/                             # fast unit tests only

# Tail integration-relevant log lines
./monitor_logs.sh
```

There is no lint/format config — don't add one without checking. Hassfest validation runs in CI (`.github/workflows/hassfest Action.yml`).

## Architecture

### Dynamic discovery is the core idea

All sensor/select/number/binary_sensor definitions are **discovered at runtime from API metadata** — there are no hard-coded entity lists. The old approach (~1300 lines of `*_SENSOR_TYPES` constants) was removed; see the note at the bottom of `const.py`. When adding support for new Ökofen features, do **not** add per-key definitions — extend the discovery logic instead.

The pipeline:

1. **`__init__.py`** — `PellematicHub.fetch_pellematic_data()` polls the API on `scan_interval`. The Ökofen API requires ≥ 2500 ms between requests; the hub enforces a 2.5 s minimum interval per-instance (rate limiter in `fetch_pellematic_data`).
2. **`dynamic_discovery.py`** — `discover_all_entities(api_data)` walks the API response and classifies each field:
   - Keys starting with `L_` → read-only sensor (or binary sensor if `format` is `0:x|1:y`)
   - Keys without `L_` that match `is_read_only_statistic(...)` (totals, runtimes, `_yesterday`, etc.) → sensor, not number
   - Writable + `format` with >2 options → select
   - Writable + `format` with 2 options → select (not binary, because it's settable)
   - Select options are strings `"<api value>_<label slug>"` (`parse_select_options`), where the prefix is the **API value, not a list index** — `select.py` maps both directions through that prefix. Never index into `options`: `autocomfort` reports `-1` when the feature is off (Python's negative indexing then picked the last option), and `format` need not number its entries contiguously.
   - Writable + `min`/`max` → number
   - Otherwise → sensor fallback
3. **Platform files** (`sensor.py`, `binary_sensor.py`, `select.py`, `number.py`, `climate.py`) — each `async_setup_entry` calls `discover_all_entities()` via the shared `setup_platform_with_retry()` helper in `__init__.py`. If the API hasn't returned data yet, setup is retried every 60 s; this is why entities can appear up to a minute after install.
4. **Binary sensors are their own platform** (`binary_sensor.py`, `PLATFORMS = ["sensor", "binary_sensor", "select", "number", "climate"]`). `PellematicBinarySensor` itself is still defined in `sensor.py` (historic location, imported by `binary_sensor.py`). Older versions registered them on the `sensor` platform, so existing installs have orphan `sensor.*` entries — these are surfaced via the Repairs platform (`repairs.py`); the fix flow deletes the orphans and reloads the entry so `binary_sensor.py` recreates them. Auto-renaming via `entity_registry.async_update_entity` is **not** an option — HA forbids cross-domain renames (`raise ValueError("New entity ID should be same domain")` in `entity_registry.py`).

### API quirks the code must handle

These are workarounds for real firmware behavior — when touching the request/parse path, keep them:

- **Two response shapes:** modern firmware returns `{"val": 123, "unit": "°C", "factor": 0.1, ...}`; old firmware (≤ v3.10d) returns bare values. Detected by `_api_response_has_metadata()` in `__init__.py`. Use `get_api_value()` from `const.py` to read either shape.
- **API suffix:** `?` vs `??` is **decoupled from metadata** (issue #191). Most firmware uses `?`; some old Euro firmware exposes richer metadata only via `??`; some US 3.10 firmware *drops the connection* on `??` and must use `?` even though it returns bare values. `_detect_api_config()` chooses empirically — probe `?`, only switch to `??` if it yields strictly richer (metadata) data or `?` failed — preferring `?`. The `old_firmware` flag now only means "response has no metadata" and never forces the suffix. Stored as `CONF_API_SUFFIX`. Mirror any change in `config_flow.py::_fetch_api_data` (auto-detect branch).
- **Charset:** can be UTF-8 or ISO-8859-1, sometimes mixed within one response. `_detect_api_config` uses a 20%-replacement-character heuristic. The default is `iso-8859-1` for safety.
- **Invalid JSON in responses:**
  - `L_statetext:` → `L_statetext":` (firmware 4.02 bug)
  - Unescaped control characters inside string values (`\n`, `\r`, `\t`) — escaped via regex in `fetch_data()` and in `tests/conftest.py::load_fixture` (keep them in sync).
- **Sentinel values:** `_sanitize_oekofen_value()` in `sensor.py` (used by `sensor.py` *and* `number.py`) drops exactly two things: the int16 "not available" markers `32765…32767` / `-32768…-32766` (`_is_sentinel_value()`, skipped for keys whose declared range reaches past int16 — ms-based times go up to 14400000), and readings more than a full range beyond `min`/`max` (`_is_out_of_scale()`, e.g. `L_storage_max` = 304366 kg). Do **not** reintroduce a "close to min/max" rule: a genuine limit is a normal value (issue #193 — `L_cfg_uw_runon` = max = 120 min), while settings slightly outside their range are real user data (`solarheat_off_tmp` = 810 with max 800). `min`/`max` may arrive as strings; `_as_number()` handles that, and `raw_data` may be a bare value on old firmware.

### Component prefix convention

Auto-discovered components use these prefixes (`discover_components_from_api` in `__init__.py`):
`pe` (heater), `hk` (heating circuit), `ww` (hot water), `pu` (buffer), `sk`/`se` (solar), `wp` (heat pump), `wireless`, plus singletons `stirling`, `circ1`, `power` (Smart PV), `system`.

Entity IDs follow `{platform}.{hub_name}_{component}_{key}` — e.g. `sensor.pellematic_pe1_L_temp_act`. The `key` is the **raw API key** on purpose (language-independent, stable across firmware). Don't translate or normalize it into entity IDs.

### Entity ID migration (`migration.py`)

`async_migrate_entity_ids()` runs **once** per config entry on first startup after an upgrade. It detects pre-4.0 patterns like `sensor.pellematic_heater_1_*` → `sensor.pellematic_pe1_*` and preserves the old `entity_id` (keeping user automations working) while updating the `unique_id`/`object_id` mapping. The "already ran" flag is `MIGRATION_NOTIFICATION_SHOWN_KEY` in `entry.data` — both flags from setup are persisted in a single `async_update_entry` call to avoid the "first write succeeds, second clobbers it" footgun (see the comment in `async_setup_entry`).

Config entry version is currently `2`. `async_migrate_entry` handles V1→V2 (adds missing component counts + auto-detects charset/suffix). Bumping the version requires adding another branch there.

The binary-sensor domain fix lives in `migration.py::async_refresh_legacy_binary_sensor_repair_issue` (called on every `async_setup_entry`) plus `repairs.py::FixLegacyBinarySensorsFlow`. Both auto-clear once the registry no longer has orphan `sensor.*` entries that look like binary sensors.

Whether an orphan "looks like a binary sensor" is decided by `_looks_like_legacy_binary_sensor()` in two stages: (1) resolve the object_id against the live API response — component slug anywhere in the ID, the remaining words matched against the raw key *or* the slugified `text` — and mirror discovery's classification via `_discovery_makes_binary_sensor()`; (2) only for IDs that name nothing in the current response, fall back to `_LEGACY_BINARY_KEY_SUFFIXES` + `_SUFFIX_TO_API_KEYS`. Never widen the verdict beyond `is_binary_sensor()` alone: writable two-option fields (`heat_once`, `oekomode`) pass that check but become **selects**, and flagging anything discovery recreates as a non-binary entity produces an endless repair loop (issues #191-style regressions: modulation pumps, and #192 for translated names like French `L_pump_release` = "T démarrage pompe"). `tests/unit/test_repair_no_loop_against_fixtures.py` asserts both directions for every legacy ID shape of every fixture.

### Service

`oekofen_pellematic_compact.rediscover_components` re-fetches the API, recomputes component counts, updates the config entry, and reloads it. Useful when the user adds hardware (a new heating circuit) without re-adding the integration.

## Tests

- `tests/fixtures/*.json` are **real, anonymized API responses** from many different installations (different firmware versions, languages, hardware combos). These are the regression bedrock — when fixing a parsing bug, the fixture from the affected user often already exists or should be added.
- `tests/conftest.py::load_fixture` applies the **same JSON-repair logic** as `fetch_data()` in production. If you change one, change the other.
- `tests/unit/` contains fast pure-function tests (charset detection, suffix detection, encoding); the top-level `test_*.py` files are integration-ish tests that exercise discovery against real fixtures.
- `tests/entity_id_snapshot.json` is a checked-in snapshot of every entity ID the integration produces from each fixture — `test_entity_id_snapshot.py` fails if entity IDs change unexpectedly. Update it deliberately, not as a "make the test pass" reflex.

## Conventions specific to this repo

- The `manifest.json` `version` field uses a `v` prefix (e.g. `"v4.2.9"`) — HACS accepts this but the leading `v` is unusual; keep it consistent when bumping.
- README is the user-facing doc; `MIGRATION_GUIDE.md` is the source of truth for the entity ID migration behavior — keep it in sync when changing `migration.py`.
- The integration has no external Python dependencies (`requirements: []` in manifest); use `urllib` rather than adding `aiohttp`/`requests`.
- Blocking HTTP calls (`urllib.request.urlopen`) are wrapped via `hass.async_add_executor_job` — keep that pattern, don't call them from the event loop directly.
- Commit messages and PR descriptions carry **no AI/Claude attribution** (no `Co-Authored-By: Claude`, no "Generated with" footer) — the project's commit history stays tool-agnostic.
