"""The Notify MQTT integration."""
from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.components.notify import ATTR_MESSAGE, ATTR_TITLE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import DOMAIN

PLATFORMS = [Platform.NOTIFY]

SERVICE_PUBLISH = "publish"
ATTR_DATA = "data"

SERVICE_PUBLISH_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_DATA): dict,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notify MQTT from a config entry."""
    # hass.data[DOMAIN] maps entry_id → MqttNotifyEntity for all active entries.
    hass.data.setdefault(DOMAIN, {})

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # Register the custom service once; subsequent entries reuse the same handler.
    if not hass.services.has_service(DOMAIN, SERVICE_PUBLISH):

        async def handle_publish(call: ServiceCall) -> None:
            """Handle the notify_mqtt.publish service call."""
            from .notify import _build_payload  # local import avoids circular dep

            entity_id: str = call.data["entity_id"]
            entity = next(
                (e for e in hass.data[DOMAIN].values() if e.entity_id == entity_id),
                None,
            )
            if entity is None:
                raise ServiceValidationError(
                    f"No active notify_mqtt entity with entity_id '{entity_id}'"
                )
            payload = _build_payload(
                call.data[ATTR_MESSAGE],
                call.data.get(ATTR_TITLE),
                data=call.data.get(ATTR_DATA),
            )
            await mqtt.async_publish(hass, entity.topic, payload)

        hass.services.async_register(
            DOMAIN,
            SERVICE_PUBLISH,
            handle_publish,
            schema=SERVICE_PUBLISH_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Remove the shared service only when the last entry is unloaded.
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_PUBLISH)
    return unloaded


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
