import json
from pathlib import Path

import pytest
import yaml
from homeassistant.helpers import selector

from custom_components.bakalari.api import BakalariError
from custom_components.bakalari.endpoints import READS, validate_result
from custom_components.bakalari.services import SERVICE_NAMES

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/bakalari"


def test_action_descriptions_and_selectors_match_registration():
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    assert set(services) == set(SERVICE_NAMES)
    for action in services.values():
        for field in action["fields"].values():
            selector.validate_selector(field["selector"])
    options = services["query"]["fields"]["endpoint"]["selector"]["select"]["options"]
    assert set(options) == set(READS)


def test_translations_cover_form_fields():
    for language in ("cs", "en"):
        data = json.loads((COMPONENT / "translations" / f"{language}.json").read_text())
        assert set(data["config"]["step"]) == {"user", "reauth_confirm", "reconfigure"}
        assert set(data["options"]["step"]["init"]["data"]) == {
            "scan_interval",
            "modules",
            "expose_details",
            "read_only",
        }
    assert json.loads((COMPONENT / "strings.json").read_text()) == json.loads(
        (COMPONENT / "translations/en.json").read_text()
    )


@pytest.mark.parametrize(
    "result", [None, [], {}, {"Subjects": None}, {"Subjects": ["bad"]}]
)
def test_malformed_collections_rejected(result):
    with pytest.raises(BakalariError):
        validate_result("marks", result)


def test_component_syntax_does_not_require_pep758():
    import ast

    for source in COMPONENT.glob("*.py"):
        ast.parse(source.read_text(), filename=str(source), feature_version=(3, 13))


def test_all_entity_and_action_translations_exist():
    from custom_components.bakalari.sensor import DESCRIPTIONS

    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    for language in ("cs", "en"):
        data = json.loads((COMPONENT / "translations" / f"{language}.json").read_text())
        assert set(data["services"]) == set(SERVICE_NAMES)
        assert all(
            description[1] in data["entity"]["sensor"] for description in DESCRIPTIONS
        )
        assert "{subject}" in data["entity"]["sensor"]["subject_average"]["name"]
        for action, schema in services.items():
            assert set(data["services"][action]["fields"]) == set(schema["fields"])
            assert data["services"][action]["description"]


@pytest.mark.parametrize(
    ("language", "entity_name", "action_name"),
    [("cs", "Aktualizovat", "Aktualizovat"), ("en", "Refresh", "Refresh")],
)
async def test_homeassistant_loads_translated_entity_and_service_names(
    hass, loaded_integration, language, entity_name, action_name
):
    from homeassistant.helpers.translation import async_get_translations

    entities = await async_get_translations(hass, language, "entity", {"bakalari"})
    actions = await async_get_translations(hass, language, "services", {"bakalari"})
    assert entities["component.bakalari.entity.button.refresh.name"] == entity_name
    assert actions["component.bakalari.services.refresh.name"] == action_name
