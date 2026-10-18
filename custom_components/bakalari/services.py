"""Validované akce konkrétního účtu s pevně určenými operacemi API."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import AuthenticationError, BakalariError, path_id
from .apologies import apology_payload
from .const import CONF_READ_ONLY, DOMAIN
from .endpoints import READS, validate_result

SERVICE_NAMES = (
    "refresh",
    "query",
    "mark_message_read",
    "set_homework_done",
    "confirm_marks",
    "predict_marks",
    "send_message",
    "send_apology",
    "write_classbook",
    "get_attachment",
    "web_login",
)
BASE = {vol.Required("entry_id"): cv.string}
WRITE_SERVICES = frozenset(
    {
        "mark_message_read",
        "set_homework_done",
        "confirm_marks",
        "send_message",
        "send_apology",
        "write_classbook",
        "web_login",
    }
)


def async_register_services(hass):
    if hass.services.has_service(DOMAIN, "query"):
        return

    async def handle(call):
        entry = hass.config_entries.async_get_entry(call.data["entry_id"])
        if (
            entry is None
            or entry.domain != DOMAIN
            or not hasattr(entry, "runtime_data")
            or entry.runtime_data is None
        ):
            raise ServiceValidationError("Vyberte načtený konfigurační záznam Bakalářů")
        from homeassistant.config_entries import ConfigEntryState

        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("Konfigurační záznam Bakalářů není načtený")
        coordinator = entry.runtime_data
        client = coordinator.client
        data = call.data
        name = call.service
        if name in WRITE_SERVICES and entry.options.get(CONF_READ_ONLY, False):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="read_only"
            )
        result = None
        try:
            if name == "refresh":
                await coordinator.async_request_refresh()
                return None
            if name == "query":
                key = data["endpoint"]
                endpoint = READS[key]
                # Výslovný dotaz může načíst i nezjištěný volitelný či učitelský modul;
                # o přístupu rozhoduje školní server.
                path = endpoint.path
                if "{id}" in path:
                    if not data.get("id"):
                        raise ServiceValidationError("Tento endpoint vyžaduje pole id")
                    path = path.format(id=path_id(data["id"]))
                result = validate_result(
                    key,
                    await client.request(
                        endpoint.method, path, params=data.get("parameters")
                    ),
                )
            elif name == "mark_message_read":
                await client.request(
                    "PUT",
                    f"/api/3/komens/message/{path_id(data['message_id'])}/mark-as-read",
                )
            elif name == "set_homework_done":
                await client.request(
                    "PUT",
                    f"/api/3/homeworks/{path_id(data['homework_id'])}/student-done/{str(data['done']).lower()}",
                )
            elif name == "confirm_marks":
                await client.request(
                    "POST",
                    "/api/3/marks/SetClassificationConfirmation",
                    json=data["mark_ids"],
                )
            elif name == "predict_marks":
                result = await client.request(
                    "POST", "/api/3/marks/what-if", json=data["marks"]
                )
            elif name == "send_apology":
                if data["date_to"] < data["date_from"]:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN, translation_key="apology_dates"
                    )
                types = await client.request("GET", "/api/3/komens/message-types")
                payload = apology_payload(data, types, hass.config.time_zone)
                result = await client.request(
                    "POST", "/api/3/komens/message", json=payload
                )
            elif name == "send_message":
                payload = {
                    "MessageType": data["message_type"],
                    "Title": data["title"],
                    "Text": data["text"],
                    "RecipientType": data["recipient_type"],
                    "Recipients": data["recipients"],
                    **data.get("options", {}),
                }
                result = await client.request(
                    "POST", "/api/3/komens/message", json=payload
                )
            elif name == "write_classbook":
                payload = data["record"]
                if payload.get("Id") != data["record_id"]:
                    raise ServiceValidationError(
                        "Hodnota record.Id musí odpovídat record_id"
                    )
                result = await client.request(
                    "POST",
                    f"/api/3/classbook/{path_id(data['record_id'])}",
                    json=payload,
                )
            elif name == "get_attachment":
                result = await client.request(
                    "GET",
                    f"/api/3/komens/attachment/{path_id(data['attachment_id'])}",
                    binary=True,
                )
            elif name == "web_login":
                token = await client.request("GET", "/api/3/logintoken")
                if not isinstance(token, str) or not token:
                    raise BakalariError("Neplatný token pro webové přihlášení")
                # Jednorázový token se vrací pouze volající akci, nikoli do entity.
                result = {
                    "url": f"{client.url}/api/3/login/{path_id(token)}?returnUrl=next%2Fdash.aspx"
                }
            else:
                raise ServiceValidationError("Neznámá akce")
            if name in (
                "mark_message_read",
                "set_homework_done",
                "confirm_marks",
                "write_classbook",
                "send_message",
                "send_apology",
            ):
                await coordinator.async_request_refresh()
        except AuthenticationError as err:
            entry.async_start_reauth(hass)
            raise HomeAssistantError("Je nutné opětovné přihlášení") from err
        except (BakalariError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        return {"result": result} if call.return_response else None

    options_schema = vol.Schema(
        {
            vol.Optional("Lifetime"): vol.Any(None, str),
            vol.Optional("DateFrom"): vol.Any(None, str),
            vol.Optional("DateTo"): vol.Any(None, str),
            vol.Optional("PreviousMessageId"): vol.Any(None, str),
            vol.Optional("CopyForClassTeacher"): bool,
            vol.Optional("CopyForParent"): bool,
            vol.Optional("EmailNotification"): bool,
            vol.Optional("SendAsDirector"): bool,
            vol.Optional("RequireConfirmation"): bool,
            vol.Optional("TypeOfRatingId"): vol.Any(None, str),
            vol.Optional("Scale"): vol.Any(None, str, int),
            vol.Optional("Attachments"): [dict],
            vol.Optional("DraftDate"): vol.Any(None, str),
        }
    )
    nonempty_ids = vol.All([cv.string], vol.Length(min=1))
    schemas = {
        "refresh": {},
        "query": {
            vol.Required("endpoint"): vol.In(READS),
            vol.Optional("id"): cv.string,
            vol.Optional("parameters", default={}): {str: vol.Any(str, int, float)},
        },
        "mark_message_read": {vol.Required("message_id"): cv.string},
        "set_homework_done": {
            vol.Required("homework_id"): cv.string,
            vol.Required("done"): cv.boolean,
        },
        "confirm_marks": {vol.Required("mark_ids"): nonempty_ids},
        "predict_marks": {vol.Required("marks"): vol.All([dict], vol.Length(min=1))},
        "send_message": {
            vol.Required("message_type", default="OBECNA"): cv.string,
            vol.Required("title"): cv.string,
            vol.Required("text"): cv.string,
            vol.Required("recipient_type"): cv.string,
            vol.Required("recipients"): [cv.string],
            vol.Optional("options", default={}): options_schema,
        },
        "send_apology": {
            vol.Required("date_from"): cv.date,
            vol.Required("date_to"): cv.date,
            vol.Required("reason"): vol.All(cv.string, str.strip, vol.Length(min=1)),
        },
        "write_classbook": {
            vol.Required("record_id"): cv.string,
            vol.Required("record"): dict,
        },
        "get_attachment": {vol.Required("attachment_id"): cv.string},
        "web_login": {},
    }
    for name in SERVICE_NAMES:
        hass.services.async_register(
            DOMAIN,
            name,
            handle,
            schema=vol.Schema({**BASE, **schemas[name]}),
            supports_response=SupportsResponse.ONLY
            if name in ("query", "predict_marks", "get_attachment", "web_login")
            else SupportsResponse.OPTIONAL
            if name in ("send_message", "send_apology", "write_classbook")
            else SupportsResponse.NONE,
        )
