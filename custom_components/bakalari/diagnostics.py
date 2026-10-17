"""Diagnostika struktury bez přihlašovacích údajů a školních dat."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "integration_version": "1.0.0",
        "poll_interval_seconds": coordinator.update_interval.total_seconds(),
        "last_update_success": coordinator.last_update_success,
        "available_endpoints": sorted(coordinator.data or {}),
        "endpoint_errors": dict(coordinator.errors),
    }
