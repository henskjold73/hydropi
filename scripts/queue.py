"""
Offline queue for Tilt readings.

Readings that fail to POST (network unavailable) are appended to a local
JSON file. On the next scan cycle the queue is flushed as a single bulk
POST to the tiltLogger endpoint, which preserves the original recordedAt
timestamps.
"""
import json
import time
import httpx
import config

QUEUE_FILE = "/home/horrible/hydropi/offline_queue.json"


def _load() -> list:
    try:
        with open(QUEUE_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(items: list) -> None:
    with open(QUEUE_FILE, "w") as f:
        json.dump(items, f)


def enqueue(color: str, avg_gravity: float, avg_temp_c: float) -> None:
    items = _load()
    items.append({
        "color": color,
        "avg_gravity": avg_gravity,
        "avg_temp_c": avg_temp_c,
        "recordedAt": int(time.time() * 1000),
    })
    _save(items)
    print(f"Queued offline reading for {color} ({len(items)} total in queue)")


async def flush(client: httpx.AsyncClient) -> None:
    items = _load()
    if not items:
        return

    endpoint = f"{config.API_URL}/{config.TENANT_ID}/{config.API_KEY}"
    print(f"Flushing {len(items)} queued reading(s) to API...")
    try:
        response = await client.post(endpoint, json=items, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"Queue flushed: {data.get('processed', '?')} processed, {data.get('failed', 0)} failed")
            _save([])  # clear queue on success
        else:
            print(f"Queue flush failed: {response.status_code} - {response.text}")
    except httpx.RequestError as e:
        print(f"Queue flush error (still offline?): {e}")
