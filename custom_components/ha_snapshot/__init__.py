"""
HA Snapshot: A custom integration to export Home Assistant data into a minified JSON file.

This version merges the original ha_snapshot logic with the condensed gather_home_assistant_data() approach.
"""

import logging
import json
import os

# Home Assistant imports
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
    Gather a condensed view of devices, entities, areas, and integrations.

    Skips devices with no name/manufacturer,
    and skips entities with no name (often "back of house" objects).
    """
    device_registry = async_get_device_registry(hass)
    entity_registry = async_get_entity_registry(hass)
    area_registry = async_get_area_registry(hass)

    # Data structure:
    #   {
    #       "devices": { <device_id>: {...}, ... },
    #       "areas":   { <area_id>: {...}, ... },
    #       "integrations": {
    #           <config_entry_id>: {
    #               "devices": [],
    #               "entities": []
    #           },
    #           ...
    #       }
    #   }
    ha_data = {
        "devices": {},
        "areas": {},
        "integrations": {}
    }

    # 1. Collect area info
    for area_id, area in area_registry.areas.items():
        ha_data["areas"][area_id] = {
            "name": area.name,
            "picture": area.picture
        }

    # 2. Collect devices and associated entities
    for device_id, device in device_registry.devices.items():
        # Skip unnamed or missing manufacturer
        if not device.name or not device.manufacturer:
            continue

        # Grab first config_entry that references this device
        integration_entry_id = next(iter(device.config_entries), None)
        if integration_entry_id:
            ha_data["integrations"].setdefault(
                integration_entry_id, {"devices": [], "entities": []}
            )
            ha_data["integrations"][integration_entry_id]["devices"].append(device_id)

        # Gather entity info
        entities = []
        for entity in entity_registry.async_entries_for_device(device_id):
            # Skip unnamed entities
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
            entities.append(entity_info)

            # Associate this entity with its integration as well
            if integration_entry_id:
                ha_data["integrations"][integration_entry_id]["entities"].append(entity.entity_id)

        # Populate device info in the dictionary
        ha_data["devices"][device_id] = {
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
            "hw_version": device.hw_version,
            "area_id": device.area_id,
            "integration": integration_entry_id,
            "entities": entities
        }

    return ha_data


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the ha_snapshot integration (YAML-based).
    Requires 'ha_snapshot:' in configuration.yaml to invoke this setup method.
    """

    async def handle_export_data(call: ServiceCall) -> None:
        """
        Handle the service call to export the condensed system data to a JSON file.
        If 'notify' is True, creates a persistent notification with a download link.
        """
        _LOGGER.debug("HA Snapshot (export_data): Called with data: %s", call.data)
        notify_user = call.data.get("notify", False)

        try:
            # 1. Gather data
            _LOGGER.debug("Gathering Home Assistant data in condensed form...")
            data = gather_home_assistant_data(hass)

            # 2. Determine the path for output JSON
            _LOGGER.debug("Ensuring /config/www directory exists...")
            www_path = hass.config.path("www")
            if not os.path.exists(www_path):
                _LOGGER.warning("www folder does not exist; creating it at: %s", www_path)
                os.makedirs(www_path)

            output_file = os.path.join(www_path, "ha_snapshot_data.json")
            _LOGGER.debug("Writing condensed snapshot data to %s", output_file)

            # 3. Write data in minified form to keep file size small
            with open(output_file, "w", encoding="utf-8") as f:
                # separators=(',',':') removes unnecessary spaces
                json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

            _LOGGER.info("HA Snapshot: Exported system data to '%s'", output_file)

            # 4. Provide a local path for download
            download_url = "/local/ha_snapshot_data.json"
            _LOGGER.info("Download your snapshot file at: %s", download_url)

            # 5. Optional: Create a persistent notification with the link
            if notify_user:
                title = "HA Snapshot Created"
                message = (
                    "Your HA snapshot file is ready. "
                    f"[Click here to download]({download_url})"
                )
                _LOGGER.debug("Creating persistent_notification with title '%s'", title)
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
            # Log full traceback
            _LOGGER.exception("HA Snapshot: Failed to export data. Error: %s", e)

            # Optionally notify user of error
            if notify_user:
                hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "HA Snapshot Error",
                            "message": f"Failed to export data: {str(e)}",
                            "notification_id": f"{DOMAIN}_export_error"
                        }
                    )
                )

    # Register the custom service
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_DATA, handle_export_data)
    _LOGGER.info("HA Snapshot: Service '%s.%s' registered.", DOMAIN, SERVICE_EXPORT_DATA)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up ha_snapshot from a config entry (if you add a config_flow later).
    Right now, we do nothing special here.
    """
    _LOGGER.debug("HA Snapshot: async_setup_entry called for config entry: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry if needed.
    """
    _LOGGER.debug("HA Snapshot: async_unload_entry called for config entry: %s", entry.entry_id)
    return True
