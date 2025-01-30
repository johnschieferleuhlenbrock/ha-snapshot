# custom_components/ha_snapshot/config_flow.py

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
    """Config flow for HA Snapshot."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the config flow."""
        if user_input is not None:
            # Use the domain as a unique_id so only one instance is allowed
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # Create the entry
            return self.async_create_entry(
                title="HA Snapshot",
                data=user_input
            )

        # Show a form with two Booleans
        data_schema = vol.Schema({
            vol.Required("skip_nameless_devices", default=DEFAULT_SKIP_NAMELESS_DEVICES): bool,
            vol.Required("include_disabled_entities", default=DEFAULT_INCLUDE_DISABLED_ENTITIES): bool
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HaSnapshotOptionsFlow(config_entry)


class HaSnapshotOptionsFlow(config_entries.OptionsFlow):
    """Options flow if you want to allow changing those Booleans later."""
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = dict(self.config_entry.data)
        data_schema = vol.Schema({
            vol.Required("skip_nameless_devices", default=current.get("skip_nameless_devices", DEFAULT_SKIP_NAMELESS_DEVICES)): bool,
            vol.Required("include_disabled_entities", default=current.get("include_disabled_entities", DEFAULT_INCLUDE_DISABLED_ENTITIES)): bool
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
