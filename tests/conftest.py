"""Skutečné třídy Home Assistantu bez připojení ke školnímu serveru."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    # Účty v jednotkových testech jsou pouze v paměti, bez skutečného úložiště HA.
    with patch.object(ConfigEntries, "_async_schedule_save"):
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


@pytest.fixture
async def loaded_integration(hass):
    from homeassistant import loader

    root = Path(__file__).resolve().parents[1]
    (Path(hass.config.config_dir) / "custom_components").symlink_to(
        root / "custom_components", target_is_directory=True
    )
    loader.async_setup(hass)
    return await loader.async_get_integration(hass, "bakalari")
