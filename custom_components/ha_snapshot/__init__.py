# ======================================
# custom_components/ha_snapshot/__init__.py
# ======================================
import logging
import json
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.area_registry import async_get as async_get_area_registry

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ha_snapshot"
SERVICE_EXPORT_DATA = "export_data"


def gather_home_assistant_data(hass) -> dict:
    """
    Gathers a condensed view of devices, entities, areas, and integrations.
    Skips nameless or manufacturer-less devices to avoid "back of house" items.
    Includes fallback for older HA versions lacking 'async_entries_for_device'.
    """
    device_registry = async_get_device_registry(hass)
    entity_registry = async_get_entity_registry(hass)
    area_registry = async_get_area_registry(hass)

    ha_data = {
        "devices": {},
        "areas": {},
        "integrations": {}
    }

    # 1. Collect AREA info
    for area_id, area in area_registry.areas.items():
        ha_data["areas"][area_id] = {
            "name": area.name,
            "picture": area.picture
        }

    # 2. Collect DEVICES (plus associated ENTITIES)
    for device_id, device in device_registry.devices.items():
        # Skip devices without a name or manufacturer
        if not device.name or not device.manufacturer:
            continue

        # Find a config entry (integration) referencing this device
        integration_entry_id = next(iter(device.config_entries), None)
        if integration_entry_id:
            ha_data["integrations"].setdefault(
                integration_entry_id, {"devices": [], "entities": []}
            )
            ha_data["integrations"][integration_entry_id]["devices"].append(device_id)

        # Try to retrieve entities for this device
        try:
            entities_for_device = entity_registry.async_entries_for_device(
                device_id, include_disabled_entities=False
            )
        except AttributeError:
            # Fallback for older versions
            entities_for_device = [
                e for e in entity_registry.entities.values() if e.device_id == device_id
            ]

        device_entities = []
        for entity in entities_for_device:
            if not entity.name:
                continue

            entity_info = {
                "entity_id": entity.entity_id,
                "name": entity.name,
                "device_class": entity.device_class,
                "unit_of_measurement": entity.unit_of_measurement,
                "icon": entity.icon,
                "platform": entity.platform,
                "area_id": entity.area_id,
            }
            device_entities.append(entity_info)

            # Tie this entity to the integration
            if integration_entry_id:
                ha_data["integrations"][integration_entry_id]["entities"].append(
                    entity.entity_id
                )

        ha_data["devices"][device_id] = {
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
            "hw_version": device.hw_version,
            "area_id": device.area_id,
            "integration": integration_entry_id,
            "entities": device_entities
        }

    return ha_data


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the ha_snapshot integration (YAML-based). 
    If you want a UI-based config flow, you'd add a config_flow.py and use async_setup_entry instead.
    """

    async def handle_export_data(call: ServiceCall) -> None:
        """
        Service: ha_snapshot.export_data
        Exports data to /config/www/ha_snapshot_data.json (accessible at /local/).
        If notify=True, also creates a persistent notification with a download link.
        """
        _LOGGER.debug("ha_snapshot.export_data called with: %s", call.data)
        notify_user = call.data.get("notify", False)

        try:
            data = gather_home_assistant_data(hass)

            # Ensure /config/www exists
            www_path = hass.config.path("www")
            if not os.path.exists(www_path):
                os.makedirs(www_path)

            # Write minified JSON
            output_file = os.path.join(www_path, "ha_snapshot_data.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

            _LOGGER.info("HA Snapshot: Exported data to '%s'", output_file)
            download_url = "/local/ha_snapshot_data.json"  # Typical location in Home Assistant

            # Optionally notify
            if notify_user:
                title = "HA Snapshot Created"
                message = f"Your snapshot is ready! [Click here to download]({download_url})"
                hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": title,
                            "message": message,
                            "notification_id": f"{DOMAIN}_export_data"
                        }
                    )
                )
        except Exception as e:
            _LOGGER.exception("HA Snapshot: Failed to export data: %s", e)
            if notify_user:
                hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "HA Snapshot Error",
                            "message": f"Export failed: {e}",
                            "notification_id": f"{DOMAIN}_export_error"
                        }
                    )
                )

    # Register the custom service
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_DATA, handle_export_data)
    _LOGGER.info("HA Snapshot: Registered service %s.%s", DOMAIN, SERVICE_EXPORT_DATA)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ha_snapshot from a Config Flow (not implemented in this example)."""
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry (if needed in the future)."""
    return True
