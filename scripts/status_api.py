from flask import Flask, jsonify
from flask_cors import CORS  # Import CORS
import psutil
import subprocess

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def get_service_status(services):
    statuses = []
    for service in services:
        try:
            # Run systemctl to check the service status
            result = subprocess.run(
                ["systemctl", "is-active", service],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Add the service status
            statuses.append({"name": service, "status": result.stdout.strip()})
        except Exception as e:
            statuses.append({"name": service, "status": "unknown"})
    return statuses

@app.route("/status", methods=["GET"])
def status():
    # Example services to monitor
    services = ["tilt-scanner", "status-api", "hydropi-next", "cloudflared","ssh"]

    # Fetch system metrics
    memory = psutil.virtual_memory()
    temperature = psutil.sensors_temperatures().get("cpu_thermal", [])[0].current
    uptime = subprocess.run(
        ["uptime", "-p"], stdout=subprocess.PIPE, text=True
    ).stdout.strip()

    # Fetch service statuses
    service_statuses = get_service_status(services)

    # Build the response
    response = {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory": {
            "active": memory.active,
            "available": memory.available,
            "buffers": memory.buffers,
            "cached": memory.cached,
            "free": memory.free,
            "inactive": memory.inactive,
            "percent": memory.percent,
            "shared": memory.shared,
            "slab": memory.slab,
            "total": memory.total,
            "used": memory.used,
        },
        "temperature": temperature,
        "top_processes": [
            {"name": proc.info["name"], "cpu": proc.info["cpu_percent"]}
            for proc in sorted(
                psutil.process_iter(["name", "cpu_percent"]),
                key=lambda p: p.info["cpu_percent"],
                reverse=True,
            )[:5]
        ],
        "uptime": uptime,
        "services": service_statuses,
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
