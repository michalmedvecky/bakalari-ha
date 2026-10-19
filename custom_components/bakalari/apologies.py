"""Omluvenky s příjemcem určeným školním API pro daný účet."""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN


def apology_range(data, time_zone):
    """Připraví místní interval a odmítne neexistující či dvojznačné časy."""
    paired = ("time_from" in data, "time_to" in data)
    if paired[0] != paired[1]:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="apology_times"
        )
    zone = ZoneInfo(time_zone)
    bounds = []
    for date_key, time_key, default in (
        ("date_from", "time_from", time.min),
        ("date_to", "time_to", time(23, 59, 59)),
    ):
        clock = data.get(time_key, default)
        local = datetime.combine(data[date_key], clock)
        aware = local.replace(tzinfo=zone)
        if clock.tzinfo is not None or (
            aware.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != local
            or aware.utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset()
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="apology_times"
            )
        bounds.append(aware)
    if bounds[1].astimezone(UTC) <= bounds[0].astimezone(UTC):
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="apology_dates"
        )
    return tuple(bound.isoformat() for bound in bounds)


def apology_payload(data, response, bounds):
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
    names = {}
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
            name = recipient.get("DisplayName") or recipient.get("Name")
            if isinstance(name, str):
                names[code] = name.strip()
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
    title = data.get("title") or f"Omluvenka {data['date_from']:%d.%m.%Y}"
    return {
        "MessageType": "OMLUVENKA",
        "Title": title,
        "Text": data["reason"],
        "RecipientType": "U",
        "Recipients": [teacher],
        "DateFrom": bounds[0],
        "DateTo": bounds[1],
    }, {"id": teacher, "name": names.get(teacher)}


def sent_message_id(response):
    """Vrátí jen ID výslovně obsažené v odpovědi; prázdný Message není ID."""
    if not isinstance(response, dict):
        return None
    nested = response.get("Message")
    for value in (
        response.get("Id"),
        response.get("MessageId"),
        nested.get("Id") if isinstance(nested, dict) else None,
    ):
        if (
            isinstance(value, (str, int))
            and not isinstance(value, bool)
            and str(value).strip()
        ):
            return str(value).strip()
    return None
