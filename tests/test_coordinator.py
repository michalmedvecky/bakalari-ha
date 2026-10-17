from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.bakalari.api import (
    AuthenticationError,
    BakalariError,
    EndpointError,
)
from custom_components.bakalari.coordinator import BakalariCoordinator


def client():
    value = SimpleNamespace(
        url="https://school.example", user=AsyncMock(), request=AsyncMock()
    )
    value.user.return_value = {
        "UserUID": "student",
        "EnabledModules": [
            {"Module": "Marks", "Rights": ["ShowMarks"]},
            {"Module": "Homeworks", "Rights": ["ShowHomeworks"]},
        ],
    }
    return value


async def test_partial_failure_does_not_disable_healthy_module(hass, entry):
    api = client()

    async def request(method, path, **kwargs):
        if "marks" in path:
            raise EndpointError(403)
        if "count-actual" in path:
            return 0
        return {"Homeworks": []}

    api.request.side_effect = request
    coordinator = BakalariCoordinator(hass, entry, api)
    data = await coordinator._async_update_data()
    assert data["homeworks"] == {"Homeworks": []}
    assert "marks" not in data
    assert coordinator.errors["marks"] == "403"
    assert not any("timetable" in str(c) for c in api.request.call_args_list)


async def test_auth_failure_triggers_reauth(hass, entry):
    api = client()
    api.request.side_effect = AuthenticationError()
    with pytest.raises(ConfigEntryAuthFailed):
        await BakalariCoordinator(hass, entry, api)._async_update_data()


async def test_user_failure_is_update_failed(hass, entry):
    api = client()
    api.user.side_effect = BakalariError("offline")
    with pytest.raises(UpdateFailed):
        await BakalariCoordinator(hass, entry, api)._async_update_data()


async def test_options_and_rights(hass, entry):
    coordinator = BakalariCoordinator(hass, entry, client())
    coordinator.profile = {
        "EnabledModules": [{"Module": "Marks", "Rights": ["ShowMarks"]}]
    }
    assert coordinator.allowed("marks")
    assert not coordinator.allowed("final_marks")
    assert not coordinator.allowed("received")
    coordinator.profile = {"UserUID": "student"}
    assert coordinator.allowed("marks")


async def test_bad_shape_is_unavailable_not_zero(hass, entry):
    api = client()
    api.request.return_value = None
    coordinator = BakalariCoordinator(hass, entry, api)
    data = await coordinator._async_update_data()
    assert "homework_count" not in data
    assert coordinator.errors["homework_count"] == "communication_or_data"


async def test_timetable_fetches_all_weeks_and_caches(hass, entry):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Europe/Prague")
    api = client()
    api.request.return_value = {"Days": [], "Hours": []}
    coordinator = BakalariCoordinator(hass, entry, api)
    start, end = datetime(2026, 10, 19, tzinfo=tz), datetime(2026, 11, 3, tzinfo=tz)
    assert len(await coordinator.timetable_range(start, end)) == 3
    await coordinator.timetable_range(start, end)
    assert api.request.call_count == 3


def lesson_week(day):
    return {
        "Days": [
            {
                "Date": day + "T00:00:00+02:00",
                "Atoms": [{"HourId": 1, "SubjectId": "M"}],
            }
        ],
        "Hours": [{"Id": 1, "BeginTime": "8:00", "EndTime": "8:45"}],
        "Subjects": [{"Id": "M", "Name": "Matematika"}],
    }


@pytest.mark.parametrize(
    "now",
    [
        "2026-10-16T17:00:00+02:00",
        "2026-10-17T12:00:00+02:00",
        "2026-10-18T12:00:00+02:00",
    ],
)
async def test_calendar_has_next_monday_after_last_lesson(hass, entry, now):
    from datetime import datetime
    from unittest.mock import patch

    from custom_components.bakalari.calendar import BakalariCalendar

    api = client()
    api.user.return_value = {
        "UserUID": "student",
        "EnabledModules": [{"Module": "Timetable", "Rights": ["ShowTimetable"]}],
    }

    async def request(method, path, *, params):
        return lesson_week(
            "2026-10-19" if params["date"] == "2026-10-19" else "2026-10-16"
        )

    api.request.side_effect = request
    coordinator = BakalariCoordinator(hass, entry, api)
    with patch(
        "custom_components.bakalari.coordinator.dt_util.now",
        return_value=datetime.fromisoformat(now),
    ):
        data = await coordinator._async_update_data()
        coordinator.async_set_updated_data(data)
        entity = BakalariCalendar(coordinator, "timetable", "timetable", "mdi:calendar")
        assert entity.state == "off"
        assert entity.event.start.isoformat() == "2026-10-19T08:00:00+02:00"
        assert entity.state_attributes["message"] == "Matematika"
        assert api.request.await_count == 2
        # Požadavek z kalendáře využije tentýž už načtený následující týden.
        await coordinator.timetable_range(
            datetime.fromisoformat("2026-10-19T00:00:00+02:00"),
            datetime.fromisoformat("2026-10-20T00:00:00+02:00"),
        )
        assert api.request.await_count == 2


async def test_next_week_error_keeps_current_timetable(hass, entry):
    api = client()
    api.user.return_value = {
        "UserUID": "student",
        "EnabledModules": [{"Module": "Timetable", "Rights": ["ShowTimetable"]}],
    }
    api.request.side_effect = [lesson_week("2026-10-16"), EndpointError(500)]
    coordinator = BakalariCoordinator(hass, entry, api)
    data = await coordinator._async_update_data()
    assert "timetable" in data
    assert "timetable_next" not in data
    assert coordinator.errors == {"timetable_next": "500"}


async def test_diagnostics_distinguish_absent_modules_and_missing_rights(
    hass, entry, loaded_integration
):
    from custom_components.bakalari.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    api = client()
    api.user.return_value = {
        "UserUID": "student",
        "EnabledModules": [{"Module": "Marks", "Rights": ["ShowMarks"]}],
    }

    async def request(method, path, **kwargs):
        if path.endswith("count-new"):
            return 0
        if path.endswith("measures"):
            return {"PedagogicalMeasures": []}
        return {"Subjects": []}

    api.request.side_effect = request
    coordinator = BakalariCoordinator(hass, entry, api)
    coordinator.async_set_updated_data(await coordinator._async_update_data())
    entry.runtime_data = coordinator
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["skipped_modules"]["Homeworks"] == "module_not_available"
    assert result["skipped_endpoints"]["final_marks"] == {
        "module": "Marks",
        "reason": "missing_right",
    }
    assert result["endpoint_errors"] == {}
    assert "marks" in result["available_endpoints"]
    # Změna profilu při dalším načtení odstraní dřívější důvody vynechání.
    api.user.return_value["EnabledModules"] = None
    await coordinator._async_update_data()
    assert coordinator.skipped_modules == {}
    assert coordinator.skipped_endpoints == {}


async def test_disabled_modules_have_distinct_reason(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    hass.config_entries.async_update_entry(entry, options={"modules": []})
    coordinator = BakalariCoordinator(hass, entry, client())
    await coordinator._async_update_data()
    assert coordinator.skipped_modules["Marks"] == "disabled_by_options"
    coordinator.client.request.assert_not_called()
