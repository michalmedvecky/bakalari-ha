import asyncio
import re

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.bakalari.api import (
    AuthenticationError,
    BakalariClient,
    BakalariError,
    EndpointError,
    normalize_url,
    path_id,
)

BASE = "https://school.example/baka"
TOKEN = {"access_token": "token-one", "refresh_token": "refresh-one", "expires_in": 600}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (BASE + "/login/", BASE),
        ("HTTPS://SCHOOL.EXAMPLE/baka/", BASE),
        ("http://school.example:8080/", "http://school.example:8080"),
    ],
)
def test_normalize_url(value, expected):
    assert normalize_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "school.example",
        "file:///tmp",
        "https://u:p@school.example",
        "https://school.example?token=secret",
        "https://school.example/#secret",
        "https://school.example:broken",
    ],
)
def test_invalid_url(value):
    with pytest.raises(ValueError):
        normalize_url(value)


def test_id_encoding():
    assert path_id("U /A[1]?") == "U%20%2FA%5B1%5D%3F"
    with pytest.raises(ValueError):
        path_id("..")


async def test_concurrent_login_and_headers():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", payload=TOKEN)
            mock.get(BASE + "/api/3/user", payload={"UserUID": "uid"}, repeat=True)
            client = BakalariClient(session, BASE, "test", "secret")
            await asyncio.gather(*(client.user() for _ in range(6)))
            posts = [
                calls
                for (method, _), calls in mock.requests.items()
                if method == "POST"
            ]
            assert len(posts) == 1 and len(posts[0]) == 1
            for (method, _), calls in mock.requests.items():
                if method == "GET":
                    assert all(
                        call.kwargs["headers"]["Authorization"] == "Bearer token-one"
                        for call in calls
                    )
                    assert all(
                        call.kwargs["allow_redirects"] is False for call in calls
                    )


async def test_refresh_and_rotated_token():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", payload=TOKEN)
            mock.get(BASE + "/api/3/user", status=401)
            mock.post(
                BASE + "/api/login",
                payload={
                    **TOKEN,
                    "access_token": "token-two",
                    "refresh_token": "refresh-two",
                },
            )
            mock.get(BASE + "/api/3/user", payload={"UserUID": "uid"})
            client = BakalariClient(session, BASE, "test", "secret")
            assert await client.user() == {"UserUID": "uid"}
            assert client._refresh == "refresh-two"
            posts = next(
                calls
                for (method, _), calls in mock.requests.items()
                if method == "POST"
            )
            assert posts[1].kwargs["data"]["refresh_token"] == "refresh-one"


async def test_invalid_refresh_falls_back_to_password():
    async with aiohttp.ClientSession() as session:
        client = BakalariClient(session, BASE, "test", "secret")
        client._refresh = "expired"
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", status=400)
            mock.post(BASE + "/api/login", payload=TOKEN)
            await client._token()
            assert client._access == TOKEN["access_token"]


async def test_invalid_password_is_auth_error():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(
                BASE + "/api/login",
                status=400,
                payload={"error_description": "sensitive"},
            )
            with pytest.raises(AuthenticationError) as error:
                await BakalariClient(session, BASE, "test", "secret").user()
            assert "sensitive" not in str(error.value)


@pytest.mark.parametrize("status", [403, 404, 429, 500, 302])
async def test_http_errors_not_retried(status):
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", payload=TOKEN)
            mock.get(BASE + "/api/3/user", status=status)
            with pytest.raises(EndpointError) as error:
                await BakalariClient(session, BASE, "test", "secret").user()
            assert error.value.status == status


async def test_empty_put_response_and_encoded_id():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", payload=TOKEN)
            mock.put(
                re.compile(
                    r"https://school.example/baka/api/3/homeworks/.*/student-done/true"
                ),
                status=204,
            )
            client = BakalariClient(session, BASE, "test", "secret")
            assert (
                await client.request(
                    "PUT", f"/api/3/homeworks/{path_id('A[B /')}/student-done/true"
                )
                is None
            )


async def test_malformed_json():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", payload=TOKEN)
            mock.get(BASE + "/api/3/user", body="<html>login</html>")
            with pytest.raises(BakalariError, match="neplatný JSON"):
                await BakalariClient(session, BASE, "test", "secret").user()


async def test_second_401_is_auth_failure():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", payload=TOKEN, repeat=True)
            mock.get(BASE + "/api/3/user", status=401, repeat=True)
            with pytest.raises(AuthenticationError):
                await BakalariClient(session, BASE, "test", "secret").user()


async def test_attachment_is_base64():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mock:
            mock.post(BASE + "/api/login", payload=TOKEN)
            mock.get(
                BASE + "/api/3/komens/attachment/A",
                body=b"abc",
                content_type="application/pdf",
            )
            result = await BakalariClient(session, BASE, "test", "secret").request(
                "GET", "/api/3/komens/attachment/A", binary=True
            )
            assert result["content_base64"] == "YWJj"
