"""HA Snapshot: Exports devices, entities, integrations, and areas (with optional floor parsing)."""

import logging
import json
import re
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.area_registry import async_get as async_get_area_registry

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ha_snapshot"
SERVICE_EXPORT_DATA = "export_data"

# Optional regex for parsing out a "floor" label if you embed it in the area name
# e.g., "2F - Kitchen" => floor="2F", name="Kitchen"
FLOOR_REGEX = r"^(\w+)\s*-\s*(.*)$"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the ha_snapshot integration (YAML-based)."""

    async def handle_export_data(call: ServiceCall):
        """Handle the service call to export system data."""
        _LOGGER.debug("HA Snapshot: Starting snapshot export...")

        # Check if the user passed "notify: true" in the service call
        notify_user = call.data.get("notify", False)

        try:
            # 1. Retrieve registries
            _LOGGER.debug("Retrieving device registry...")
            device_registry = async_get_device_registry(hass)

            _LOGGER.debug("Retrieving entity registry...")
            entity_registry = async_get_entity_registry(hass)

            _LOGGER.debug("Retrieving area registry...")
            area_registry = async_get_area_registry(hass)

            # 2. Collect Devices
            _LOGGER.debug("Collecting device info...")
            devices_info = []
            for device_id, device in device_registry.devices.items():
                devices_info.append({
                    "id": device_id,
                    "name": device.name,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "area_id": device.area_id,
                    "config_entries": list(device.config_entries),
                })

            # 3. Collect Entities
            _LOGGER.debug("Collecting entity info...")
            entities_info = []
            for entity_id, entity in entity_registry.entities.items():
                entities_info.append({
                    "entity_id": entity_id,
                    "unique_id": entity.unique_id,
                    "platform": entity.platform,
                    "name": entity.name,
                    "device_id": entity.device_id,
                })

            # 4. Collect Integrations (Config Entries)
            _LOGGER.debug("Collecting integration (config entry) info...")
            integrations_info = []
            for entry in hass.config_entries.async_entries():
                integrations_info.append({
                    "entry_id": entry.entry_id,
                    "domain": entry.domain,
                    "title": entry.title,
                    "source": entry.source,
                    "state": str(entry.state),
                })

            # 5. Collect Areas (with optional floor parsing)
            _LOGGER.debug("Collecting area info with optional floor parsing...")
            areas_info = []
            for area_id, area in area_registry.areas.items():
                match = re.match(FLOOR_REGEX, area.name)
                if match:
                    floor_label = match.group(1)
                    area_name = match.group(2)
                else:
                    floor_label = None
                    area_name = area.name

                areas_info.append({
                    "id": area_id,
                    "name": area_name,
                    "floor": floor_label,
                    "normalized_name": area.normalized_name,
                    "picture": area.picture,
                })

            # Combine all data
            export_data = {
                "devices": devices_info,
                "entities": entities_info,
                "integrations": integrations_info,
                "areas": areas_info,
            }

            # 6. Write JSON File to /config/www/
            www_path = hass.config.path("www")  # make sure this folder exists
            if not os.path.exists(www_path):
                _LOGGER.warning("www folder does not exist; creating it at: %s", www_path)
                os.makedirs(www_path)

            output_file = os.path.join(www_path, "ha_snapshot_data.json")
            _LOGGER.debug("Writing snapshot data to %s...", output_file)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)

            _LOGGER.info("HA Snapshot: Exported system data to '%s'", output_file)
            download_url = "/local/ha_snapshot_data.json"
            _LOGGER.info("Download your snapshot file at: %s", download_url)

            # 7. Optional: Show a persistent notification with the download link
            if notify_user:
                title = "HA Snapshot Created"
                message = (
                    "Your HA snapshot file is ready. "
                    f"[Click here to download]({download_url})"
                )
                # Create a persistent notification so the user sees it in the UI
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
            _LOGGER.exception("HA Snapshot: Failed to export data. Error: %s", e)
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

    # Register the service
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_DATA, handle_export_data)
    _LOGGER.info("HA Snapshot: Service '%s.%s' registered.", DOMAIN, SERVICE_EXPORT_DATA)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up ha_snapshot from a config entry (UI-based)."""
    _LOGGER.debug("HA Snapshot: async_setup_entry called for config entry: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("HA Snapshot: async_unload_entry called for config entry: %s", entry.entry_id)
    return True
