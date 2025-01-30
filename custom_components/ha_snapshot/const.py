# custom_components/ha_snapshot/const.py

DOMAIN = "ha_snapshot"
SERVICE_EXPORT_DATA = "export_data"
SERVICE_IMPORT_DATA = "import_data"

# Default config flow values (if you want user toggles)
DEFAULT_SKIP_NAMELESS_DEVICES = True
DEFAULT_INCLUDE_DISABLED_ENTITIES = False

# A note to show in the panel about what can/can't be updated
IMPORT_LIMITATIONS_MESSAGE = (
    "Import can only update existing entities' names and labels. "
    "It does NOT create new entities, change domains, reassign devices, or remove anything."
)
