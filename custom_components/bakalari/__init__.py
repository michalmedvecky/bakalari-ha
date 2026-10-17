"""Integrace školního systému Bakaláři."""

from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_validation import config_entry_only_config_schema

from .api import BakalariClient
from .const import DOMAIN, PLATFORMS
from .coordinator import BakalariCoordinator
from .services import async_register_services

CONFIG_SCHEMA = config_entry_only_config_schema(DOMAIN)


async def async_setup(hass, config):
    """Zaregistruje akce i bez načteného účtu a ponechá je dostupné při jeho výpadku."""
    async_register_services(hass)
    return True


async def async_setup_entry(hass, entry):
    client = BakalariClient(
        async_get_clientsession(hass),
        entry.data[CONF_URL],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    coordinator = BakalariCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
