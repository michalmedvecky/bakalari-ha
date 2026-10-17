"""Přítomnost podle přístupového systému školy."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import callback

from .entity import BakalariEntity


async def async_setup_entry(hass, entry, async_add_entities):
    added = False

    @callback
    def discover():
        nonlocal added
        if not added and "student_present" in entry.runtime_data.data:
            added = True
            async_add_entities(
                [
                    StudentPresent(
                        entry.runtime_data,
                        "student_present",
                        "student_present",
                        "mdi:school",
                    )
                ]
            )

    discover()
    entry.async_on_unload(entry.runtime_data.async_add_listener(discover))


class StudentPresent(BakalariEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    @property
    def is_on(self):
        return self.coordinator.data.get(self.key)
