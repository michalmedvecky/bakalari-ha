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
    value = AsyncMock()
    value.url = "https://school.example"
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
