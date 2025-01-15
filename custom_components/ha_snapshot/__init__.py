"""
HA Snapshot: A custom integration to export Home Assistant data in a condensed, minified JSON format.
This version handles older Home Assistant versions that lack 'async_entries_for_device' in the EntityRegistry.
"""

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
    Gather a condensed view of devices, entities, areas, and integrations,
    skipping "back of house" items (nameless or manufacturer-less).

    Also includes a fallback approach for older Home Assistant installs
    that lack 'async_entries_for_device' on the EntityRegistry.
    """

    # -- Retrieve the registries --
    device_registry = async_get_device_registry(hass)
    entity_registry = async_get_entity_registry(hass)
    area_registry = async_get_area_registry(hass)

    # Prepare the data structure
    #   {
    #       "devices": {
    #           device_id: {
    #               "name": ...,
    #               "manufacturer": ...,
    #               "model": ...,
    #               "sw_version": ...,
    #               "hw_version": ...,
    #               "area_id": ...,
    #               "integration": ...,
    #               "entities": [...]
    #           },
    #           ...
    #       },
    #       "areas": {
    #           area_id: {
    #               "name": ...,
    #               "picture": ...
    #           },
    #           ...
    #       },
    #       "integrations": {
    #           config_entry_id: {
    #               "devices": [...],
    #               "entities": [...]
    #           },
    #           ...
    #       }
    #   }
    ha_data = {
        "devices": {},
        "areas": {},
        "integrations": {}
    }

    # ----------------------------------------------------------------
    # 1. Collect AREA info
    # ----------------------------------------------------------------
    _LOGGER.debug("Gathering area info from area_registry...")
    for area_id, area in area_registry.areas.items():
        ha_data["areas"][area_id] = {
            "name": area.name,
            "picture": area.picture
        }

    # ----------------------------------------------------------------
    # 2. Collect DEVICES and associated ENTITIES
    # ----------------------------------------------------------------
    _LOGGER.debug("Gathering devices from device_registry...")
    for device_id, device in device_registry.devices.items():
        # Skip devices without a name or manufacturer to exclude "back of house" items
        if not device.name or not device.manufacturer:
            _LOGGER.debug(
                "Skipping device_id=%s because it has no name/manufacturer (name=%r, manufacturer=%r)",
                device_id, device.name, device.manufacturer
            )
            continue

        # Integration (config entry) that references this device
        # This is typically a set, so we take the first entry if any
        integration_entry_id = next(iter(device.config_entries), None)
        if integration_entry_id:
            # Create a placeholder for this integration if not present
            ha_data["integrations"].setdefault(
                integration_entry_id,
                {"devices": [], "entities": []}
            )
            # Associate device_id with that integration
            ha_data["integrations"][integration_entry_id]["devices"].append(device_id)

        # Attempt to retrieve entities for this device
        # Some older HA versions lack 'async_entries_for_device' on the registry.
        try:
            # If this attribute exists, use it
            entities_for_device = entity_registry.async_entries_for_device(
                device_id, include_disabled_entities=False
            )
        except AttributeError:
            # Fall back to a manual iteration
            _LOGGER.warning(
                "EntityRegistry has no 'async_entries_for_device'; "
                "falling back to manual filtering for device_id=%s",
                device_id
            )
            # Filter all known entities in 'entity_registry.entities' by device_id
            # (Older approach)
            entities_for_device = [
                e for e in entity_registry.entities.values()
                if e.device_id == device_id
            ]

        # Build an array of entity info to store in "entities" for this device
        device_entities = []
        for entity in entities_for_device:
            # Skip entities with no user-friendly name
            if not entity.name:
                _LOGGER.debug(
                    "Skipping entity_id=%s because it has no name", entity.entity_id
                )
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

            # Also tie this entity to the integration in ha_data["integrations"]
            if integration_entry_id:
                ha_data["integrations"][integration_entry_id]["entities"].append(
                    entity.entity_id
                )

        # Populate device info into the "devices" block
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

    _LOGGER.debug("Finished gathering Home Assistant data.")
    return ha_data


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the ha_snapshot integration (YAML-based).
    Make sure you have 'ha_snapshot:' in configuration.yaml.
    """

    async def handle_export_data(call: ServiceCall) -> None:
        """
        The main service handler that gathers the data and writes it to /config/www/ha_snapshot_data.json.
        Use the 'notify' field if you want a persistent notification with a download link.
        """
        _LOGGER.debug("ha_snapshot.export_data called with data: %s", call.data)

        # Check if we should display a persistent notification
        notify_user = call.data.get("notify", False)

        try:
            # 1. Gather condensed data
            _LOGGER.debug("Gathering condensed data from registries...")
            data = gather_home_assistant_data(hass)

            # 2. Ensure /config/www directory exists
            _LOGGER.debug("Ensuring /config/www exists for file output...")
            www_path = hass.config.path("www")
            if not os.path.exists(www_path):
                _LOGGER.warning("Directory '/config/www' does not exist; creating now...")
                os.makedirs(www_path)

            # 3. Build output file path
            output_file = os.path.join(www_path, "ha_snapshot_data.json")
            _LOGGER.debug("Will write data to: %s", output_file)

            # 4. Write data in minified JSON form (no extra spaces)
            #    separators=(',',':') => minimal JSON size
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

            _LOGGER.info("HA Snapshot: Data exported successfully to '%s'.", output_file)

            # 5. Provide /local path for download
            download_url = "/local/ha_snapshot_data.json"
            _LOGGER.info("Snapshot download available at: %s", download_url)

            # 6. Optional: persistent notification
            if notify_user:
                title = "HA Snapshot Created"
                message = (
                    "Your HA snapshot file is ready! "
                    f"[Click here to download]({download_url})"
                )
                _LOGGER.debug("Creating persistent_notification with title='%s'", title)
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
            _LOGGER.exception("HA Snapshot: Failed to export data due to an error: %s", e)

            # Optionally notify user if something went wrong
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
    _LOGGER.debug("Registering service '%s.%s' for exporting data...", DOMAIN, SERVICE_EXPORT_DATA)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_DATA, handle_export_data)
    _LOGGER.info("HA Snapshot: Service '%s.%s' registered successfully.", DOMAIN, SERVICE_EXPORT_DATA)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up ha_snapshot from a Config Flow (if created).
    Currently, we do nothing special here because it's a YAML-based integration.
    """
    _LOGGER.debug("HA Snapshot: async_setup_entry called for entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry if needed in the future.
    """
    _LOGGER.debug("HA Snapshot: async_unload_entry called for entry_id=%s", entry.entry_id)
    return True