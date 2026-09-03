# Localized Component Prefixes

**Date:** 2026-09-03
**Status:** Approved (design)

## Problem

Entity display names are built in `dynamic_discovery.py` as:

```python
base_name = data.get("text", key)                                # from API, in the BOILER'S language
component_name = get_component_display_name(component, index)     # hardcoded ENGLISH (COMPONENT_NAMES)
name = f"{component_name} {base_name}"
```

The **field part** (`text`) already arrives localized from the boiler (e.g. French on a
French-configured unit). The **component prefix** (`"Hot Water"`, `"Heating Circuit"`,
`"Buffer Storage"`, …) is hardcoded English. So non-English users see franglais:

> "**Hot Water** 1 Température de consigne"
> "**Heating Circuit** 1 Température ambiante"

This is the real need behind discussion #189 / PR #190. PR #190 tried to solve it by adding
full per-key HA translations (~388 keys × languages), which is the wrong scale, breaks the
fallback name for every uncovered component (heater, heating circuit, buffer, heat pump…),
and requires ongoing per-firmware maintenance.

The actual problem is only the **17 component prefixes** in `COMPONENT_NAMES`.

## Goal

Localize the component prefixes for the shipped UI languages (en/de/fr) so the whole name
reads in the user's language, while keeping the field part from the API. Minimal, isolated
change; no per-key string maintenance; no entity-ID changes.

## Non-goals

- No full per-key translation (that is PR #190's rejected approach).
- No change to **which** components get a prefix (e.g. `weather` keeps its prefix; `system`
  keeps none) — changing that is out of scope and would alter en/de names too.
- No `has_entity_name` / `translation_key` usage — HA's static JSON translations cannot
  express "localized static prefix + dynamic API text". Independent of #186 and #190.

## Approach (chosen: A — per-language prefix dict)

### Data structure (`dynamic_discovery.py`)

`COMPONENT_NAMES` stays as the **English base / fallback**. Add overlays:

```python
COMPONENT_NAMES_TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        "hk": "Heizkreis",
        "autocomfort_hk": "Auto Comfort Heizkreis",
        "pu": "Pufferspeicher",
        "ww": "Warmwasser",
        "sk": "Solarkollektor",
        "se": "Solarertrag",
        "wp": "Wärmepumpe",
        "wp_data": "Wärmepumpe Daten",
        "circ": "Zirkulation",
        "weather": "Wetter",
        "forecast": "Vorhersage",
        "wireless": "Funksensor",
        "thirdparty": "Fremdsensor",
    },
    "fr": {
        "hk": "Circuit de chauffage",
        "autocomfort_hk": "Circuit de chauffage Auto Comfort",
        "pu": "Ballon tampon",
        "ww": "ECS",                 # from PR #190 (native speaker) — Eau Chaude Sanitaire
        "sk": "Solaire",             # from PR #190 (native speaker)
        "se": "Gain solaire",
        "wp": "Pompe à chaleur",
        "wp_data": "Données pompe à chaleur",
        "circ": "Circulation",
        "weather": "Météo",
        "forecast": "Prévisions",
        "wireless": "Capteur sans fil",
        "thirdparty": "Capteur tiers",
    },
}
```

Proper nouns are intentionally omitted (they fall through to the English base and stay
identical in every language): `pe` → "Pellematic", `stirling` → "Stirling",
`power` → "Smart PV", `system` → "System".

`ww` = "ECS" and `sk` = "Solaire" are taken verbatim from PR #190, authored by a native
French speaker. The components #190 did not cover (`hk`, `pu`, `se`, `wp`, `wp_data`,
`circ`, `forecast`, `wireless`, `thirdparty`) use best-effort French to be confirmed by
dubido38 in the issue/PR.

### Threading the language

- `get_component_display_name(component, index, language="en")` — look up the base type in
  `COMPONENT_NAMES_TRANSLATIONS.get(language, {})`, else fall back to `COMPONENT_NAMES`,
  else `base.upper()`. Index suffix behavior unchanged.
- `create_sensor_definition(..., language="en")` — pass `language` to
  `get_component_display_name`. `create_number_definition` / `create_select_definition` wrap
  `create_sensor_definition`, so they inherit it via the same param.
- `discover_all_entities(api_data, language="en")` — accept `language` and pass it into the
  per-entity definition builders.
- The four platform setup files call `discover_all_entities(data, language=hass.config.language)`:
  `sensor.py`, `binary_sensor.py`, `number.py`, `select.py`. `hass` is in scope in each
  `create_*_entities` factory closure.

`language="en"` is the default everywhere, so existing pure-function unit tests that call
`discover_all_entities(data)` keep working unchanged.

### Fallback chain

1. Unknown language → English base (`COMPONENT_NAMES`).
2. Known language, component missing in that language's overlay → English base.
3. Unknown component entirely → `base.upper()` (current behavior).

## What does not change

- `entity_id` / `object_id` / `unique_id` — **only the friendly `name`** changes. No
  migration, no `entity_id_snapshot.json` change (the snapshot keys on IDs, not names).
- The API `text` field still supplies the field portion of the name.
- On HA UI-language change, a config-entry reload is needed for names to update (same as the
  status quo, where names are computed once at setup). Document in README.

## Testing (fixture leverage)

- **Unit** (`tests/unit/`): `get_component_display_name` returns the de/fr prefix for known
  components, the English base for a missing-in-language component, `base.upper()` for an
  unknown component, and English for an unknown language. Index suffix still appended.
- **Fixture-based** (new test over all `tests/fixtures/*.json`): for `language in ("de", "fr")`,
  run `discover_all_entities(data, language=lang)` and assert, for every produced entity whose
  base component is a **known** component with a translation in that language:
  - the name starts with the localized prefix (no English prefix leakage), and
  - the name is non-empty.
  This is the "helps all users" regression guard: it also catches nameless-entity regressions
  of the #190 kind for the prefix path.

## Affected files

- `custom_components/oekofen_pellematic_compact/dynamic_discovery.py` — core change.
- `sensor.py`, `binary_sensor.py`, `number.py`, `select.py` — one-line call-site change each.
- `tests/unit/test_component_prefix_localization.py` — new.
- `README.md` — note about language + reload.

## Out of scope / follow-ups

- Confirming the best-effort French terms with dubido38.
- Additional UI languages beyond en/de/fr.
- Any per-key field translation (explicitly rejected).
