"""Domácí úkoly s příznakem dokončení žákem."""

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .api import BakalariError, path_id
from .entity import BakalariEntity
from .models import SCHOOL_TZ, homework_finished, parse_datetime, plain_text


async def async_setup_entry(hass, entry, async_add_entities):
    added = False

    @callback
    def discover():
        nonlocal added
        if not added and "homeworks" in entry.runtime_data.data:
            added = True
            async_add_entities(
                [
                    HomeworkList(
                        entry.runtime_data,
                        "homeworks",
                        "Domácí úkoly",
                        "mdi:clipboard-list",
                    )
                ]
            )

    discover()
    entry.async_on_unload(entry.runtime_data.async_add_listener(discover))


class HomeworkList(BakalariEntity, TodoListEntity):
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    @property
    def todo_items(self):
        items = []
        for task in (
            self.coordinator.data.get("homeworks", {}).get("Homeworks", []) or []
        ):
            if not task.get("ID"):
                continue
            due = parse_datetime(task.get("DateEnd"))
            subject = (task.get("Subject") or {}).get("Abbrev", "")
            items.append(
                TodoItem(
                    uid=task["ID"],
                    summary=f"{subject}: {plain_text(task.get('Content'))}".strip(": ")[
                        :255
                    ]
                    or "Úkol",
                    status=TodoItemStatus.COMPLETED
                    if homework_finished(task)
                    else TodoItemStatus.NEEDS_ACTION,
                    due=due.astimezone(SCHOOL_TZ).date() if due else None,
                    description=plain_text(task.get("Content")),
                )
            )
        return items

    async def async_update_todo_item(self, item):
        original = next((x for x in self.todo_items if x.uid == item.uid), None)
        if original is None:
            raise HomeAssistantError("Neznámý domácí úkol")
        if item.status not in (TodoItemStatus.COMPLETED, TodoItemStatus.NEEDS_ACTION):
            raise HomeAssistantError("Lze změnit pouze stav dokončení úkolu")
        if any(
            getattr(item, attr) is not None
            and getattr(item, attr) != getattr(original, attr)
            for attr in ("summary", "due", "description")
        ):
            raise HomeAssistantError("Lze změnit pouze stav dokončení úkolu")
        try:
            await self.coordinator.client.request(
                "PUT",
                f"/api/3/homeworks/{path_id(item.uid)}/student-done/{str(item.status == TodoItemStatus.COMPLETED).lower()}",
            )
        except BakalariError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
