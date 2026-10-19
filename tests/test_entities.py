from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.exceptions import HomeAssistantError

from custom_components.bakalari.calendar import BakalariCalendar
from custom_components.bakalari.coordinator import BakalariCoordinator
from custom_components.bakalari.diagnostics import async_get_config_entry_diagnostics
from custom_components.bakalari.sensor import BakalariSensor, SubjectSensor
from custom_components.bakalari.todo import HomeworkList


@pytest.fixture
async def coordinator(hass, entry):
    client = SimpleNamespace(url="https://school.example", request=AsyncMock())
    value = BakalariCoordinator(hass, entry, client)
    value.async_set_updated_data(
        {
            "user": {},
            "marks": {
                "Subjects": [
                    {
                        "Subject": {"Id": "M", "Name": "Math"},
                        "AverageText": "2,86 ",
                        "Marks": [{"Id": "1", "MarkText": "3"}],
                    }
                ]
            },
            "homeworks": {
                "Homeworks": [
                    {
                        "ID": "A[",
                        "DateEnd": "2026-10-19T00:00:00+02:00",
                        "Content": "<div>Test</div>",
                        "Done": True,
                        "Finished": False,
                        "Subject": {"Abbrev": "M"},
                    }
                ]
            },
        }
    )
    value.async_request_refresh = AsyncMock()
    entry.runtime_data = value
    yield value
    await entry._async_process_on_unload(hass)
    del entry.runtime_data


async def test_subject_average_trims_text_and_hides_details(coordinator):
    entity = SubjectSensor(coordinator, "M", "Math")
    assert entity.available
    assert entity.native_value == 2.86
    assert entity.extra_state_attributes["average_text"] == "2,86"
    assert entity.state_class == "measurement"
    assert "marks" not in entity.extra_state_attributes
    assert entity.extra_state_attributes["mark_count"] == 1
    coordinator.async_set_updated_data({"user": {}})
    assert not entity.available
    assert entity.native_value is None


async def test_homeworks_completion_only(coordinator):
    entity = HomeworkList(coordinator, "homeworks", "Tasks", "mdi:clipboard")
    task = entity.todo_items[0]
    assert task.status is TodoItemStatus.NEEDS_ACTION
    assert task.summary == "M: Test"
    assert task.due.isoformat() == "2026-10-19"
    await entity.async_update_todo_item(
        TodoItem(uid="A[", status=TodoItemStatus.COMPLETED)
    )
    coordinator.client.request.assert_awaited_once_with(
        "PUT", "/api/3/homeworks/A%5B/student-done/true"
    )
    coordinator.async_request_refresh.assert_awaited_once()
    with pytest.raises(HomeAssistantError):
        await entity.async_update_todo_item(
            TodoItem(uid="A[", summary="Rename", status=TodoItemStatus.COMPLETED)
        )


async def test_missing_module_unavailable(coordinator):
    entity = BakalariSensor(
        coordinator, "unread", "Unread", "mdi:email", lambda d: d, 1
    )
    assert not entity.available
    assert entity.native_value is None


async def test_details_opt_in(coordinator, hass):
    hass.config_entries._entries[coordinator.entry.entry_id] = coordinator.entry
    hass.config_entries.async_update_entry(
        coordinator.entry, options={"expose_details": True}
    )
    assert (
        SubjectSensor(coordinator, "M", "Math").extra_state_attributes["marks"][0]["Id"]
        == "1"
    )


async def test_calendar_range_reads_server_not_just_current_cache(coordinator, hass):
    coordinator.client.request.return_value = {
        "Events": [
            {
                "Id": "event",
                "Title": "Trip",
                "Times": [
                    {
                        "WholeDay": True,
                        "StartTime": "2026-11-02T00:00:00+01:00",
                        "EndTime": "2026-11-02T23:59:00+01:00",
                    }
                ],
            }
        ]
    }
    entity = BakalariCalendar(coordinator, "events", "Events", "mdi:calendar")
    tz = ZoneInfo("Europe/Prague")
    results = await entity.async_get_events(
        hass, datetime(2026, 11, 1, tzinfo=tz), datetime(2026, 12, 1, tzinfo=tz)
    )
    assert len(results) == 1
    assert results[0].all_day
    assert results[0].end.isoformat() == "2026-11-03"


