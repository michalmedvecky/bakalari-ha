from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.bakalari import async_setup, async_unload_entry
from custom_components.bakalari.api import AuthenticationError
from custom_components.bakalari.services import WRITE_SERVICES


@pytest.fixture
async def account(hass, entry):
    api = SimpleNamespace(url="https://school.example", request=AsyncMock())
    entry.runtime_data = SimpleNamespace(client=api, async_request_refresh=AsyncMock())
    hass.config_entries._entries[entry.entry_id] = entry
    await async_setup(hass, {})
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


async def test_services_survive_last_account_unload(hass, account):
    from homeassistant.config_entries import ConfigEntryState

    with patch.object(
        type(hass.config_entries),
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        assert await async_unload_entry(hass, account)
    account._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
    assert hass.services.has_service("bakalari", "query")
    with pytest.raises(ServiceValidationError):
        await call(hass, account, "query", endpoint="user")
    account.runtime_data.client.request.assert_not_called()


async def test_unknown_entry_rejected(hass, account):
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "bakalari", "refresh", {"entry_id": "missing"}, blocking=True
        )


@pytest.mark.parametrize(
    ("action", "parameters"),
    [
        ("mark_message_read", {"message_id": "1"}),
        ("set_homework_done", {"homework_id": "1", "done": True}),
        ("confirm_marks", {"mark_ids": ["1"]}),
        (
            "send_message",
            {
                "title": "Test",
                "text": "Text",
                "recipient_type": "U",
                "recipients": ["T1"],
            },
        ),
        ("write_classbook", {"record_id": "1", "record": {"Id": "1"}}),
        ("web_login", {}),
    ],
)
async def test_read_only_blocks_all_mutations(hass, account, action, parameters):
    hass.config_entries.async_update_entry(account, options={"read_only": True})
    assert action in WRITE_SERVICES
    with pytest.raises(ServiceValidationError) as error:
        await call(hass, account, action, **parameters)
    assert error.value.translation_key == "read_only"
    account.runtime_data.client.request.assert_not_called()
    account.runtime_data.async_request_refresh.assert_not_called()


async def test_read_only_keeps_post_queries_and_predictions(hass, account):
    hass.config_entries.async_update_entry(account, options={"read_only": True})
    account.runtime_data.client.request.return_value = {"Messages": []}
    await call(hass, account, "query", endpoint="received")
    await call(
        hass,
        account,
        "predict_marks",
        marks=[{"Id": None, "MarkText": "1", "SubjectId": "M"}],
    )
    await call(hass, account, "refresh")
    assert account.runtime_data.client.request.await_count == 2
    account.runtime_data.async_request_refresh.assert_awaited_once()
