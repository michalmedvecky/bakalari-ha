from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant import loader
from homeassistant.config_entries import ConfigEntryState

from custom_components.bakalari import async_setup_entry, async_unload_entry
from custom_components.bakalari.const import PLATFORMS


async def test_setup_and_unload_lifecycle(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    entry._async_set_state(hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
    with (
        patch("custom_components.bakalari.async_get_clientsession"),
        patch("custom_components.bakalari.BakalariClient") as client,
        patch.object(
            type(hass.config_entries),
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ) as forward,
        patch.object(
            type(hass.config_entries),
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ) as unload,
    ):
        client.return_value.url = "https://school.example"
        client.return_value.user = AsyncMock(
            return_value={"UserUID": "uid", "EnabledModules": []}
        )
        assert await async_setup_entry(hass, entry)
        assert entry.runtime_data.profile["UserUID"] == "uid"
        assert hass.services.has_service("bakalari", "query")
        forward.assert_awaited_once_with(entry, PLATFORMS)
        assert await async_unload_entry(hass, entry)
        unload.assert_awaited_once_with(entry, PLATFORMS)
        assert not hass.services.has_service("bakalari", "query")
        await entry._async_process_on_unload(hass)


async def test_homeassistant_loader_finds_manifest_and_platforms(hass):
    # Ověří skutečnou komponentu na disku pomocí loaderu Home Assistantu.
    root = Path(__file__).resolve().parents[1]
    (Path(hass.config.config_dir) / "custom_components").symlink_to(
        root / "custom_components", target_is_directory=True
    )
    loader.async_setup(hass)
    integration = await loader.async_get_integration(hass, "bakalari")
    assert integration.domain == "bakalari"
    assert integration.manifest["config_flow"] is True
    platforms = await integration.async_get_platforms(
        [str(p) for p in PLATFORMS] + ["config_flow", "diagnostics"]
    )
    assert len(platforms) == len(PLATFORMS) + 2
