"""Asynchronní klient API v3; těla odpovědí a přihlašovací údaje neloguje."""

from __future__ import annotations

import asyncio
import base64
from time import monotonic
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import aiohttp
from yarl import URL


class BakalariError(Exception):
    """Chyba API bez školních dat."""


class AuthenticationError(BakalariError):
    """Přihlašovací údaje vypršely nebo jsou neplatné."""


class EndpointError(BakalariError):
    """Server odmítl požadavek na endpoint."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"Bakaláři HTTP {status}")


def normalize_url(value: str) -> str:
    """Zpracuje základní URL školy včetně instalací v podsložce."""
    parts = urlsplit(value.strip())
    if (
        parts.scheme not in ("https", "http")
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ValueError(
            "Zadejte URL školy bez přihlašovacích údajů, parametrů a fragmentu"
        )
    # Před požadavkem ověří také formát portu.
    _ = parts.port
    path = parts.path.rstrip("/")
    if path.lower().endswith("/login"):
        path = path[:-6]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def path_id(value: str) -> str:
    """Zakóduje identifikátor jako jediný segment cesty."""
    if not value or value in (".", ".."):
        raise ValueError("Neplatný identifikátor")
    return quote(value, safe="")


class BakalariClient:
    """Sdílí HTTP relaci HA, synchronizuje obnovu tokenů a opakuje pouze HTTP 401."""

    def __init__(
        self, session: aiohttp.ClientSession, url: str, username: str, password: str
    ) -> None:
        self.session = session
        self.url = normalize_url(url)
        self.username = username
        self.password = password
        self._access: str | None = None
        self._refresh: str | None = None
        self._expires = 0.0
        self._lock = asyncio.Lock()
        self._requests = asyncio.Semaphore(3)

    async def _http(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict | None = None,
        data: Any = None,
        json: Any = None,
        binary: bool = False,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if method in ("POST", "PUT") and json is None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        # Zachová zakódovaná ID a nenásleduje přesměrování s přihlašovacími údaji.
        target = URL(f"{self.url}{path}", encoded=True)
        try:
            async with (
                self._requests,
                self.session.request(
                    method,
                    target,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    timeout=aiohttp.ClientTimeout(total=30),
                    allow_redirects=False,
                ) as response,
            ):
                if response.status >= 300:
                    raise EndpointError(response.status)
                if binary:
                    chunks = []
                    size = 0
                    async for chunk in response.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > 5 * 1024 * 1024:
                            raise BakalariError("Příloha překračuje limit 5 MiB")
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    return {
                        "content_base64": base64.b64encode(content).decode(),
                        "content_type": response.headers.get(
                            "Content-Type", "application/octet-stream"
                        ),
                    }
                body = await response.read()
                if not body:
                    return None
                try:
                    return await response.json(content_type=None)
                except (ValueError, UnicodeError) as err:
                    raise BakalariError("Server vrátil neplatný JSON") from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise BakalariError("Nelze komunikovat se školním serverem") from err

    async def _token(self, *, force: bool = False, rejected: str | None = None) -> None:
        async with self._lock:
            if (
                self._access
                and monotonic() < self._expires
                and (not force or self._access != rejected)
            ):
                return
            payload = (
                {
                    "client_id": "ANDR",
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh,
                }
                if self._refresh
                else {
                    "client_id": "ANDR",
                    "grant_type": "password",
                    "username": self.username,
                    "password": self.password,
                }
            )
            try:
                result = await self._http("POST", "/api/login", data=payload)
            except EndpointError as err:
                if err.status not in (400, 401):
                    raise
                if not self._refresh:
                    raise AuthenticationError("Neplatné přihlašovací údaje") from err
                self._refresh = None
                try:
                    result = await self._http(
                        "POST",
                        "/api/login",
                        data={
                            "client_id": "ANDR",
                            "grant_type": "password",
                            "username": self.username,
                            "password": self.password,
                        },
                    )
                except EndpointError as login_err:
                    if login_err.status in (400, 401):
                        raise AuthenticationError(
                            "Neplatné přihlašovací údaje"
                        ) from login_err
                    raise
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("access_token"), str)
                or not result["access_token"]
            ):
                raise BakalariError("Neplatná odpověď při přihlášení")
            try:
                expires = float(result.get("expires_in", 600))
            except (TypeError, ValueError) as err:
                raise BakalariError("Neplatná doba platnosti tokenu") from err
            self._access = result["access_token"]
            self._refresh = result.get("refresh_token", self._refresh)
            self._expires = monotonic() + max(1, expires - 30)

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Provede přihlášený požadavek a odmítnutý token obnoví nejvýše jednou."""
        await self._token()
        token = self._access
        try:
            return await self._http(method, path, token=token, **kwargs)
        except EndpointError as err:
            if err.status != 401:
                raise
        await self._token(force=True, rejected=token)
        try:
            return await self._http(method, path, token=self._access, **kwargs)
        except EndpointError as err:
            if err.status == 401:
                raise AuthenticationError("Přístup byl zamítnut") from err
            raise

    async def user(self) -> dict:
        result = await self.request("GET", "/api/3/user")
        if not isinstance(result, dict) or not result.get("UserUID"):
            raise BakalariError("Neplatná odpověď s údaji účtu")
        return result
