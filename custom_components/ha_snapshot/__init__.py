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

# Set up a logger for this integration
_LOGGER = logging.getLogger(__name__)

# The domain must match what's in manifest.json
DOMAIN = "ha_snapshot"

# Name of the custom service in services.yaml
SERVICE_EXPORT_DATA = "export_data"

# Optional regex for parsing out a "floor" label if you embed it in the area name
# Example: "2F - Kitchen" => floor="2F", name="Kitchen"
FLOOR_REGEX = r"^(\w+)\s*-\s*(.*)$"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the ha_snapshot integration via YAML.
    
    This function is called if you have 'ha_snapshot:' in configuration.yaml.
    It should register our export_data service so it becomes available.
    """
    # Log that we've reached async_setup and show the config block
    _LOGGER.info("HA Snapshot: async_setup called with config: %s", config)

    # For additional debugging, confirm the domain is present in config
    if DOMAIN not in config:
        _LOGGER.warning("HA Snapshot: '%s' not found in YAML config! Service may not load.", DOMAIN)
    else:
        _LOGGER.debug("HA Snapshot: Found '%s' in YAML config, proceeding with setup.", DOMAIN)

    # Define the actual service call handler
    async def handle_export_data(call: ServiceCall):
        """
        Handle the service call to export system data.

        :param call: The service call object, which may contain 'notify' if desired.
        """
        # Start debug log
        _LOGGER.debug("HA Snapshot (export_data): Service called with data: %s", call.data)

        # Check if "notify: true" was passed
        notify_user = call.data.get("notify", False)

        try:
            # 1. Retrieve device/ entity/ area registries
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
            _LOGGER.debug("Collecting area info (floor parsing regex: %s)...", FLOOR_REGEX)
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

            # Combine all data into a dictionary
            export_data = {
                "devices": devices_info,
                "entities": entities_info,
                "integrations": integrations_info,
                "areas": areas_info,
            }

            # 6. Write JSON File to /config/www/
            _LOGGER.debug("Preparing to write JSON file to /config/www/ folder...")
            www_path = hass.config.path("www")  # Path to /config/www
            if not os.path.exists(www_path):
                _LOGGER.warning("www folder does not exist; creating it at: %s", www_path)
                os.makedirs(www_path)

            output_file = os.path.join(www_path, "ha_snapshot_data.json")
            _LOGGER.debug("Writing snapshot data to %s...", output_file)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)

            # Log success
            _LOGGER.info("HA Snapshot: Exported system data to '%s'", output_file)
            download_url = "/local/ha_snapshot_data.json"
            _LOGGER.info("Download your snapshot file at: %s", download_url)

            # 7. Optional: Show a persistent notification
            if notify_user:
                title = "HA Snapshot Created"
                message = (
                    "Your HA snapshot file is ready. "
                    f"[Click here to download]({download_url})"
                )
                _LOGGER.debug("Creating persistent_notification with title '%s' ...", title)
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

    # Register the service if everything is good
    _LOGGER.debug("Registering service '%s.%s' ...", DOMAIN, SERVICE_EXPORT_DATA)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_DATA, handle_export_data)
    _LOGGER.info("HA Snapshot: Service '%s.%s' registered successfully.", DOMAIN, SERVICE_EXPORT_DATA)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up ha_snapshot from a config entry (UI-based).
    
    Currently, no config flow is defined, so this might not be called.
    But if you later add a config_flow.py, this code can help
    handle that setup.
    """
    _LOGGER.debug("HA Snapshot: async_setup_entry called for config entry: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry.
    
    If you had anything to clean up, you'd do it here.
    """
    _LOGGER.debug("HA Snapshot: async_unload_entry called for config entry: %s", entry.entry_id)
    return True
