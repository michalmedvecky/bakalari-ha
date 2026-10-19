"""Omezené atributy entit; těla zpráv a jiné dlouhé texty se nezveřejňují."""

import json
import math

from .models import parse_datetime, plain_text

MAX_ATTRIBUTE_BYTES = 8192
MAX_DETAIL_ITEMS = 10
OMITTED_FIELDS = frozenset(
    {
        "Text",
        "Content",
        "Notice",
        "PrivateNotice",
        "Description",
        "Theme",
        "SubjectNote",
        "TemporaryMarkNote",
    }
)


def json_size(value):
    # ASCII zápis je konzervativní i pro serializéry escapující české znaky.
    return len(json.dumps(value, ensure_ascii=True, allow_nan=False).encode("utf-8"))


def bounded_attributes(attributes):
    """Omezí texty, vnoření a celkovou velikost včetně informace o zkrácení."""
    truncated = False

    def clean(value, depth=0):
        nonlocal truncated
        if isinstance(value, str):
            text = value
            truncated |= len(text) > 160
            return text[:160]
        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if depth > 5:
            truncated = True
            return None
        if isinstance(value, list):
            truncated |= len(value) > MAX_DETAIL_ITEMS
            return [clean(item, depth + 1) for item in value[:MAX_DETAIL_ITEMS]]
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in OMITTED_FIELDS or len(result) >= 20:
                    truncated = True
                    continue
                result[str(key)[:64]] = clean(item, depth + 1)
            return result
        truncated = True
        return None

    result = clean(attributes)

    # Nejprve zmenšuje seznamy. Základní skalární údaje senzorů zůstávají zachované.
    def lists(value):
        if isinstance(value, list):
            if value:
                yield value
            for item in value:
                yield from lists(item)
        elif isinstance(value, dict):
            for item in value.values():
                yield from lists(item)

    while json_size(result) > MAX_ATTRIBUTE_BYTES - 64:
        candidates = list(lists(result))
        if not candidates:
            return {"details_truncated": True}
        max(candidates, key=json_size).pop()
        truncated = True
    if truncated:
        result["details_truncated"] = True
    return result


def message_summary(message):
    """Pouze výslovně povolená metadata, nikdy Text ani další neznámá pole."""
    sender = message.get("Sender") or {}
    return {
        **{key: message.get(key) for key in ("Id", "SentDate", "Read")},
        "Title": plain_text(message.get("Title")),
        "Sender": {"Name": plain_text(sender.get("Name"))}
        if isinstance(sender, dict)
        else {},
        "attachment_count": len(message.get("Attachments") or []),
    }


def mark_summary(mark):
    """Krátké hodnocení bez popisu práce, komentářů a údajů o podpisu."""
    return {
        key: mark.get(key)
        for key in ("Id", "MarkText", "MarkDate", "Weight", "IsNew", "IsPoints")
    }


def newest_messages(messages):
    """Nejnovější nejprve bez závislosti na pořadí vráceném serverem."""

    def key(message):
        parsed = parse_datetime(message.get("SentDate"))
        return parsed.timestamp() if parsed else float("-inf")

    return sorted(messages, key=key, reverse=True)