async def test_diagnostics_does_not_leak_credentials_or_content(
    coordinator, hass, loaded_integration
):
    import json

    result = await async_get_config_entry_diagnostics(hass, coordinator.entry)
    text = json.dumps(result)
    for secret in ("secret", "school.example", "MarkText", "UserUID", "Test account"):
        assert secret not in text
    assert result["last_update_success"]


async def test_diagnostics_uses_loader_version(coordinator, hass):
    from types import SimpleNamespace
    from unittest.mock import patch

    with patch(
        "custom_components.bakalari.diagnostics.async_get_integration",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(version="9.8.7"),
    ):
        result = await async_get_config_entry_diagnostics(hass, coordinator.entry)
    assert result["integration_version"] == "9.8.7"


async def test_read_only_homeworks_hide_updates_and_reject_direct_calls(
    coordinator, hass
):
    from homeassistant.components.todo import TodoListEntityFeature

    hass.config_entries._entries[coordinator.entry.entry_id] = coordinator.entry
    entity = HomeworkList(coordinator, "homeworks", "homeworks", "mdi:clipboard")
    assert entity.supported_features == TodoListEntityFeature.UPDATE_TODO_ITEM
    hass.config_entries.async_update_entry(
        coordinator.entry, options={"read_only": True}
    )
    assert entity.supported_features == 0
    assert entity.todo_items[0].uid == "A["
    with pytest.raises(HomeAssistantError) as error:
        await entity.async_update_todo_item(
            TodoItem(uid="A[", status=TodoItemStatus.COMPLETED)
        )
    assert error.value.translation_key == "read_only"
    coordinator.client.request.assert_not_called()


@pytest.mark.parametrize(
    ("language", "expected"),
    [("cs", "Matematika – průměr"), ("en", "Matematika average")],
)
async def test_subject_name_uses_ha_translations(
    coordinator, hass, loaded_integration, language, expected
):
    from types import SimpleNamespace

    from homeassistant.helpers.translation import async_get_translations

    translations = await async_get_translations(hass, language, "entity", {"bakalari"})
    entity = SubjectSensor(coordinator, "M", "Matematika")
    entity.platform_data = SimpleNamespace(platform_name="bakalari", domain="sensor")
    assert entity._name_internal(None, translations) == expected
    assert entity.unique_id == "account-id_marks_M"


@pytest.mark.parametrize(
    ("average", "number", "unit"),
    [("1,47", 1.47, None), ("87,5 %", 87.5, "%"), ("slovní hodnocení", None, None)],
)
async def test_numeric_subject_average_and_units(coordinator, average, number, unit):
    coordinator.data["marks"]["Subjects"][0]["AverageText"] = average
    entity = SubjectSensor(coordinator, "M", "Math")
    assert entity.native_value == number
    assert entity.native_unit_of_measurement == unit
    assert entity.extra_state_attributes["average_text"] == average


async def test_new_marks_uses_is_new_and_keeps_legacy_id(coordinator):
    from custom_components.bakalari.sensor import DESCRIPTIONS

    coordinator.data["marks"]["Subjects"][0]["Marks"] = [{"IsNew": True}] * 10 + [
        {"IsNew": False}
    ]
    coordinator.data["new_marks"] = 0
    key, name, icon, extract = DESCRIPTIONS[0]
    entity = BakalariSensor(coordinator, key, name, icon, extract, 0)
    assert entity.available
    assert entity.native_value == 10
    assert entity.unique_id == "account-id_new_marks_0"
    assert entity.extra_state_attributes == {"source": "marks.IsNew", "server_count": 0}
    del coordinator.data["new_marks"]
    assert entity.available
    assert entity.native_value == 10


