import asyncio
from collections import defaultdict, deque
from types import SimpleNamespace

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

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


@pytest.fixture
async def school():
    """Lokální HTTP server ověří skutečný transport bez přístupu ke škole."""
    responses = defaultdict(deque)
    calls = []

    def add(
        method,
        path,
        *,
        payload=None,
        body=None,
        status=200,
        repeat=False,
        content_type="application/json",
        headers=None,
    ):
        responses[method, path].append(
            {
                "payload": payload,
                "body": body,
                "status": status,
                "repeat": repeat,
                "content_type": content_type,
                "headers": headers,
            }
        )

    async def handle(request):
        calls.append(
            {
                "method": request.method,
                "path": request.raw_path,
                "headers": dict(request.headers),
                "data": dict(await request.post()),
            }
        )
        key = request.method, request.raw_path.removeprefix("/baka")
        if not responses[key]:
            return web.Response(status=599, text="Neočekávaný požadavek v testu")
        result = responses[key][0]
        if not result["repeat"]:
            responses[key].popleft()
        if result["payload"] is not None:
            return web.json_response(
                result["payload"], status=result["status"], headers=result["headers"]
            )
        return web.Response(
            body=result["body"],
            status=result["status"],
            content_type=result["content_type"],
            headers=result["headers"],
        )

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handle)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        url = str(server.make_url("/baka"))
        yield SimpleNamespace(
            add=add, calls=calls, client=BakalariClient(session, url, "test", "secret")
        )


async def test_concurrent_login_and_headers(school):
    school.add("POST", "/api/login", payload=TOKEN)
    school.add("GET", "/api/3/user", payload={"UserUID": "uid"}, repeat=True)
    await asyncio.gather(*(school.client.user() for _ in range(6)))
    posts = [call for call in school.calls if call["method"] == "POST"]
    assert len(posts) == 1
    assert posts[0]["data"]["grant_type"] == "password"
    assert posts[0]["data"]["client_id"] == "ANDR"
    assert all(
        call["headers"]["Authorization"] == "Bearer token-one"
        for call in school.calls
        if call["method"] == "GET"
    )


async def test_refresh_and_rotated_token(school):
    school.add("POST", "/api/login", payload=TOKEN)
    school.add("GET", "/api/3/user", status=401)
    school.add(
        "POST",
        "/api/login",
        payload={**TOKEN, "access_token": "token-two", "refresh_token": "refresh-two"},
    )
    school.add("GET", "/api/3/user", payload={"UserUID": "uid"})
    assert await school.client.user() == {"UserUID": "uid"}
    assert school.client._refresh == "refresh-two"
    posts = [call for call in school.calls if call["method"] == "POST"]
    assert posts[1]["data"]["refresh_token"] == "refresh-one"
    assert school.calls[-1]["headers"]["Authorization"] == "Bearer token-two"


async def test_invalid_refresh_falls_back_to_password(school):
    school.client._refresh = "expired"
    school.add("POST", "/api/login", status=400)
    school.add("POST", "/api/login", payload=TOKEN)
    await school.client._token()
    assert school.client._access == TOKEN["access_token"]
    assert school.calls[-1]["data"]["grant_type"] == "password"


async def test_invalid_password_is_auth_error(school):
    school.add(
        "POST", "/api/login", status=400, payload={"error_description": "sensitive"}
    )
    with pytest.raises(AuthenticationError) as error:
        await school.client.user()
    assert "sensitive" not in str(error.value)


@pytest.mark.parametrize("status", [403, 404, 429, 500, 302])
async def test_http_errors_not_retried(school, status):
    school.add("POST", "/api/login", payload=TOKEN)
    school.add("GET", "/api/3/user", status=status, headers={"Location": "/redirected"})
    with pytest.raises(EndpointError) as error:
        await school.client.user()
    assert error.value.status == status
    assert len(school.calls) == 2
    assert all(call["path"] != "/redirected" for call in school.calls)


async def test_empty_put_response_and_encoded_id(school):
    school.add("POST", "/api/login", payload=TOKEN)
    path = f"/api/3/homeworks/{path_id('A[B /')}/student-done/true"
    school.add("PUT", path, status=204)
    assert await school.client.request("PUT", path) is None
    assert school.calls[-1]["path"] == "/baka" + path


async def test_malformed_json(school):
    school.add("POST", "/api/login", payload=TOKEN)
    school.add("GET", "/api/3/user", body=b"<html>login</html>")
    with pytest.raises(BakalariError, match="neplatný JSON"):
        await school.client.user()


async def test_second_401_is_auth_failure(school):
    school.add("POST", "/api/login", payload=TOKEN, repeat=True)
    school.add("GET", "/api/3/user", status=401, repeat=True)
    with pytest.raises(AuthenticationError):
        await school.client.user()
    assert len(school.calls) == 4


async def test_attachment_is_base64(school):
    school.add("POST", "/api/login", payload=TOKEN)
    school.add(
        "GET", "/api/3/komens/attachment/A", body=b"abc", content_type="application/pdf"
    )
    result = await school.client.request(
        "GET", "/api/3/komens/attachment/A", binary=True
    )
    assert result["content_base64"] == "YWJj"
    assert result["content_type"] == "application/pdf"
