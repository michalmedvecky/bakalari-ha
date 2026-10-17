"""Skutečné třídy Home Assistantu bez připojení ke školnímu serveru."""

import sys
from pathlib import Path

import pytest
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    yield instance
    await instance.async_stop(force=True)


@pytest.fixture
def entry():
    return ConfigEntry(
        domain="bakalari",
        title="Test account",
        data={
            "url": "https://school.example/baka",
            "username": "test",
            "password": "secret",
        },
        options={},
        version=1,
        minor_version=1,
        unique_id="account-id",
        source="user",
        discovery_keys={},
        subentries_data=[],
        state=ConfigEntryState.LOADED,
    )
