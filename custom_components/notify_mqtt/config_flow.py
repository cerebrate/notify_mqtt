"""Config flow for Notify MQTT."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.mqtt import valid_publish_topic
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_NAME, CONF_TOPIC, DOMAIN


def _topic_name_schema(
    default_topic: str = "", default_name: str = ""
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_TOPIC, default=default_topic): selector.selector({"text": {}}),
            vol.Optional(CONF_NAME, default=default_name): selector.selector({"text": {}}),
        }
    )


def _entry_title(user_input: dict[str, Any]) -> str:
    """Derive a config entry title from user input."""
    name = (user_input.get(CONF_NAME) or "").strip()
    return name if name else user_input[CONF_TOPIC]


def _validate_topic(user_input: dict[str, Any]) -> dict[str, str]:
    """Return an errors dict; empty means valid."""
    try:
        valid_publish_topic(user_input[CONF_TOPIC])
    except vol.Invalid:
        return {CONF_TOPIC: "invalid_topic"}
    return {}


class NotifyMqttConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notify MQTT."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NotifyMqttOptionsFlow:
        """Return the options flow handler."""
        return NotifyMqttOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_topic(user_input)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_TOPIC])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_entry_title(user_input),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_topic_name_schema(),
            errors=errors,
        )


class NotifyMqttOptionsFlow(OptionsFlow):
    """Handle options for an existing Notify MQTT entry."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the config entry for use in the flow step."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options — topic and friendly name."""
        errors: dict[str, str] = {}

        # Read current effective values (options override data).
        current = {**self._entry.data, **self._entry.options}
        current_topic: str = current.get(CONF_TOPIC, "")
        current_name: str = current.get(CONF_NAME, "")

        if user_input is not None:
            errors = _validate_topic(user_input)
            if not errors:
                # Strip empty name so it doesn't shadow the topic fallback.
                cleaned = {CONF_TOPIC: user_input[CONF_TOPIC]}
                name = (user_input.get(CONF_NAME) or "").strip()
                if name:
                    cleaned[CONF_NAME] = name
                return self.async_create_entry(
                    title=name or cleaned[CONF_TOPIC],
                    data=cleaned,
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_topic_name_schema(current_topic, current_name),
            errors=errors,
        )

