"""Ruční aktualizace dat účtu."""

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import BakalariEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [RefreshButton(entry.runtime_data, "user", "Aktualizovat", "mdi:refresh")]
    )


class RefreshButton(BakalariEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG

    async def async_press(self):
        await self.coordinator.async_request_refresh()
