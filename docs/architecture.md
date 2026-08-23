# HydroPi Architecture

## Overview

HydroPi is a Raspberry Pi service that bridges Tilt hydrometers to Producery via Bluetooth. It runs as a systemd service, scanning for Tilt BLE advertisements on a fixed interval and forwarding readings to the Producery API. Pi health telemetry is posted alongside each scan cycle.

iSpindel hydrometers connect directly to Producery over HTTP — no Pi involvement needed beyond network routing.

## Components

### Raspberry Pi (`scan.py`)
- Scans for Tilt BLE advertisements using `bleak`.
- Forwards gravity and temperature to the `tiltLogger` Cloud Function.
- Falls back to a local offline queue when the network is unavailable; flushes on the next successful cycle.
- Posts Pi health stats (CPU, memory, temperature, uptime, hostname, queue depth) to the `piTelemetry` Cloud Function after each scan.
- Runs as `tilt-scanner.service` under systemd; restarts automatically on failure.
- Logs to `logs/scan.log`, rotated weekly.

### iSpindel (direct)
- iSpindel devices POST their native JSON payload directly to the `ispindelLogger` Cloud Function.
- Auto-registered on first reading; assignable to a batch from the Producery UI.

### Producery Cloud Functions
- `tiltLogger` — validates and stores Tilt gravity/temperature readings per batch.
- `ispindelLogger` — validates and stores iSpindel readings; auto-registers unknown devices.
- `piTelemetry` — overwrites a single `piStats/latest` document so the Devices page always shows the freshest snapshot.
- `assignTiltDevice` / `releaseTiltDevice` — link/unlink a Tilt color to a batch.
- `assignISpindelDevice` / `releaseISpindelDevice` — link/unlink an iSpindel to a batch.

### Firestore
- `breweries/{id}/batches/{id}/readings` — time-series gravity and temperature readings.
- `breweries/{id}/tiltDevices/{color}` — current batch assignment per Tilt color.
- `breweries/{id}/iSpindelDevices/{name}` — registered iSpindels and their batch assignments.
- `breweries/{id}/piStats/latest` — latest Pi health snapshot.

## Data flow

```
Tilt (BLE)
    └─→ scan.py (Pi)
            ├─→ tiltLogger  ─→ Firestore readings
            └─→ piTelemetry ─→ Firestore piStats/latest

iSpindel (WiFi/HTTP)
    └─→ ispindelLogger ─→ Firestore readings
```

## Service management

`tilt-scanner.service` is managed by systemd:

```bash
sudo systemctl status tilt-scanner
sudo systemctl restart tilt-scanner
journalctl -u tilt-scanner -f
```
