<h1 align="center">Ultraloq BLE</h1>

<p align="center"><b>Control your Bluetooth capable U-Tec locks locally and natively in Home Assistant.</b>
</p>

---

This is a [forked](https://github.com/maeneak/utecio-ha) Home Assistant custom integration for Ultraloq / U-Tec / Xthings BLE locks.

I really wanted to have local control over my U-Bolt Pro locks, and the original integration wouldn't even start the config process. So I forked it and fixed the biggest bugs, then did extensive testing and iterating with the help of Codex. In addition to extending lock support, battery, door, and sound status are now first-class entities, along with controls for auto-lock and lock mode. This integration should have all of the original features for non U-Bolt Pro locks, *plus* full support for the U-Bolt Pro locks.

## Requirements
- Active (GATT) Bluetooth support in Home Assistant, whether through [your host's built in Bluetooth](https://www.home-assistant.io/integrations/bluetooth/), a [local USB adapter](https://a.co/d/09RioHgV), or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy/).
- Internet connection on initial setup to get lock info from the Xthings API - this will be user controlled in the future.

## Features (1.0.0, in beta)

Entities currently exposed per lock (when supported by your lock):

- `lock.name_of_lock`
- `sensor.battery_level`
- `sensor.autolock_time`
- `binary_sensor.door`
- `binary_sensor.sound`
- `select.lock_mode`
- `button.rescan`
- `button.restart`

Actions:

- `ultraloq_ble.refresh_locks`: refreshes cached lock metadata from the cloud and reloads the integration.
- `ultraloq_ble.get_device_information`: queries all supported information from a selected lock over BLE.
- `ultraloq_ble.set_device_time`: sets a selected lock's clock from Home Assistant's local time or a supplied date and time.
- `ultraloq_ble.set_device_autolock`: configures auto-lock time, door-sensor mode, and enabled state, or sends a manual hex payload.

Important Bluetooth note:
- Passive advertisement-only proxies are not enough for lock control
- Shelly Bluetooth proxy sightings can help discovery, but active GATT connectivity is what actually matters for operating the lock
- If HA decides that the advertisement is not connectable, it will cause status updates and lock controls to fail

## Install
You can install using HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=inventor7777&repository=ultraloq-ble-ha&category=integration)

Or manually:
1. Open your Home Assistant config directory.
1. Create `custom_components` if it does not already exist.
1. Copy the `custom_components/ultraloq_ble/` folder from this repository into your Home Assistant config directory.
1. Restart Home Assistant.

## Notes

### Speed and Reliability
This integration relies on a direct, active BLE connection to the lock. Ultraloq locks are VERY stingy about BLE connections, even with the offical WiFi bridge. This means that updates may occasionally fail, and the update speed will be much lower than a normal Zigbee/WiFi lock. 

### Offline-ish Behavior

This integration is designed so the cloud is used only when needed:
- first setup
- credential reauthentication
- manual lock metadata refresh

Normal operation such as:
- lock
- unlock
- state updates
- reading battery/autolock/mode values
- setting the auto-lock timer

is intended to happen locally over BLE.

I am working on a local only version, but I am still exploring whether it's viable for normal users.

### Entities

Each lock may expose:

- `sensor.battery_level`: reports High, Medium, Low, or Critical.
- `sensor.autolock_time`: reports the current auto-lock delay in seconds.
- `binary_sensor.door`: reports open or closed on models with door-sensor support.
- `binary_sensor.sound`: reports whether lock sounds are enabled on models with mute-mode support.
- `select.lock_mode`: contains only the modes supported by that model.
- `button.rescan`: immediately requests fresh state over BLE.
- `button.restart`: reboots the lock over BLE.

Notes:

- Availability is shared across a lock's entities, except the Rescan and Restart buttons, which remain available so recovery can be attempted.
- Capability-dependent entities are only created when the model mapping reports support.

### Known Limitations

- Bluetooth quality matters a lot. Weak or non-connectable advertisements will cause timeouts or unavailable entities. You will need active-capable Bluetooth nodes very close to each lock.
- Some lock models may still need extra command or capability tuning.
- Structured auto-lock settings are currently mapped for U-Bolt Pro locks. Other models can use the action's Manual hex field until their payload format is confirmed.
- State updates after a lock or unlock are very slow and dependent on refresh interval. Perhaps there is a way to subscribe to Ultraloq BLE pushes, but I do not have the tools to reverse engineer such a thing.
- Shelly Bluetooth proxies are incapable of starting an active GATT BLE connection, so you will need either a USB Bluetooth adapter or an ESPHome device with `active: true` enabled in the Bluetooth configuration.
- There is a Bleak depreciation warning in the debug logs. I am aware of this but I'd like to get the rest of the implementation stable before attacking that.
- Some locks randomly go offline due to them not responding to `ADMIN_LOGIN`. I am working on a fix, but it only happens occasionally.

### Lock shows up but will not operate

Check:
- the lock is in Bluetooth range
- your Home Assistant Bluetooth adapter or ESPHome proxy can make active connections
- the lock is not only being seen as `connectable: false`
- Unsupported device, in which case you could try reporting an issue here

*Full disclaimer: Most of the improvements from the original were by GPT 5.6 Sol and GPT 5.4 Codex. However, I personally use this integration and I am happy with it, so I am sharing it in case it could be useful to anyone else.*
