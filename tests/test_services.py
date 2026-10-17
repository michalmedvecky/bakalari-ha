from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.bakalari.api import AuthenticationError
from custom_components.bakalari.services import (
    async_register_services,
    async_remove_services,
)


@pytest.fixture
async def account(hass, entry):
    api = AsyncMock()
    api.url = "https://school.example"
    entry.runtime_data = SimpleNamespace(client=api, async_request_refresh=AsyncMock())
    hass.config_entries._entries[entry.entry_id] = entry
    async_register_services(hass)
    return entry


async def call(hass, account, action, **kwargs):
    return await hass.services.async_call(
        "bakalari",
        action,
        {"entry_id": account.entry_id, **kwargs},
        blocking=True,
        return_response=action
        in ("query", "predict_marks", "get_attachment", "web_login"),
    )


async def test_query_scopes_path_and_preserves_post_reads(hass, account):
    account.runtime_data.client.request.return_value = {"Messages": []}
    result = await call(hass, account, "query", endpoint="received")
    assert result == {"result": {"Messages": []}}
    account.runtime_data.client.request.assert_awaited_once_with(
        "POST", "/api/3/komens/messages/received", params={}
    )


async def test_query_requires_id(hass, account):
    with pytest.raises(ServiceValidationError):
        await call(hass, account, "query", endpoint="themes")


async def test_no_arbitrary_endpoint_proxy(hass, account):
    with pytest.raises(vol.Invalid):
        await call(hass, account, "query", endpoint="https://other.example/secret")
    account.runtime_data.client.request.assert_not_called()


async def test_homework_writes_and_refreshes(hass, account):
    await call(hass, account, "set_homework_done", homework_id="A[ X", done=True)
    account.runtime_data.client.request.assert_awaited_once_with(
        "PUT", "/api/3/homeworks/A%5B%20X/student-done/true"
    )
    account.runtime_data.async_request_refresh.assert_awaited_once()


async def test_read_message(hass, account):
    await call(hass, account, "mark_message_read", message_id="1")
    account.runtime_data.client.request.assert_awaited_once_with(
        "PUT", "/api/3/komens/message/1/mark-as-read"
    )


async def test_confirm_marks(hass, account):
    await call(hass, account, "confirm_marks", mark_ids=["m1", "m2"])
    account.runtime_data.client.request.assert_awaited_once_with(
        "POST", "/api/3/marks/SetClassificationConfirmation", json=["m1", "m2"]
    )


async def test_send_message_payload(hass, account):
    await call(
        hass,
        account,
        "send_message",
        message_type="OBECNA",
        title="Test",
        text="Content",
        recipient_type="U",
        recipients=["T1"],
        options={"RequireConfirmation": True},
    )
    payload = account.runtime_data.client.request.call_args.kwargs["json"]
    assert payload["Recipients"] == ["T1"]
    assert payload["RequireConfirmation"] is True
    assert payload["MessageType"] == "OBECNA"


async def test_options_cannot_override_message_recipient(hass, account):
    with pytest.raises(vol.Invalid):
        await call(
            hass,
            account,
            "send_message",
            title="Test",
            text="Content",
            recipient_type="U",
            recipients=["T1"],
            options={"Recipients": ["all"]},
        )


async def test_classbook_id_must_match(hass, account):
    with pytest.raises(ServiceValidationError):
        await call(hass, account, "write_classbook", record_id="A", record={"Id": "B"})
    account.runtime_data.client.request.assert_not_called()


async def test_web_login_returns_single_use_url(hass, account):
    account.runtime_data.client.request.return_value = "single use"
    result = await call(hass, account, "web_login")
    assert result["result"]["url"].endswith(
        "/api/3/login/single%20use?returnUrl=next%2Fdash.aspx"
    )


async def test_auth_failure_starts_reauth(hass, account):
    account.runtime_data.client.request.side_effect = AuthenticationError()
    with patch.object(type(account), "async_start_reauth") as reauth:
        with pytest.raises(HomeAssistantError):
            await call(hass, account, "query", endpoint="user")
    reauth.assert_called_once_with(hass)


async def test_services_removed_with_last_account(hass, account):
    async_remove_services(hass, account.entry_id)
    assert not hass.services.has_service("bakalari", "query")


async def test_unknown_entry_rejected(hass, account):
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "bakalari", "refresh", {"entry_id": "missing"}, blocking=True
        )
