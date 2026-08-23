# HydroPi

Raspberry Pi bridge that reads Tilt hydrometer data over Bluetooth and forwards it to [Producery](https://producery-prod.web.app). Also accepts iSpindel readings over HTTP and posts Pi health telemetry on every scan cycle.

## What it does

- **Tilt hydrometers** — scans for BLE advertisements every 5 minutes, forwards gravity and temperature to the Producery `tiltLogger` endpoint. Readings that fail (no network) are queued locally and flushed on the next successful cycle.
- **iSpindel hydrometers** — iSpindel devices POST directly to the Producery `ispindelLogger` endpoint (no Pi involvement beyond routing).
- **Pi telemetry** — after each scan, posts CPU %, memory %, CPU temperature, uptime, hostname, and offline queue depth to the `piTelemetry` endpoint so the Producery Devices page shows Pi health.
- **Offline queue** — failed Tilt readings are stored in `offline_queue.json` and sent as a bulk request (with original timestamps) when connectivity is restored.
- **Remote access** — Pi is reachable over Cloudflare Tunnel at `ssh horrible@horribleclaw.hydropi.io`.

## Repository layout

```
hydropi/
├── scripts/
│   ├── scan.py            # Main loop: BLE scan → API post → telemetry
│   ├── config.py          # Loads .env variables (API_URL, TENANT_ID, API_KEY)
│   ├── stats.py           # Collects and posts Pi health stats
│   └── offline_queue.py   # Persist / flush failed Tilt readings
├── setup/
│   ├── setup.sh           # Automated setup script
│   ├── requirements.txt   # Python dependencies
│   ├── services/          # systemd unit files
│   ├── logrotate-hydropi  # Log rotation config for logs/scan.log
│   └── readme.md          # Setup-folder notes
├── logs/
│   └── scan.log           # Live service output (rotated weekly, kept 4 weeks)
└── offline_queue.json     # Runtime only — not in git
```

## Setup

### 1. Clone and run setup

```bash
git clone https://github.com/henskjold73/hydropi.git
cd hydropi
bash setup/setup.sh
```

The script installs system packages, creates a Python venv, installs dependencies, registers and starts `tilt-scanner.service`.

### 2. Configure environment

Create `/home/horrible/hydropi/.env`:

```env
API_URL=https://tiltlogger-p4exxa3jhq-ew.a.run.app
TENANT_ID=<your-brewery-id>
API_KEY=<your-hydropi-api-key>
```

Find your brewery ID and API key under **Profile → HydroPi API key** in Producery.

### 3. Install log rotation

```bash
sudo cp setup/logrotate-hydropi /etc/logrotate.d/hydropi
```

This rotates `logs/scan.log` weekly and keeps 4 compressed weeks.

### 4. iSpindel setup

Point the iSpindel at the Producery endpoint directly — no Pi config needed:

- **Server:** `ispindellogger-p4exxa3jhq-ew.a.run.app`
- **Port:** 443
- **Path:** `/<brewery-id>/<api-key>`

The endpoint is shown in **Profile → HydroPi API key** in Producery.

## Useful commands

```bash
# Watch live logs
journalctl -u tilt-scanner -f

# Or tail the log file
tail -f logs/scan.log

# Restart the scanner
sudo systemctl restart tilt-scanner

# Check service status
sudo systemctl status tilt-scanner
```

## Timing

| Setting | Value |
|---|---|
| BLE scan duration | 15 seconds |
| Scan interval | 5 minutes |
| Offline queue flush | On every scan cycle |
| Log rotation | Weekly, 4 weeks retained |

## License

MIT — see `LICENSE`.
