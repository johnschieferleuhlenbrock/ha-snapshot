# custom_components/ha_snapshot/config_flow.py

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN  # We'll define DOMAIN in const.py or just use a string

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        # If you want user input, define fields here. 
        # Example: vol.Required("sidebar_title", default="HA Snapshot"): str
    }
)

class HaSnapshotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Snapshot."""

    VERSION = 1  # Increment if you change the data schema
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # If you want to ensure only one instance, you can check here:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # user_input might hold any fields from the form
            return self.async_create_entry(
                title="HA Snapshot",
                data=user_input  # store in .data
            )

        # Show form to the user
        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define an options flow if needed."""
        return HaSnapshotOptionsFlow(config_entry)

class HaSnapshotOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for advanced settings (optional)."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        # Show an options form if you want advanced user settings
        return self
