"""Převody dat společné pro entity a testy."""

from __future__ import annotations

import html
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SCHOOL_TZ = ZoneInfo("Europe/Prague")


def plain_text(value):
    return html.unescape(re.sub(r"<[^>]*>", " ", str(value or ""))).strip()


def parse_datetime(value):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.year < 1900:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=SCHOOL_TZ)
    except ValueError:
        return None


def homework_finished(item):
    # Finished označuje dokončení žákem; Done/Closed patří postupu učitele.
    return bool(item.get("Finished", False))


def school_events(data):
    events = []
    for item in data.get("Events", []) or []:
        for index, slot in enumerate(item.get("Times", []) or []):
            start, end = (
                parse_datetime(slot.get("StartTime")),
                parse_datetime(slot.get("EndTime")),
            )
            if start is None or end is None or end < start:
                continue
            if slot.get("WholeDay"):
                start = start.astimezone(SCHOOL_TZ).date()
                end = end.astimezone(SCHOOL_TZ).date() + timedelta(days=1)
            elif end == start:
                continue
            events.append(
                {
                    "start": start,
                    "end": end,
                    "summary": item.get("Title") or "Událost",
                    "description": plain_text(item.get("Description")),
                    "uid": f"{item.get('Id')}_{index}",
                    "location": ", ".join(
                        r.get("Abbrev", "") for r in item.get("Rooms", []) or []
                    ),
                }
            )
    return events


def timetable_events(data):
    tables = {
        key: {str(item["Id"]): item for item in data.get(key, []) or []}
        for key in ("Hours", "Subjects", "Teachers", "Rooms")
    }
    events = []
    for day in data.get("Days", []) or []:
        parsed_day = parse_datetime(day.get("Date"))
        if parsed_day is None:
            continue
        lesson_date = parsed_day.astimezone(SCHOOL_TZ).date()
        for index, atom in enumerate(day.get("Atoms", []) or []):
            change = atom.get("Change") or {}
            if change.get("ChangeType") in ("Removed", "Canceled"):
                continue
            hour = tables["Hours"].get(str(atom.get("HourId")), {})
            try:

                def lesson_time(field):
                    parts = str(hour[field]).split(":")
                    return datetime.combine(
                        lesson_date, time(int(parts[0]), int(parts[1])), SCHOOL_TZ
                    )

                start, end = lesson_time("BeginTime"), lesson_time("EndTime")
            except KeyError, ValueError, IndexError:
                continue
            if end <= start:
                continue
            subject = tables["Subjects"].get(str(atom.get("SubjectId")), {})
            teacher = tables["Teachers"].get(str(atom.get("TeacherId")), {})
            room = tables["Rooms"].get(str(atom.get("RoomId")), {})
            events.append(
                {
                    "start": start,
                    "end": end,
                    "summary": subject.get("Name") or subject.get("Abbrev") or "Výuka",
                    "description": "\n".join(
                        filter(
                            None,
                            (
                                teacher.get("Name"),
                                plain_text(atom.get("Theme")),
                                change.get("Description"),
                            ),
                        )
                    ),
                    "location": room.get("Abbrev") or room.get("Name") or "",
                    "uid": f"{lesson_date}_{atom.get('HourId')}_{index}",
                }
            )
    return events


def event_start(event):
    value = event["start"]
    return (
        datetime.combine(value, time.min, SCHOOL_TZ) if type(value) is date else value
    )


def event_end(event):
    value = event["end"]
    return (
        datetime.combine(value, time.min, SCHOOL_TZ) if type(value) is date else value
    )


def in_range(events, start, end):
    unique = {
        e["uid"]: e for e in events if event_start(e) < end and event_end(e) > start
    }
    return sorted(unique.values(), key=event_start)
