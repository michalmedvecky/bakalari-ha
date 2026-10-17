"""Kalendáře rozvrhu a školních akcí pouze pro čtení."""

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .api import BakalariError
from .endpoints import READS, validate_result
from .entity import BakalariEntity
from .models import event_end, event_start, in_range, school_events, timetable_events


async def async_setup_entry(hass, entry, async_add_entities):
    added = set()

    @callback
    def discover():
        for key in ("timetable", "events"):
            if key in entry.runtime_data.data and key not in added:
                added.add(key)
                async_add_entities(
                    [BakalariCalendar(entry.runtime_data, key, key, "mdi:calendar")]
                )

    discover()
    entry.async_on_unload(entry.runtime_data.async_add_listener(discover))


class BakalariCalendar(BakalariEntity, CalendarEntity):
    @property
    def event(self):
        data = self.coordinator.data.get(self.key, {})
        events = (
            timetable_events(data) if self.key == "timetable" else school_events(data)
        )
        upcoming = sorted(
            (e for e in events if event_end(e) > dt_util.now()),
            key=event_start,
        )
        return CalendarEvent(**upcoming[0]) if upcoming else None

    async def async_get_events(self, hass, start_date, end_date):
        try:
            if self.key == "timetable":
                events = [
                    event
                    for week in await self.coordinator.timetable_range(
                        start_date, end_date
                    )
                    for event in timetable_events(week)
                ]
            else:
                result = validate_result(
                    "events",
                    await self.coordinator.client.request(
                        "GET",
                        READS["events"].path,
                    ),
                )
                events = school_events(result)
            return [
                CalendarEvent(**event)
                for event in in_range(events, start_date, end_date)
            ]
        except BakalariError as err:
            raise HomeAssistantError(str(err)) from err
