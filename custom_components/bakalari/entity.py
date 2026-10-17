"""Společné chování entit."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .models import school_model


class BakalariEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, translation_key, icon):
        super().__init__(coordinator)
        self.key = key
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{key}"
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id)},
            name=coordinator.entry.title,
            manufacturer="Bakaláři",
            model=school_model(coordinator.profile.get("SchoolOrganizationName")),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.client.url,
        )

    @property
    def available(self):
        return super().available and self.key in self.coordinator.data
