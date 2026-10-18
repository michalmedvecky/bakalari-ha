"""Omluvenky s příjemcem určeným školním API pro daný účet."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN


def apology_payload(data, response, time_zone):
    """Vybere výchozího či jediného povoleného učitele bez odhadování podle jména."""

    def reject(key):
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key=key)

    if not isinstance(response, dict) or not isinstance(
        response.get("MessageTypes"), list
    ):
        reject("apology_response")
    types = [
        item
        for item in response["MessageTypes"]
        if isinstance(item, dict) and item.get("Abbreviation") == "OMLUVENKA"
    ]
    if not types:
        reject("apology_unavailable")
    if len(types) != 1 or not isinstance(types[0].get("RecipientsTypes"), list):
        reject("apology_response")
    teachers = {}
    for group in types[0]["RecipientsTypes"]:
        if not isinstance(group, dict):
            reject("apology_response")
        if group.get("Code") != "U":
            continue
        recipients = group.get("Recipients")
        if not isinstance(recipients, list):
            reject("apology_response")
        for recipient in recipients:
            if (
                not isinstance(recipient, dict)
                or not isinstance(recipient.get("Code"), str)
                or not recipient["Code"].strip()
            ):
                reject("apology_response")
            code = recipient["Code"]
            teachers[code] = (
                teachers.get(code, False) or recipient.get("IsDefault") is True
            )
    defaults = [code for code, is_default in teachers.items() if is_default]
    if len(defaults) == 1:
        teacher = defaults[0]
    elif not defaults and len(teachers) == 1:
        teacher = next(iter(teachers))
    else:
        reject("apology_recipient")
    zone = ZoneInfo(time_zone)
    return {
        "MessageType": "OMLUVENKA",
        "Title": "",
        "Text": data["reason"],
        "RecipientType": "U",
        "Recipients": [teacher],
        "DateFrom": datetime.combine(data["date_from"], time.min, zone).isoformat(),
        "DateTo": datetime.combine(data["date_to"], time(23, 59, 59), zone).isoformat(),
    }
