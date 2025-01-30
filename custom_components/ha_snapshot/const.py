# custom_components/ha_snapshot/const.py
"""
Constants for HA Snapshot integration.
"""

DOMAIN = "ha_snapshot"
SERVICE_EXPORT_DATA = "export_data"
SERVICE_IMPORT_DATA = "import_data"

DEFAULT_SKIP_NAMELESS_DEVICES = True
DEFAULT_INCLUDE_DISABLED_ENTITIES = False

IMPORT_LIMITATIONS_MESSAGE = (
    "Import can only update existing entities’ names and labels. "
    "We do NOT create or remove entities, reassign devices, or change domains/devices."
)
