"""Nastavení účtu, možnosti integrace a opětovné přihlášení."""

from __future__ import annotations

from hashlib import sha256

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuthenticationError, BakalariClient, BakalariError, normalize_url
from .const import (
    CONF_EXPOSE_DETAILS,
    CONF_MODULES,
    CONF_READ_ONLY,
    DEFAULT_INTERVAL,
    DOMAIN,
    MODULES,
)


def account_id(url, uid):
    return sha256(f"{url}|{uid}".encode()).hexdigest()


def credentials_schema(defaults):
    return vol.Schema(
        {
            vol.Required(CONF_URL, default=defaults.get(CONF_URL, "")): str,
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


class BakalariConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Samostatný konfigurační záznam pro každý školní účet."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BakalariOptionsFlow()

    async def _configure(self, step, user_input=None):
        errors = {}
        defaults = (
            {}
            if step == "user"
            else self.hass.config_entries.async_get_entry(self.context["entry_id"]).data
        )
        if user_input is not None:
            try:
                data = dict(user_input)
                data[CONF_URL] = normalize_url(data[CONF_URL])
                client = BakalariClient(
                    async_get_clientsession(self.hass),
                    data[CONF_URL],
                    data[CONF_USERNAME],
                    data[CONF_PASSWORD],
                )
                profile = await client.user()
            except ValueError:
                errors["base"] = "invalid_url"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except BakalariError:
                errors["base"] = "cannot_connect"
            else:
                unique_id = account_id(data[CONF_URL], profile["UserUID"])
                if step != "user":
                    entry = self.hass.config_entries.async_get_entry(
                        self.context["entry_id"]
                    )
                    if unique_id != entry.unique_id:
                        return self.async_abort(reason="wrong_account")
                    return self.async_update_reload_and_abort(entry, data_updates=data)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=profile.get("FullName") or data[CONF_USERNAME], data=data
                )
            defaults = user_input
        return self.async_show_form(
            step_id=step, data_schema=credentials_schema(defaults), errors=errors
        )

    async def async_step_user(self, user_input=None):
        return await self._configure("user", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._configure("reauth_confirm", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._configure("reconfigure", user_input)


class BakalariOptionsFlow(config_entries.OptionsFlow):
    """Volba intervalu načítání, modulů a zveřejnění podrobných atributů."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(CONF_SCAN_INTERVAL, DEFAULT_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=300, max=86400)),
                    vol.Required(
                        CONF_MODULES, default=options.get(CONF_MODULES, MODULES)
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=MODULES, multiple=True)
                    ),
                    vol.Required(
                        CONF_EXPOSE_DETAILS,
                        default=options.get(CONF_EXPOSE_DETAILS, False),
                    ): bool,
                    vol.Required(
                        CONF_READ_ONLY,
                        default=options.get(CONF_READ_ONLY, False),
                    ): bool,
                }
            ),
        )
