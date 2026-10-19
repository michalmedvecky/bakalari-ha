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
        (
            "send_apology",
            {"date_from": "2026-10-19", "date_to": "2026-10-19", "reason": "Nemoc"},
        ),
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


def apology_types(recipients):
    return {
        "MessageTypes": [
            {
                "Abbreviation": "OBECNA",
                "RecipientsTypes": [
                    {"Code": "U", "Recipients": [{"Code": "OTHER", "IsDefault": True}]}
                ],
            },
            {
                "Abbreviation": "OMLUVENKA",
                "RecipientsTypes": [{"Code": "U", "Recipients": recipients}],
            },
        ],
        "Recipients": [{"Code": "OTHER", "IsDefault": True}],
    }


APOLOGY = {"date_from": "2026-10-24", "date_to": "2026-10-25", "reason": " Nemoc "}


@pytest.mark.parametrize(
    "recipients",
    [
        [{"Code": "T1", "IsDefault": True}, {"Code": "T2", "IsDefault": False}],
        [{"Code": "T1", "IsDefault": False}],
    ],
)
async def test_apology_selects_teacher_and_local_calendar_dates(
    hass, account, recipients
):
    hass.config.time_zone = "Europe/Prague"
    client = account.runtime_data.client
    client.request.side_effect = [apology_types(recipients), {"Message": ""}]
    result = await hass.services.async_call(
        "bakalari",
        "send_apology",
        {"entry_id": account.entry_id, **APOLOGY},
        blocking=True,
        return_response=True,
    )
    assert result == {
        "result": {"Message": ""},
        "dry_run": False,
        "sent": True,
        "recipient": {"id": "T1", "name": None},
        "message_id": None,
    }
    assert client.request.await_count == 2
    assert client.request.await_args_list[0].args == (
        "GET",
        "/api/3/komens/message-types",
    )
    client.request.assert_awaited_with(
        "POST",
        "/api/3/komens/message",
        json={
            "MessageType": "OMLUVENKA",
            "Title": "Omluvenka 24.10.2026",
            "Text": "Nemoc",
            "RecipientType": "U",
            "Recipients": ["T1"],
            "DateFrom": "2026-10-24T00:00:00+02:00",
            "DateTo": "2026-10-25T23:59:59+01:00",
        },
    )
    account.runtime_data.async_request_refresh.assert_awaited_once()


@pytest.mark.parametrize(
    ("response", "error_key"),
    [
        ({"MessageTypes": []}, "apology_unavailable"),
        ({}, "apology_response"),
        (None, "apology_response"),
        ({"MessageTypes": "bad"}, "apology_response"),
        ({"MessageTypes": [{"Abbreviation": "OMLUVENKA"}]}, "apology_response"),
        (apology_types([{"Code": ""}]), "apology_response"),
        (apology_types([None]), "apology_response"),
        (apology_types([]), "apology_recipient"),
        (apology_types([{"Code": "T1"}, {"Code": "T2"}]), "apology_recipient"),
        (
            apology_types(
                [{"Code": "T1", "IsDefault": True}, {"Code": "T2", "IsDefault": True}]
            ),
            "apology_recipient",
        ),
        (
            {
                "MessageTypes": [
                    {
                        "Abbreviation": "OMLUVENKA",
                        "RecipientsTypes": [
                            {
                                "Code": "UV",
                                "Recipients": [{"Code": "ALL", "IsDefault": True}],
                            }
                        ],
                    }
                ]
            },
            "apology_recipient",
        ),
    ],
)
async def test_apology_does_not_send_without_unambiguous_recipient(
    hass, account, response, error_key
):
    account.runtime_data.client.request.return_value = response
    with pytest.raises(ServiceValidationError) as error:
        await call(hass, account, "send_apology", **APOLOGY)
    assert error.value.translation_key == error_key
    account.runtime_data.client.request.assert_awaited_once_with(
        "GET", "/api/3/komens/message-types"
    )
    account.runtime_data.async_request_refresh.assert_not_called()


@pytest.mark.parametrize(
    "overrides",
    [
        {"reason": "   "},
        {"date_from": "2026-02-30"},
        {"date_to": "2026-10-25T12:00:00"},
        {"recipients": ["T1"]},
    ],
)
async def test_apology_rejects_invalid_fields_before_network(hass, account, overrides):
    with pytest.raises(vol.Invalid):
        await call(hass, account, "send_apology", **{**APOLOGY, **overrides})
    account.runtime_data.client.request.assert_not_called()


async def test_apology_rejects_reversed_dates_before_network(hass, account):
    with pytest.raises(ServiceValidationError) as error:
        await call(
            hass, account, "send_apology", **{**APOLOGY, "date_to": "2026-10-23"}
        )
    assert error.value.translation_key == "apology_dates"
    account.runtime_data.client.request.assert_not_called()


async def test_apology_accepts_single_day_and_does_not_retry_failed_post(hass, account):
    from custom_components.bakalari.api import BakalariError

    account.runtime_data.client.request.side_effect = [
        apology_types([{"Code": "T1", "IsDefault": True}]),
        BakalariError("Offline"),
    ]
    with pytest.raises(HomeAssistantError, match="Offline"):
        await call(
            hass, account, "send_apology", **{**APOLOGY, "date_to": "2026-10-24"}
        )
    assert account.runtime_data.client.request.await_count == 2
    account.runtime_data.async_request_refresh.assert_not_called()


