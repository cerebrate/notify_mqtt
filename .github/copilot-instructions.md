# Copilot Instructions

## Project Overview

This is a Home Assistant custom component that bridges HA's notification system to MQTT. When a notification is sent via this platform, it serializes the payload to JSON and publishes it to a configured MQTT topic — enabling consumption by Node-RED or any MQTT-aware system.

Distributed via [HACS](https://hacs.xyz/). Minimum supported Home Assistant version: 2023.4.0.

## Architecture

Two parallel setup paths exist in the same codebase:

```
── UI / Config Flow path ──────────────────────────────────────────────
ConfigFlow (config_flow.py)
    → stores topic in ConfigEntry
    → async_setup_entry (__init__.py)
        → forwards to notify platform → MqttNotifyEntity (notify.py)
            → notify.send_message  (message + title only)
        → registers notify_mqtt.publish service (__init__.py)
            → _build_payload(message, title, data) → mqtt.async_publish

── YAML / Legacy path ─────────────────────────────────────────────────
configuration.yaml: notify: platform: notify_mqtt
    → get_service (notify.py)
        → MqttNotificationService (notify.py)
            → notify.NAME  (message + title + target + data dict)
                → _build_payload → mqtt.async_publish
```

`_build_payload()` in `notify.py` is the single shared serialization helper used by all paths.

## Key Files

| File | Purpose |
|---|---|
| `custom_components/notify_mqtt/notify.py` | Both platforms: `MqttNotifyEntity` (config entry), `MqttNotificationService` (YAML legacy), `_build_payload` helper |
| `custom_components/notify_mqtt/__init__.py` | `async_setup_entry` / `async_unload_entry`; registers `notify_mqtt.publish` custom service |
| `custom_components/notify_mqtt/config_flow.py` | Single-step config flow: prompts for MQTT topic, validates with `valid_publish_topic` |
| `custom_components/notify_mqtt/const.py` | `DOMAIN`, `CONF_TOPIC` constants |
| `custom_components/notify_mqtt/manifest.json` | Integration metadata: `config_flow: true`, `iot_class: local_push`, `integration_type: service` |
| `custom_components/notify_mqtt/services.yaml` | Defines `notify_mqtt.publish` custom service with `entity_id`, `message`, `title`, `data` fields |
| `custom_components/notify_mqtt/strings.json` | Config flow UI strings (source of truth) |
| `custom_components/notify_mqtt/translations/en.json` | English translations (mirrors strings.json) |
| `hacs.json` | HACS store metadata |

## Home Assistant Integration Conventions

### Config-entry path (new)
- `MqttNotifyEntity` inherits from `NotifyEntity`; implements `async_send_message(message, title=None)`.
- `_attr_supported_features = NotifyEntityFeature.TITLE` signals title support to HA.
- The entity instance is stored in `hass.data[DOMAIN]` keyed by `entry.entry_id` so the custom service handler in `__init__.py` can retrieve it.
- MQTT is published via `await mqtt.async_publish(hass, topic, payload)`.

### YAML-legacy path (kept for backward compat)
- `MqttNotificationService` inherits from `BaseNotificationService`; implements `async_send_message(message, **kwargs)`.
- `PLATFORM_SCHEMA` extends HA's base with `vol.Required(CONF_TOPIC): valid_publish_topic`.
- `get_service(hass, config, discovery_info=None)` is the factory HA calls.
- Supports full payload: `message`, `title`, `target`, and `data` dict (merged top-level).

### Custom service + multi-entry
- `notify_mqtt.publish` is registered on the **first** `async_setup_entry` call and removed only when the **last** entry is unloaded (`hass.data[DOMAIN]` is empty).
- All active entities are stored in `hass.data[DOMAIN]` keyed by `entry.entry_id`; the service handler resolves the target by matching `entity.entity_id` across all entries.
- This means multiple topics (multiple config entries) all work correctly with one shared service registration.

### Config flow
- `ConfigFlow` subclass in `config_flow.py`; `domain=DOMAIN` passed to class decorator.
- `unique_id` = the MQTT topic string (prevents duplicate entries for the same topic).
- Error key `"invalid_topic"` maps to the string in `strings.json`.
- `NotifyMqttOptionsFlow` handles editing an existing entry (topic + name); registered via `async_get_options_flow`.
- On options save, `_async_options_updated` triggers `async_reload` so the entity immediately reflects the new values.
- The entity reads effective config as `{**entry.data, **entry.options}` so options always override the original data.

## Configuration

### UI (recommended)
Settings → Devices & Services → Add Integration → Notify MQTT → enter topic.

### YAML (legacy)
```yaml
notify:
  - name: NOTIFIER_NAME       # optional, defaults to "notify"
    platform: notify_mqtt
    topic: some/mqtt/topic    # required
```

## JSON Payload Format

All paths produce the same format:
```json
{
  "message": "...",
  "title": "...",        // if provided
  "target": "...",       // YAML path only
  "key": "value"         // any data dict keys, merged top-level
}
```
