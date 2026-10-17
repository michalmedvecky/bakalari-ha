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
