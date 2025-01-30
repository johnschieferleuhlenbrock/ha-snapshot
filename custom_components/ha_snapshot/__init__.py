# custom_components/ha_snapshot/__init__.py
"""
HA Snapshot integration entry point.
Defines service registration, panel setup, and main data export/import logic.
"""

import logging
import json
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import async_get as async_device_registry
from homeassistant.helpers.entity_registry import async_get as async_entity_registry
from homeassistant.helpers.area_registry import async_get as async_area_registry

from .const import (
    DOMAIN,
    SERVICE_EXPORT_DATA,
    SERVICE_IMPORT_DATA
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Legacy entrypoint if someone tries to configure it via YAML.
    This integration is meant for UI-based config, so we do nothing special here.
    """
    _LOGGER.debug("async_setup called; no YAML support is used.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Called when the user adds/integrates HA Snapshot via the UI config flow.
    - We store user preferences (skip_nameless, include_disabled).
    - Register services if they aren't already.
    - Register a built-in panel at /ha_snapshot for the UI.
    """
    _LOGGER.info("HA Snapshot: Setting up config entry %s", entry.entry_id)

    skip_nameless = entry.data.get("skip_nameless_devices", True)
    include_disabled = entry.data.get("include_disabled_entities", False)

    # Keep track of each config entry's preferences in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "skip_nameless_devices": skip_nameless,
        "include_disabled_entities": include_disabled
    }

    # Register services if not already present
    if not hass.services.has_service(DOMAIN, SERVICE_EXPORT_DATA):
        hass.services.async_register(DOMAIN, SERVICE_EXPORT_DATA, handle_export_data)
        _LOGGER.info("Registered service %s.%s", DOMAIN, SERVICE_EXPORT_DATA)

    if not hass.services.has_service(DOMAIN, SERVICE_IMPORT_DATA):
        hass.services.async_register(DOMAIN, SERVICE_IMPORT_DATA, handle_import_data)
        _LOGGER.info("Registered service %s.%s", DOMAIN, SERVICE_IMPORT_DATA)

    # Serve the panel's JS from a static path
    panel_dir = os.path.join(os.path.dirname(__file__), "panel")
    hass.http.register_static_path(
        f"/{DOMAIN}/panel",
        panel_dir,
        cache_headers=False
    )

    # Create a custom panel in the sidebar.
    # "embed_iframe=False" so the code can directly access `this.hass.callService`.
    hass.components.frontend.async_register_panel(
        component_name="custom",
        sidebar_title="HA Snapshot",
        sidebar_icon="mdi:folder-download",
        frontend_url_path=DOMAIN,  # => /ha_snapshot
        config={
            "name": "ha-snapshot-panel",   # The custom element <ha-snapshot-panel>
            "embed_iframe": False,
            "trust_external": False,
            "js_url": f"/{DOMAIN}/panel/ha_snapshot_panel.js"
        },
        require_admin=False
    )

    _LOGGER.info("HA Snapshot: Panel registered at /%s", DOMAIN)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Called when the user removes the integration from the UI.
    We remove the custom panel and delete stored config data.
    """
    _LOGGER.info("HA Snapshot: Unloading entry %s", entry.entry_id)
    hass.data[DOMAIN].pop(entry.entry_id, None)

    # Remove the built-in panel
    hass.components.frontend.async_remove_panel(DOMAIN)
    return True

async def handle_export_data(call: ServiceCall) -> None:
    """
    Service: ha_snapshot.export_data
    Args in call.data:
      - notify (bool): Whether to create a persistent notification.
      - filename (str): Output filename in /config/www/.
    This writes a JSON snapshot to /config/www/<filename>.
    """
    hass = call.hass
    _LOGGER.debug("export_data called, data=%s", call.data)

    notify_user = call.data.get("notify", False)
    filename = call.data.get("filename", "ha_snapshot_data.json")

    # If multiple config entries exist, pick the first
    entry_id = next(iter(hass.data[DOMAIN]), None)
    user_opts = hass.data[DOMAIN].get(entry_id, {}) if entry_id else {}
    skip_nameless = user_opts.get("skip_nameless_devices", True)
    include_disabled = user_opts.get("include_disabled_entities", False)

    try:
        data = gather_ha_data(hass, skip_nameless, include_disabled)

        www_path = hass.config.path("www")
        if not os.path.exists(www_path):
            os.makedirs(www_path)
            _LOGGER.info("Created /config/www folder for snapshot output.")

        output_file = os.path.join(www_path, filename)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

        _LOGGER.info("HA Snapshot: Exported to %s", output_file)
        download_url = f"/local/{filename}"

        if notify_user:
            title = "HA Snapshot Created"
            message = f"Your snapshot is ready! [Download here]({download_url})"
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"{DOMAIN}_export"
                }
            )
    except Exception as e:
        _LOGGER.exception("Export failed: %s", e)
        if notify_user:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "HA Snapshot Export Error",
                    "message": f"{e}",
                    "notification_id": f"{DOMAIN}_export_error"
                }
            )

async def handle_import_data(call: ServiceCall) -> None:
    """
    Service: ha_snapshot.import_data
    Expects:
      - import_json (str): The JSON string to parse.
      - notify (bool): Whether to create a persistent notification.
    We only update existing entities' "name" and "labels" from the input.
    """
    hass = call.hass
    _LOGGER.debug("import_data called, data=%s", call.data)

    import_json = call.data.get("import_json")
    notify_user = call.data.get("notify", False)

    if not import_json:
        _LOGGER.error("No 'import_json' provided.")
        if notify_user:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "HA Snapshot Import Error",
                    "message": "No import_json was provided.",
                    "notification_id": f"{DOMAIN}_import_error"
                }
            )
        return

    try:
        parsed = json.loads(import_json)
    except Exception as e:
        _LOGGER.error("Failed to parse import JSON: %s", e)
        if notify_user:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Import Error",
                    "message": f"JSON parse failed: {e}",
                    "notification_id": f"{DOMAIN}_import_error"
                }
            )
        return

    entity_registry = async_entity_registry(hass)

    changes_applied = 0
    changes_skipped = 0

    try:
        floors = parsed.get("floors", [])
        for floor in floors:
            areas = floor.get("areas", [])
            for area in areas:
                devices = area.get("devices", [])
                for dev in devices:
                    entities = dev.get("entities", [])
                    for ent in entities:
                        ent_id = ent.get("entity_id")
                        if not ent_id:
                            changes_skipped += 1
                            continue

                        reg_entry = entity_registry.entities.get(ent_id)
                        if not reg_entry:
                            _LOGGER.debug("Entity %s not found in registry; skipping", ent_id)
                            changes_skipped += 1
                            continue

                        # Potential updates: name, labels
                        new_name = ent.get("name")
                        new_labels = ent.get("labels")

                        updated_args = {}
                        if new_name and new_name != reg_entry.name:
                            updated_args["name"] = new_name

                        if new_labels and isinstance(new_labels, list):
                            # Store them in reg_entry.options[DOMAIN]["labels"]
                            cur_options = dict(reg_entry.options)
                            cur_options.setdefault(DOMAIN, {})
                            cur_options[DOMAIN]["labels"] = new_labels
                            updated_args["options"] = cur_options

                        if updated_args:
                            entity_registry.async_update_entity(ent_id, **updated_args)
                            _LOGGER.debug("Updated %s => %s", ent_id, updated_args)
                            changes_applied += 1
                        else:
                            changes_skipped += 1
    except Exception as e:
        _LOGGER.exception("Error applying import data: %s", e)
        if notify_user:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Import Error",
                    "message": f"Exception: {e}",
                    "notification_id": f"{DOMAIN}_import_error"
                }
            )
        return

    _LOGGER.info("Import complete: %s applied, %s skipped.", changes_applied, changes_skipped)

    if notify_user:
        msg = f"Import complete! {changes_applied} changes applied, {changes_skipped} skipped."
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "HA Snapshot Import",
                "message": msg,
                "notification_id": f"{DOMAIN}_import_result"
            }
        )

def gather_ha_data(hass, skip_nameless=True, include_disabled=False) -> dict:
    """
    Returns a floors->areas->devices->entities structure, e.g.:
    {
      "export_metadata": {...},
      "floors": [
        {
          "floor_id": "floor_1",
          "name": "Default Floor",
          "areas": [
            {
              "area_id": "...",
              "name": "...",
              "devices": [
                {
                  "device_id": "...",
                  "name": "...",
                  "manufacturer": "...",
                  "model": "...",
                  "entities": [
                    {
                      "entity_id": "...",
                      "name": "...",
                      "domain": "...",
                      "labels": [...],
                      "disabled": false
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
    """
    device_registry = async_device_registry(hass)
    entity_registry = async_entity_registry(hass)
    area_registry = async_area_registry(hass)

    # We'll create one "Default Floor" to hold all areas.
    floor_data = {
        "floor_id": "floor_1",
        "name": "Default Floor",
        "areas": []
    }

    area_map = {}

    # Initialize map of area_id -> dict
    for ar_id, area in area_registry.areas.items():
        area_map[ar_id] = {
            "area_id": ar_id,
            "name": area.name,
            "devices": []
        }
    # Unassigned area for devices that have no area_id
    area_map["unassigned"] = {
        "area_id": "unassigned",
        "name": "Unassigned",
        "devices": []
    }

    # Process devices
    for dev_id, device in device_registry.devices.items():
        if skip_nameless and (not device.name or not device.manufacturer):
            continue

        a_id = device.area_id or "unassigned"
        if a_id not in area_map:
            a_id = "unassigned"
        area_block = area_map[a_id]

        # Gather entities for this device
        try:
            dev_entities = entity_registry.async_entries_for_device(
                dev_id,
                include_disabled_entities=include_disabled
            )
        except AttributeError:
            # Fallback for older HA
            dev_entities = [
                e for e in entity_registry.entities.values()
                if e.device_id == dev_id
                and (include_disabled or not e.disabled_by)
            ]

        ent_list = []
        for e in dev_entities:
            ent_list.append({
                "entity_id": e.entity_id,
                "name": e.name or "",
                "domain": e.entity_id.split(".")[0],
                # If "labels" exist in the entity options, retrieve them
                "labels": e.options.get(DOMAIN, {}).get("labels", []),
                "disabled": bool(e.disabled_by)
            })

        area_block["devices"].append({
            "device_id": dev_id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "entities": ent_list
        })

    floor_data["areas"] = list(area_map.values())

    return {
        "export_metadata": {
            "generated_by": "HA Snapshot",
            "skip_nameless_devices": skip_nameless,
            "include_disabled_entities": include_disabled
        },
        "floors": [floor_data]
    }