async def test_apology_auth_failure_starts_reauth_without_sending(hass, account):
    account.runtime_data.client.request.side_effect = AuthenticationError()
    with patch.object(type(account), "async_start_reauth") as reauth:
        with pytest.raises(HomeAssistantError):
            await call(hass, account, "send_apology", **APOLOGY)
    reauth.assert_called_once_with(hass)
    assert account.runtime_data.client.request.await_count == 1


@pytest.mark.parametrize("read_only", [False, True])
async def test_apology_preview_only_reads_and_returns_named_recipient(
    hass, account, read_only
):
    hass.config.time_zone = "Europe/Prague"
    hass.config_entries.async_update_entry(account, options={"read_only": read_only})
    account.runtime_data.client.request.return_value = apology_types(
        [{"Code": "T1", "DisplayName": " Pan učitel ", "IsDefault": True}]
    )
    response = await hass.services.async_call(
        "bakalari",
        "send_apology",
        {
            "entry_id": account.entry_id,
            **APOLOGY,
            "dry_run": True,
            "date_to": "2026-10-24",
            "time_from": "08:00:00",
            "time_to": "08:45:00",
            "title": " Pozdní vlak ",
        },
        blocking=True,
        return_response=True,
    )
    assert response["result"] is None
    assert not response["sent"] and response["dry_run"]
    assert response["message_id"] is None
    assert response["recipient"] == {"id": "T1", "name": "Pan učitel"}
    assert response["payload"]["Title"] == "Pozdní vlak"
    assert response["payload"]["DateFrom"] == "2026-10-24T08:00:00+02:00"
    assert response["payload"]["DateTo"] == "2026-10-24T08:45:00+02:00"
    account.runtime_data.client.request.assert_awaited_once_with(
        "GET", "/api/3/komens/message-types"
    )
    account.runtime_data.async_request_refresh.assert_not_called()


async def test_apology_preview_requires_response_variable(hass, account):
    with pytest.raises(ServiceValidationError) as error:
        await call(hass, account, "send_apology", **APOLOGY, dry_run=True)
    assert error.value.translation_key == "apology_preview_response"
    account.runtime_data.client.request.assert_not_called()


@pytest.mark.parametrize(
    "fields",
    [
        {"time_from": "08:00:00"},
        {"time_to": "08:45:00"},
        {"time_from": "09:00:00", "time_to": "08:00:00"},
        {"time_from": "08:00:00", "time_to": "08:00:00"},
        {
            "date_from": "2026-10-25",
            "date_to": "2026-10-25",
            "time_from": "02:15:00",
            "time_to": "03:15:00",
        },
        {
            "date_from": "2026-03-29",
            "date_to": "2026-03-29",
            "time_from": "02:15:00",
            "time_to": "03:15:00",
        },
    ],
)
async def test_invalid_or_dst_ambiguous_times_do_not_contact_school(
    hass, account, fields
):
    hass.config.time_zone = "Europe/Prague"
    with pytest.raises(ServiceValidationError):
        await call(
            hass,
            account,
            "send_apology",
            **{**APOLOGY, "date_to": "2026-10-24", **fields},
        )
    account.runtime_data.client.request.assert_not_called()


@pytest.mark.parametrize(
    ("raw", "message_id"),
    [
        ({"Message": ""}, None),
        ({"Id": "M1"}, "M1"),
        ({"MessageId": "M2"}, "M2"),
        ({"Message": {"Id": "M3"}}, "M3"),
        ({"Message": "Some text"}, None),
    ],
)
async def test_apology_sending_returns_only_explicit_id(hass, account, raw, message_id):
    account.runtime_data.client.request.side_effect = [
        apology_types([{"Code": "T1", "Name": "Učitel"}]),
        raw,
    ]
    response = await hass.services.async_call(
        "bakalari",
        "send_apology",
        {
            "entry_id": account.entry_id,
            **APOLOGY,
            "date_to": "2026-10-24",
            "time_from": "08:00:00",
            "time_to": "08:45:00",
        },
        blocking=True,
        return_response=True,
    )
    assert response["result"] == raw
    assert response["message_id"] == message_id
    assert response["recipient"] == {"id": "T1", "name": "Učitel"}
    assert response["sent"] and not response["dry_run"]
    assert "payload" not in response
    assert account.runtime_data.client.request.await_count == 2
    payload = account.runtime_data.client.request.await_args_list[1].kwargs["json"]
    assert "T08:00:00" in payload["DateFrom"]
    account.runtime_data.async_request_refresh.assert_awaited_once()


@pytest.mark.parametrize("message_type", ["NASSKO", "AKTUAL", "OTHER"])
async def test_generic_message_rejects_publication_types(hass, account, message_type):
    with pytest.raises(vol.Invalid):
        await call(
            hass,
            account,
            "send_message",
            message_type=message_type,
            title="Test",
            text="Text",
            recipient_type="U",
            recipients=["T1"],
        )
    account.runtime_data.client.request.assert_not_called()
