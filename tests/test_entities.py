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


async def test_subject_average_preserves_server_format_and_hides_details(coordinator):
    entity = SubjectSensor(coordinator, "M", "Math")
    assert entity.available
    assert entity.native_value == "2,86"
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
