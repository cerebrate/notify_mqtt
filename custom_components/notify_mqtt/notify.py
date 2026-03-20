"""Support for MQTT notification."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.components.mqtt import valid_publish_topic
from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
    NotifyEntity,
    NotifyEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_NAME, CONF_TOPIC, DOMAIN

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy YAML platform (kept for backward compatibility)
# ---------------------------------------------------------------------------

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {vol.Required(CONF_TOPIC): valid_publish_topic}
    )
)


def get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> MqttNotificationService:
    """Return the legacy notification service (YAML-configured instances)."""
    topic = (discovery_info or config)[CONF_TOPIC]
    return MqttNotificationService(hass, topic)


class MqttNotificationService(BaseNotificationService):
    """Legacy notify service — used for YAML-configured instances.

    Supports the full payload: message, title, target, and an arbitrary
    data dict whose keys are merged at the top level of the JSON object
    published to the configured MQTT topic.
    """

    def __init__(self, hass: HomeAssistant, topic: str) -> None:
        """Initialize the service."""
        self.hass = hass
        self.topic = topic

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Publish a notification as a JSON string to the MQTT topic."""
        payload = _build_payload(message, kwargs.get(ATTR_TITLE), kwargs.get(ATTR_TARGET), kwargs.get(ATTR_DATA))
        await mqtt.async_publish(self.hass, self.topic, payload)


# ---------------------------------------------------------------------------
# Modern entity platform (config-entry-configured instances)
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a notify entity from a config entry."""
    entity = MqttNotifyEntity(entry)
    async_add_entities([entity])
    # Register in the shared hass.data registry so __init__.handle_publish
    # can locate this entity by entity_id across all active entries.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entity


class MqttNotifyEntity(NotifyEntity):
    """Notify entity for config-entry-configured instances.

    Integrates with Home Assistant's standard notify.send_message service
    (supports message and title).  For full payload control — including an
    arbitrary data dict merged at the top level — use the custom
    notify_mqtt.publish service instead.
    """

    _attr_supported_features = NotifyEntityFeature.TITLE
    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the entity."""
        config = {**entry.data, **entry.options}
        self._topic: str = config[CONF_TOPIC]
        name = (config.get(CONF_NAME) or "").strip()
        self._attr_name = name if name else self._topic
        # Use entry_id as unique_id so it stays stable if topic/name change.
        self._attr_unique_id = entry.entry_id

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Publish a notification to the configured MQTT topic."""
        payload = _build_payload(message, title)
        await mqtt.async_publish(self.hass, self._topic, payload)

    @property
    def topic(self) -> str:
        """Return the configured MQTT topic."""
        return self._topic


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _build_payload(
    message: str,
    title: str | None = None,
    target: Any = None,
    data: dict[str, Any] | None = None,
) -> str:
    """Serialize notification fields to a JSON string.

    Keys present in *data* are merged at the top level of the returned
    object, matching the behaviour users of the legacy platform relied on.
    """
    dto: dict[str, Any] = {ATTR_MESSAGE: message}
    if title is not None:
        dto[ATTR_TITLE] = title
    if target is not None:
        dto[ATTR_TARGET] = target
    if data:
        dto.update(data)
    return json.dumps(dto)

