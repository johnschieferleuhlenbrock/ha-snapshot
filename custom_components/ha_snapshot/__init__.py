# custom_components/ha_snapshot/__init__.py

import logging
import json
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.area_registry import async_get as async_get_area_registry

from .const import (
    DOMAIN,
    SERVICE_EXPORT_DATA,
    SERVICE_IMPORT_DATA
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up if someone tries to configure via YAML, but we rely on the UI flow."""
    _LOGGER.debug("async_setup: no YAML-based config is supported.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from the UI config flow."""
    _LOGGER.info("HA Snapshot: Setting up config entry %s", entry.entry_id)

    # Pull the user's chosen options
    skip_nameless_devices = entry.data.get("skip_nameless_devices", True)
    include_disabled_entities = entry.data.get("include_disabled_entities", False)

    # Store in hass.data so we can access in services
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "skip_nameless_devices": skip_nameless_devices,
        "include_disabled_entities": include_disabled_entities
    }

    # Register the services if not already present
    if not hass.services.has_service(DOMAIN, SERVICE_EXPORT_DATA):
        hass.services.async_register(DOMAIN, SERVICE_EXPORT_DATA, handle_export_data)
        _LOGGER.info("Registered service %s.%s", DOMAIN, SERVICE_EXPORT_DATA)

    if not hass.services.has_service(DOMAIN, SERVICE_IMPORT_DATA):
        hass.services.async_register(DOMAIN, SERVICE_IMPORT_DATA, handle_import_data)
        _LOGGER.info("Registered service %s.%s", DOMAIN, SERVICE_IMPORT_DATA)

    # Serve our panel .js from a static path
    panel_dir = os.path.join(os.path.dirname(__file__), "panel")
    hass.http.register_static_path(f"/{DOMAIN}/panel", panel_dir, cache_headers=False)

    # Register a custom panel that will get access to `this.hass` (no manual token needed).
    # The user sees "HA Snapshot" in the sidebar and a route at /ha_snapshot
    # We use "embed_iframe=False" so the code runs directly in HA's frontend context, letting us call `this.hass.callService`.
    hass.components.frontend.async_register_panel(
        component_name="custom",
        sidebar_title="HA Snapshot",
        sidebar_icon="mdi:folder-download",
        frontend_url_path=DOMAIN,
        config={
            "name": "ha-snapshot-panel",           # <ha-snapshot-panel> custom element
            "embed_iframe": False,
            "trust_external": False,
            "js_url": f"/{DOMAIN}/panel/ha_snapshot_panel.js"  # served via register_static_path
        },
        require_admin=False
    )

    _LOGGER.info("HA Snapshot: Panel registered at /%s", DOMAIN)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration and remove panel."""
    _LOGGER.info("HA Snapshot: Unloading entry %s", entry.entry_id)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    hass.components.frontend.async_remove_panel(DOMAIN)
    return True

async def handle_export_data(call: ServiceCall) -> None:
    """Service: ha_snapshot.export_data. Exports data in the hierarchical floors->areas->devices->entities structure."""
    hass = call.hass

    _LOGGER.debug("HA Snapshot: export_data called, data=%s", call.data)
    notify_user = call.data.get("notify", False)
    custom_filename = call.data.get("filename", "ha_snapshot_data.json")

    # Find any config entry to get user-chosen options
    entry_id = next(iter(hass.data[DOMAIN]), None)
    user_opts = hass.data[DOMAIN].get(entry_id, {})
    skip_nameless = user_opts.get("skip_nameless_devices", True)
    include_disabled = user_opts.get("include_disabled_entities", False)

    try:
        data = gather_ha_data(hass, skip_nameless, include_disabled)

        www_path = hass.config.path("www")
        if not os.path.exists(www_path):
            os.makedirs(www_path)
            _LOGGER.info("Created /config/www folder for snapshot output.")

        output_file = os.path.join(www_path, custom_filename)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

        download_url = f"/local/{custom_filename}"
        _LOGGER.info("HA Snapshot: Exported to %s (download: %s)", output_file, download_url)

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
                    "message": f"Export failed: {e}",
                    "notification_id": f"{DOMAIN}_export_error"
                }
            )


async def handle_import_data(call: ServiceCall) -> None:
    """
    Service: ha_snapshot.import_data
    call.data["import_json"]: The JSON to import.
    We'll only update:
      - entity "name" if provided
      - entity "labels" if provided
    (No new entities or domain/device changes.)
    """
    hass = call.hass
    _LOGGER.debug("HA Snapshot: import_data called, data=%s", call.data)
    notify_user = call.data.get("notify", False)
    import_json = call.data.get("import_json")

    if not import_json:
        _LOGGER.error("No 'import_json' provided.")
        if notify_user:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "HA Snapshot Import Error",
                    "message": "No import_json provided.",
                    "notification_id": f"{DOMAIN}_import_error"
                }
            )
        return

    try:
        parsed = json.loads(import_json)
    except Exception as e:
        _LOGGER.error("Import JSON parsing failed: %s", e)
        if notify_user:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "HA Snapshot Import Error",
                    "message": f"JSON parsing failed: {e}",
                    "notification_id": f"{DOMAIN}_import_error"
                }
            )
        return

    entity_registry = async_get_entity_registry(hass)

    changes_applied = 0
    changes_skipped = 0

    try:
        floors = parsed.get("floors", [])
        for floor in floors:
            areas = floor.get("areas", [])
            for area in areas:
                devices = area.get("devices", [])
                for device in devices:
                    entities = device.get("entities", [])
                    for e in entities:
                        ent_id = e.get("entity_id")
                        if not ent_id:
                            changes_skipped += 1
                            continue

                        ent_reg_entry = entity_registry.entities.get(ent_id)
                        if not ent_reg_entry:
                            _LOGGER.debug("Skipping unknown entity_id %s", ent_id)
                            changes_skipped += 1
                            continue

                        new_name = e.get("name")
                        new_labels = e.get("labels")  # e.g. ["Lighting","Main"]

                        # We'll only update name if it's different
                        updated_kwargs = {}
                        if new_name and new_name != ent_reg_entry.name:
                            updated_kwargs["name"] = new_name

                        # "labels" are not natively stored in entity registry,
                        # but we can store them in "capabilities" or "entity_description" as custom attributes if you want.
                        # For demonstration, let's store them in "entity_registry_entry.options" or a custom extended attribute
                        # if we want to track them. We'll do an example by updating "entity_registry_entry.options" under "ha_snapshot_labels".

                        if new_labels and isinstance(new_labels, list):
                            # This is one possible approach, storing them in the registry's "options" dict
                            existing_options = dict(ent_reg_entry.options)
                            existing_options.setdefault(DOMAIN, {})
                            existing_options[DOMAIN]["labels"] = new_labels
                            updated_kwargs["options"] = existing_options

                        if updated_kwargs:
                            entity_registry.async_update_entity(ent_id, **updated_kwargs)
                            _LOGGER.debug("Updated %s => %s", ent_id, updated_kwargs)
                            changes_applied += 1
                        else:
                            changes_skipped += 1

    except Exception as ex:
        _LOGGER.exception("Error applying import data: %s", ex)
        if notify_user:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "HA Snapshot Import Error",
                    "message": f"Import encountered an error: {ex}",
                    "notification_id": f"{DOMAIN}_import_error"
                }
            )
        return

    _LOGGER.info("Import completed: %s changes applied, %s skipped.", changes_applied, changes_skipped)
    if notify_user:
        title = "HA Snapshot Import"
        msg = f"Import complete! {changes_applied} changes applied, {changes_skipped} skipped."
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": msg,
                "notification_id": f"{DOMAIN}_import_result"
            }
        )


def gather_ha_data(hass, skip_nameless=True, include_disabled=False) -> dict:
    """Build the floors->areas->devices->entities JSON structure."""
    device_registry = async_get_device_registry(hass)
    entity_registry = async_get_entity_registry(hass)
    area_registry = async_get_area_registry(hass)

    # We'll create a single "Default Floor" for everything, for demonstration
    floor_data = {
        "floor_id": "floor_1",
        "name": "Default Floor",
        "areas": []
    }

    # Build an index of area_id -> { 'area_id':..., 'name':..., 'devices':[...] }
    area_map = {}
    for ar_id, area in area_registry.areas.items():
        area_map[ar_id] = {
            "area_id": ar_id,
            "name": area.name,
            "devices": []
        }

    # Also handle devices not assigned to an area
    area_map["unassigned"] = {
        "area_id": "unassigned",
        "name": "Unassigned",
        "devices": []
    }

    for dev_id, device in device_registry.devices.items():
        # Possibly skip devices with no name or manufacturer
        if skip_nameless and (not device.name or not device.manufacturer):
            continue

        # Which area does it belong to?
        a_id = device.area_id if device.area_id in area_map else "unassigned"
        area_block = area_map[a_id]

        # Gather entities for this device
        try:
            dev_entities = entity_registry.async_entries_for_device(dev_id, include_disabled_entities=include_disabled)
        except AttributeError:
            # older HA fallback
            dev_entities = [
                e for e in entity_registry.entities.values()
                if e.device_id == dev_id
                and (include_disabled or not e.disabled_by)
            ]

        entity_list = []
        for ent in dev_entities:
            entity_list.append({
                "entity_id": ent.entity_id,
                "name": ent.name or "",
                "domain": ent.entity_id.split(".")[0],
                "labels": ent.options.get(DOMAIN, {}).get("labels", []),
                "disabled": bool(ent.disabled_by)
            })

        area_block["devices"].append({
            "device_id": dev_id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "entities": entity_list
        })

    floor_data["areas"] = list(area_map.values())

    # Return final structure
    return {
        "export_metadata": {
            "generated_by": "HA Snapshot",
            "skip_nameless_devices": skip_nameless,
            "include_disabled_entities": include_disabled
        },
        "floors": [floor_data]
    }
