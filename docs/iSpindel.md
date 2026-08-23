# iSpindel Configuration Guide

This guide explains how to configure an iSpindel hydrometer to send data directly to Producery.

---

## Prerequisites

- iSpindel assembled with firmware installed. See the [iSpindel setup guide](https://www.ispindel.de/docs/README_en.html) if needed.
- A stable WiFi network.
- A Producery account with a brewery workspace and an API key (found under **Profile → HydroPi API key**).

---

## Configuration steps

### Step 1: Enter configuration mode

1. Power on the iSpindel.
2. If it cannot connect to a known WiFi network it starts in access point mode.
3. Connect your phone or PC to the `iSpindel` WiFi network.
4. Open `http://192.168.4.1` in a browser.

### Step 2: Set WiFi credentials

Enter your WiFi SSID and password and save. The iSpindel will restart and join your network.

### Step 3: Configure the HTTP endpoint

Return to `http://192.168.4.1` and open **Configuration**. Set:

| Field | Value |
|---|---|
| Service type | `HTTP` |
| Server address | `<ispindelLogger endpoint — see Producery Profile>` |
| Port | `443` |
| Path | `/<your-brewery-id>/<your-api-key>` |
| Interval | `900` (15 min recommended for production) |

The full endpoint and path are shown in **Profile → HydroPi API key** in Producery.

### Step 4: Verify

Reboot the iSpindel. After the first successful POST the device appears automatically in the Producery **Devices** page, where it can be assigned to a batch.

---

## Payload format

The iSpindel sends JSON on each interval:

```json
{
  "name": "my-ispindel",
  "ID": 1234567,
  "angle": 45.2,
  "temperature": 20.1,
  "battery": 3.9,
  "gravity": 1.048,
  "RSSI": -62,
  "interval": 900
}
```

All fields except `name`, `gravity`, and `temperature` are optional but stored when present.

---

## Troubleshooting

- **Device not appearing in Producery** — check the server address and path; verify WiFi signal.
- **Gravity not updating** — confirm the interval hasn't been set too long for testing; check the Devices page for the last-seen timestamp.
