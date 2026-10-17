"""Načítání účtu se samostatnou dostupností jednotlivých modulů."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthenticationError, BakalariClient, BakalariError, EndpointError
from .const import CONF_MODULES, DEFAULT_INTERVAL, DOMAIN, MODULES
from .endpoints import READS, validate_result

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
        self._calendar_lock = asyncio.Lock()
        self._calendar_cache: dict[str, tuple[float, dict]] = {}

    def allowed(self, key: str) -> bool:
        endpoint = READS[key]
        if not endpoint.module:
            return True
        enabled = self.entry.options.get(CONF_MODULES, MODULES)
        if endpoint.module not in enabled:
            return False
        modules = self.profile.get("EnabledModules")
        # Chybí-li seznam modulů o prázdninách, zkusí endpointy a zpracuje HTTP chyby.
        if not isinstance(modules, list):
            return True
        module = next(
            (
                m
                for m in modules
                if str(m.get("Module", "")).casefold() == endpoint.module.casefold()
            ),
            None,
        )
        if module is None:
            return False
        rights = module.get("Rights")
        return (
            endpoint.right is None
            or not isinstance(rights, list)
            or endpoint.right in rights
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            self.profile = await self.client.user()
            result: dict[str, Any] = {"user": self.profile}
            errors = {}
            today = dt_util.now().date()

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
                try:
                    result[key] = validate_result(
                        key,
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

            # Počká na všechny požadavky i při chybě, aby nepokračovaly po aktualizaci.
            outcomes = await asyncio.gather(
                *(fetch(key) for key in POLL_KEYS), return_exceptions=True
            )
            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    raise outcome
            self.errors = errors
            self._calendar_cache.clear()
            return result
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "Aktualizujte přihlašovací údaje Bakalářů"
            ) from err
        except BakalariError as err:
            raise UpdateFailed(str(err)) from err

    async def timetable_range(self, start, end) -> list[dict]:
        """Načte vyžádané týdny, omezí rozsah a krátce uloží výsledky do paměti."""
        import time

        if (end - start).days > 93:
            raise BakalariError("Vyžádejte nejvýše 93 dnů rozvrhu v jednom dotazu")
        from .models import SCHOOL_TZ

        start = start.astimezone(SCHOOL_TZ)
        end = end.astimezone(SCHOOL_TZ)
        day = start.date() - timedelta(days=start.weekday())
        weeks = []
        async with self._calendar_lock:
            while day < end.date() + timedelta(days=1):
                key = day.isoformat()
                cached = self._calendar_cache.get(key)
                if cached is None or cached[0] < time.monotonic() - 300:
                    data = validate_result(
                        "timetable",
                        await self.client.request(
                            "GET", READS["timetable"].path, params={"date": key}
                        ),
                    )
                    self._calendar_cache[key] = (time.monotonic(), data)
                weeks.append(self._calendar_cache[key][1])
                day += timedelta(days=7)
            while len(self._calendar_cache) > 32:
                self._calendar_cache.pop(next(iter(self._calendar_cache)))
        return weeks
