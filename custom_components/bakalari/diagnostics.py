"""Diagnostika struktury bez přihlašovacích údajů a školních dat."""

from homeassistant.loader import async_get_integration

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    integration = await async_get_integration(hass, DOMAIN)
    return {
        "integration_version": integration.version,
        "poll_interval_seconds": coordinator.update_interval.total_seconds(),
        "last_update_success": coordinator.last_update_success,
        "available_endpoints": sorted(coordinator.data or {}),
        "endpoint_errors": dict(coordinator.errors),
        "skipped_modules": dict(coordinator.skipped_modules),
        "skipped_endpoints": dict(coordinator.skipped_endpoints),
    }
