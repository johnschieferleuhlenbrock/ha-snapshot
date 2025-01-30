# custom_components/ha_snapshot/config_flow.py
"""
Config Flow for the HA Snapshot integration.
This flow allows the user to configure whether to skip nameless devices
and whether to include disabled entities in the export.
"""

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    DEFAULT_SKIP_NAMELESS_DEVICES,
    DEFAULT_INCLUDE_DISABLED_ENTITIES
)

_LOGGER = logging.getLogger(__name__)


class HaSnapshotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Snapshot."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial step shown when the user adds the integration."""
        if user_input is not None:
            # Ensure only one instance
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="HA Snapshot",
                data=user_input  # Store these in the config entry
            )

        # Show a form with two bool fields
        data_schema = vol.Schema({
            vol.Required("skip_nameless_devices", default=DEFAULT_SKIP_NAMELESS_DEVICES): bool,
            vol.Required("include_disabled_entities", default=DEFAULT_INCLUDE_DISABLED_ENTITIES): bool
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the Options Flow to let users update the integration settings."""
        return HaSnapshotOptionsFlow(config_entry)


class HaSnapshotOptionsFlow(config_entries.OptionsFlow):
    """
    Options flow for changing preferences after initial install.
    Note: We do NOT set self.config_entry = config_entry to avoid future deprecation warnings.
    """
    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle editing of options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = dict(self._entry.data)
        data_schema = vol.Schema({
            vol.Required("skip_nameless_devices", default=current.get("skip_nameless_devices", DEFAULT_SKIP_NAMELESS_DEVICES)): bool,
            vol.Required("include_disabled_entities", default=current.get("include_disabled_entities", DEFAULT_INCLUDE_DISABLED_ENTITIES)): bool
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
