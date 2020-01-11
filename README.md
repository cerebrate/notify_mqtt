# MQTT notification service for Home Assistant.

The `notify_mqtt` notification platform allows you to publish notifications from Home Assistant to an MQTT topic. This is primarily intended to help those who have an existing notification infrastructure set up in [Node-RED](https://nodered.org/) or another MQTT-friendly tool, but may find other uses.

To enable the `notify_mqtt` notification platform in your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
notify:
  - name: NOTIFIER_NAME
    platform: notify_mqtt
    topic: MQTT/TOPIC
```

**name:** Setting the optional parameter `name` allows multiple notifiers to be created. The notifier will bind to the service `notify.NOTIFIER_NAME`.
  * required: false
  * default: notify
  * type: string

**topic:** The MQTT topic that will receive the notification.
  * required: true
  * type: string

Notifications will be delivered to the MQTT topic as a string representation of a JSON object containing the message, title, and other data send to the notification service.
