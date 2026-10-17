"""Ochrana soukromí a velikosti i pro ostatní podrobné atributy."""

from custom_components.bakalari.attributes import (
    MAX_ATTRIBUTE_BYTES,
    bounded_attributes,
    json_size,
)


def test_generic_details_remain_small_and_drop_long_body_fields():
    attributes = bounded_attributes(
        {
            "data": {
                "Subjects": [
                    {
                        "Name": "Ž" * 3000,
                        "Text": "SECRET",
                        "PrivateNotice": "SECRET",
                        "Marks": [{"Caption": "Č" * 3000}] * 100,
                    }
                ]
                * 100
            }
        }
    )
    assert json_size(attributes) <= MAX_ATTRIBUTE_BYTES
    assert attributes["details_truncated"]
    assert "SECRET" not in str(attributes)


def test_non_finite_values_and_deep_payloads_are_json_safe():
    value = {
        "data": {
            "value": float("inf"),
            "nested": {
                "nested": {"nested": {"nested": {"nested": {"nested": "SECRET"}}}}
            },
        }
    }
    attributes = bounded_attributes(value)
    assert json_size(attributes) <= MAX_ATTRIBUTE_BYTES
    assert attributes["data"]["value"] is None
    assert "SECRET" not in str(attributes)
