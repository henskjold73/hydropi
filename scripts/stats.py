import socket
import time
import httpx
import psutil
import config
import offline_queue


def get_cpu_temp() -> float:
    """Read CPU temperature from the Pi thermal zone."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except OSError:
        return 0.0


def collect() -> dict:
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": round(psutil.virtual_memory().percent, 1),
        "cpu_temp_c": get_cpu_temp(),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "hostname": socket.gethostname(),
        "offline_queue_count": offline_queue.queue_size(),
    }


async def post_stats(client: httpx.AsyncClient) -> None:
    payload = collect()
    endpoint = f"{config.API_URL.replace('tiltLogger', 'piTelemetry')}/{config.TENANT_ID}/{config.API_KEY}"
    try:
        response = await client.post(endpoint, json=payload)
        if response.status_code == 200:
            print(f"Pi stats posted: CPU {payload['cpu_percent']}% mem {payload['memory_percent']}% temp {payload['cpu_temp_c']}°C uptime {payload['uptime_seconds']}s")
        else:
            print(f"Pi stats post failed: {response.status_code} - {response.text}")
    except httpx.RequestError as e:
        print(f"Pi stats request error: {e}")
