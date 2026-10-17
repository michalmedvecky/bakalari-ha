"""Načítání účtu se samostatnou dostupností jednotlivých modulů."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthenticationError, BakalariClient, BakalariError, EndpointError
from .const import CONF_MODULES, DEFAULT_INTERVAL, DOMAIN, MODULES
from .endpoints import READS, validate_result
from .models import SCHOOL_TZ

_LOGGER = logging.getLogger(__name__)
POLL_KEYS = (
    "marks",
    "new_marks",
    "final_marks",
    "measures",
    "homeworks",
    "homework_count",
    "absence",
    "received",
    "noticeboard",
    "unread",
    "noticeboard_unread",
    "timetable",
    "events",
    "substitutions",
    "subjects",
    "balance",
    "student_present",
)


class BakalariCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Ponechá funkční moduly dostupné při chybě jiného modulu."""

    def __init__(self, hass, entry: ConfigEntry, client: BakalariClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_INTERVAL)
            ),
        )
        self.client = client
        self.entry = entry
        self.profile: dict[str, Any] = {}
        self.errors: dict[str, str] = {}
        self.skipped_modules: dict[str, str] = {}
        self.skipped_endpoints: dict[str, dict[str, str]] = {}
        self._calendar_lock = asyncio.Lock()
        self._calendar_cache: dict[str, tuple[float, dict]] = {}

    def allowed(self, key: str) -> bool:
        return self.skip_reason(key) is None

    def skip_reason(self, key: str) -> str | None:
        """Rozliší vypnutí uživatelem, chybějící modul a chybějící oprávnění."""
        endpoint = READS[key]
        if not endpoint.module:
            return None
        enabled = self.entry.options.get(CONF_MODULES, MODULES)
        if endpoint.module not in enabled:
            return "disabled_by_options"
        modules = self.profile.get("EnabledModules")
        # Chybí-li seznam modulů o prázdninách, zkusí endpointy a zpracuje HTTP chyby.
        if not isinstance(modules, list):
            return None
        module = next(
            (
                m
                for m in modules
                if str(m.get("Module", "")).casefold() == endpoint.module.casefold()
            ),
            None,
        )
        if module is None:
            return "module_not_available"
        rights = module.get("Rights")
        if endpoint.right and isinstance(rights, list) and endpoint.right not in rights:
            return "missing_right"
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            self.profile = await self.client.user()
            result: dict[str, Any] = {"user": self.profile}
            errors = {}
            today = dt_util.now().astimezone(SCHOOL_TZ).date()
            next_monday = today + timedelta(days=7 - today.weekday())
            self.skipped_endpoints = {
                key: {"module": READS[key].module, "reason": reason}
                for key in POLL_KEYS
                if (reason := self.skip_reason(key)) is not None
            }
            self.skipped_modules = {
                item["module"]: item["reason"]
                for item in self.skipped_endpoints.values()
                if item["reason"] in ("module_not_available", "disabled_by_options")
            }

            async def fetch_one(key, endpoint, params):
                try:
                    result[key] = validate_result(
                        "timetable" if key == "timetable_next" else key,
                        await self.client.request(
                            endpoint.method, endpoint.path, params=params
                        ),
                    )
                except AuthenticationError:
                    raise
                except EndpointError as err:
                    errors[key] = str(err.status)
                except BakalariError:
                    errors[key] = "communication_or_data"

            async def fetch(key):
                if not self.allowed(key):
                    return
                endpoint = READS[key]
                params = None
                if key == "homeworks":
                    params = {
                        "from": (today - timedelta(days=30)).isoformat(),
                        "to": (today + timedelta(days=90)).isoformat(),
                    }
                elif key == "timetable":
                    params = {"date": today.isoformat()}
                elif key == "substitutions":
                    params = {"from": today.isoformat()}
                await fetch_one(key, endpoint, params)
                if key == "timetable" and key in result:
                    await fetch_one(
                        "timetable_next", endpoint, {"date": next_monday.isoformat()}
                    )

            # Počká na všechny požadavky i při chybě, aby nepokračovaly po aktualizaci.
            outcomes = await asyncio.gather(
                *(fetch(key) for key in POLL_KEYS), return_exceptions=True
            )
            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    raise outcome
            self.errors = errors
            self._calendar_cache.clear()
            for key, monday in (
                ("timetable", today - timedelta(days=today.weekday())),
                ("timetable_next", next_monday),
            ):
                if key in result:
                    self._calendar_cache[monday.isoformat()] = (
                        monotonic(),
                        result[key],
                    )
            return result
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "Aktualizujte přihlašovací údaje Bakalářů"
            ) from err
        except BakalariError as err:
            raise UpdateFailed(str(err)) from err

    async def timetable_range(self, start, end) -> list[dict]:
        """Načte vyžádané týdny, omezí rozsah a krátce uloží výsledky do paměti."""
        if (end - start).days > 93:
            raise BakalariError("Vyžádejte nejvýše 93 dnů rozvrhu v jednom dotazu")
        start = start.astimezone(SCHOOL_TZ)
        end = end.astimezone(SCHOOL_TZ)
        day = start.date() - timedelta(days=start.weekday())
        weeks = []
        async with self._calendar_lock:
            while day < end.date() + timedelta(days=1):
                key = day.isoformat()
                cached = self._calendar_cache.get(key)
                if cached is None or cached[0] < monotonic() - 300:
                    data = validate_result(
                        "timetable",
                        await self.client.request(
                            "GET", READS["timetable"].path, params={"date": key}
                        ),
                    )
                    self._calendar_cache[key] = (monotonic(), data)
                weeks.append(self._calendar_cache[key][1])
                day += timedelta(days=7)
            while len(self._calendar_cache) > 32:
                self._calendar_cache.pop(next(iter(self._calendar_cache)))
        return weeks