@pytest.mark.parametrize("key", ["received", "noticeboard"])
@pytest.mark.parametrize("count", [10, 500])
async def test_message_attributes_never_contain_bodies_and_fit_recorder(
    coordinator, hass, key, count
):
    import json

    from custom_components.bakalari.attributes import MAX_ATTRIBUTE_BYTES, json_size

    hass.config_entries._entries[coordinator.entry.entry_id] = coordinator.entry
    hass.config_entries.async_update_entry(
        coordinator.entry, options={"expose_details": True}
    )
    message = {
        "Id": "ID" * 500,
        "Title": "Nadpis žluťoučký" * 500,
        "Text": "<p>SECRET_SCHOOL_PASSWORD</p>" * 1000,
        "SentDate": "2026-10-17T08:00:00+02:00",
        "Read": False,
        "Sender": {"Name": "Učitel" * 500, "Text": "NESTED_SECRET"},
        "Attachments": [{"Name": "SECRET_ATTACHMENT"}],
    }
    coordinator.data[key] = {"Messages": [message] * count}
    entity = BakalariSensor(
        coordinator, key, key, "mdi:email", lambda d: len(d["Messages"]), 5
    )
    attributes = entity.extra_state_attributes
    serialized = json.dumps(attributes)
    for secret in (
        "SECRET_SCHOOL_PASSWORD",
        "NESTED_SECRET",
        "SECRET_ATTACHMENT",
        '"Text"',
    ):
        assert secret not in serialized
    assert attributes["data"]["message_count"] == count
    assert attributes["data"]["messages_truncated"]
    assert attributes["data"]["Messages"][0]["attachment_count"] == 1
    assert json_size(attributes) <= MAX_ATTRIBUTE_BYTES
    assert coordinator.data[key]["Messages"][0]["Text"].startswith("<p>SECRET")


async def test_many_marks_are_bounded_summaries(coordinator, hass):
    import json

    from custom_components.bakalari.attributes import MAX_ATTRIBUTE_BYTES, json_size

    hass.config_entries._entries[coordinator.entry.entry_id] = coordinator.entry
    hass.config_entries.async_update_entry(
        coordinator.entry, options={"expose_details": True}
    )
    coordinator.data["marks"]["Subjects"][0]["Marks"] = [
        {
            "Id": "Ž" * 1000,
            "MarkText": "1",
            "MarkDate": "2026-10-17",
            "Weight": 5,
            "Caption": "PRIVATE_CAPTION",
            "Theme": "PRIVATE_THEME",
            "ConfirmedBy": "PRIVATE_PERSON",
        }
    ] * 2000
    attributes = SubjectSensor(coordinator, "M", "Math").extra_state_attributes
    assert attributes["mark_count"] == 2000
    assert attributes["marks_truncated"]
    assert len(attributes["marks"]) <= 10
    assert json_size(attributes) <= MAX_ATTRIBUTE_BYTES
    assert "PRIVATE_" not in json.dumps(attributes)


async def test_device_model_falls_back_from_placeholder(coordinator):
    coordinator.profile["SchoolOrganizationName"] = "název školy"
    assert (
        SubjectSensor(coordinator, "M", "Math").device_info["model"]
        == "Bakaláři API v3"
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("key", ["received", "noticeboard"])
async def test_messages_keep_newest_regardless_of_server_order(
    hass, coordinator, reverse, key
):
    hass.config_entries._entries[coordinator.entry.entry_id] = coordinator.entry
    hass.config_entries.async_update_entry(
        coordinator.entry, options={"expose_details": True}
    )
    messages = [
        {"Id": str(i), "SentDate": f"2026-10-{i:02d}T08:00:00+02:00"}
        for i in range(1, 12)
    ]
    if reverse:
        messages.reverse()
    coordinator.data[key] = {"Messages": messages}
    entity = BakalariSensor(
        coordinator, key, key, "mdi:email", lambda d: len(d["Messages"]), 0
    )
    data = entity.extra_state_attributes["data"]
    assert [item["Id"] for item in data["Messages"]] == [
        str(i) for i in range(11, 1, -1)
    ]
    assert data["messages_truncated"]
    assert data["message_count"] == 11
    assert coordinator.data[key]["Messages"] == messages


async def test_subject_metadata_strips_whitespace_without_changing_identity(
    coordinator,
):
    subject = coordinator.data["marks"]["Subjects"][0]
    subject["Subject"]["Id"] = " 2"
    subject["AverageText"] = "1,00 "
    entity = SubjectSensor(coordinator, " 2", "Test")
    assert entity.extra_state_attributes["subject_id"] == "2"
    assert entity.extra_state_attributes["average_text"] == "1,00"
    assert entity.unique_id.endswith("_ 2")
    assert entity.available and entity.native_value == 1.0
