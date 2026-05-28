import json
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "api_golden"
VOLATILE_KEYS = {"created_at", "updated_at"}

CASES = [
    ("api_test", "/api/test"),
    ("categories_index", "/api/categories"),
    ("tags_index", "/api/tags"),
    ("notes_index", "/api/notes?page=1&per_page=20"),
    ("note_detail", "/api/notes/1"),
]


def _normalize(value):
    if isinstance(value, dict):
        return {
            key: "<timestamp>" if key in VOLATILE_KEYS and item is not None else _normalize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _load_fixture(name):
    with (FIXTURE_DIR / f"{name}.json").open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def test_phase18_core_api_golden_responses(client):
    """Lock the Python baseline before frontend rewrite and Go read shadow work."""
    for name, path in CASES:
        response = client.get(path)
        actual = {
            "status_code": response.status_code,
            "json": _normalize(response.get_json()),
        }

        assert actual == _load_fixture(name)
