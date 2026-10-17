from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import AbortFlow, FlowResultType

from custom_components.bakalari.api import AuthenticationError, BakalariError
from custom_components.bakalari.config_flow import (
    BakalariConfigFlow,
    BakalariOptionsFlow,
    account_id,
)

INPUT = {
    "url": "https://school.example/baka/login/",
    "username": "test",
    "password": "secret",
}


def flow(hass):
    result = BakalariConfigFlow()
    result.hass = hass
    result.context = {"source": "user"}
    result.handler = "bakalari"
    return result


async def test_user_success_and_normalized_url(hass):
    instance = flow(hass)
    with (
        patch("custom_components.bakalari.config_flow.async_get_clientsession"),
        patch("custom_components.bakalari.config_flow.BakalariClient") as factory,
    ):
        factory.return_value.user = AsyncMock(
            return_value={"UserUID": "uid", "FullName": "Test"}
        )
        result = await instance.async_step_user(INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test"
    assert result["data"]["url"] == "https://school.example/baka"
    assert instance.unique_id == account_id("https://school.example/baka", "uid")


@pytest.mark.parametrize(
    ("error", "expected"),
    [(AuthenticationError(), "invalid_auth"), (BakalariError(), "cannot_connect")],
)
async def test_user_errors(hass, error, expected):
    instance = flow(hass)
    with (
        patch("custom_components.bakalari.config_flow.async_get_clientsession"),
        patch("custom_components.bakalari.config_flow.BakalariClient") as factory,
    ):
        factory.return_value.user = AsyncMock(side_effect=error)
        result = await instance.async_step_user(INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}


async def test_bad_url_does_not_connect(hass):
    result = await flow(hass).async_step_user({**INPUT, "url": "broken"})
    assert result["errors"] == {"base": "invalid_url"}


async def test_duplicate_account(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    hass.config_entries.async_update_entry(
        entry, unique_id=account_id("https://school.example/baka", "uid")
    )
    with (
        patch("custom_components.bakalari.config_flow.async_get_clientsession"),
        patch("custom_components.bakalari.config_flow.BakalariClient") as factory,
    ):
        factory.return_value.user = AsyncMock(return_value={"UserUID": "uid"})
        with pytest.raises(AbortFlow, match="already_configured"):
            await flow(hass).async_step_user(INPUT)


async def test_reauth_keeps_account_identity(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    instance = flow(hass)
    instance.context = {"source": "reauth", "entry_id": entry.entry_id}
    with (
        patch("custom_components.bakalari.config_flow.async_get_clientsession"),
        patch("custom_components.bakalari.config_flow.BakalariClient") as factory,
    ):
        factory.return_value.user = AsyncMock(return_value={"UserUID": "someone-else"})
        result = await instance.async_step_reauth_confirm(INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


async def test_reauth_updates_credentials(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    hass.config_entries.async_update_entry(
        entry, unique_id=account_id("https://school.example/baka", "uid")
    )
    instance = flow(hass)
    instance.context = {"source": "reauth", "entry_id": entry.entry_id}
    with (
        patch("custom_components.bakalari.config_flow.async_get_clientsession"),
        patch("custom_components.bakalari.config_flow.BakalariClient") as factory,
        patch.object(type(hass.config_entries), "async_schedule_reload") as reload,
    ):
        factory.return_value.user = AsyncMock(return_value={"UserUID": "uid"})
        result = await instance.async_step_reauth_confirm(
            {**INPUT, "password": "new-password"}
        )
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new-password"
    reload.assert_called_once_with(entry.entry_id)


async def test_options(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    instance = BakalariOptionsFlow()
    instance.hass = hass
    instance.handler = entry.entry_id
    result = await instance.async_step_init()
    assert result["type"] is FlowResultType.FORM
    options = {"scan_interval": 600, "modules": ["Marks"], "expose_details": False}
    result = await instance.async_step_init(options)
    assert result["data"] == options
