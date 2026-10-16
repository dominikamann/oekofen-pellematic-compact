# Tests

```bash
pip install -r requirements_test.txt
pytest tests/                 # everything
pytest tests/unit/            # fast unit tests
pytest tests/unit/test_diagnosis.py -v
```

| Path | Content |
|---|---|
| `fixtures/` | Real, anonymized `/all?` responses from many installations (firmware versions, languages, hardware). The regression base: every parsing fix adds the affected response here. |
| `conftest.py` | `load_fixture()` applies the same JSON repair as the integration (`fetch_data()`); keep both in sync. |
| `entity_id_snapshot.json` | All entity IDs produced from every fixture; `test_entity_id_snapshot.py` fails on unintended changes. |
| `unit/` | Pure-function tests and full-setup tests with a real Home Assistant (`hass` fixture). |
| `test_*.py` | Discovery, platform and migration tests against all fixtures. |
