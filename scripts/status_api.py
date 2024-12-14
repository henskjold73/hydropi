from flask import Flask, jsonify, request
from flask_cors import CORS  # Import CORS
import psutil
import subprocess
import json
import os
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

RESULTS_FILE = "/home/horrible/hydropi/tilt_results.json"  # Path to the JSON file
LOG_FILE = "/home/horrible/hydropi/request_log.json"  # Path to the request log file

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

def read_tilt_results():
    """
    Read the Tilt results from the JSON file.
    """
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error reading Tilt results: {e}")
            return {"error": "Could not read Tilt results"}
    return {"error": "Tilt results file not found"}

def flatten_request_data(json_data):
    """
    Flatten the request data to include only the most useful information.
    """
    return {
        "name": json_data.get("name"),
        "ID": json_data.get("ID"),
        "angle": json_data.get("angle"),
        "temperature": json_data.get("temperature"),
        "battery": json_data.get("battery"),
        "gravity": json_data.get("gravity"),
        "RSSI": json_data.get("RSSI"),
        "interval": json_data.get("interval")
    }

@app.route("/ispindel/<tenant>/<apikey>", methods=["POST"])
def forward_request(tenant, apikey):
    """
    Forward the flattened request data to the specified external URL and update the log file.
    """    

    try:
         # Clear the log file at the start
        with open(LOG_FILE, "w") as log_file:  # Write mode will clean out the file
            log_file.truncate(0)  # Ensure the file is cleared out
        # Get and flatten the incoming JSON payload
        incoming_json = request.get_json(silent=True)
        if not incoming_json:
            log_data = {"error": "Invalid or missing JSON payload"}
            with open(LOG_FILE, "w") as log_file:
                json.dump(log_data, log_file, indent=4)
            return jsonify(log_data), 400

        # Ensure 'name' is in the JSON body
        name = incoming_json.get("name")
        external_url = f"https://ispindelfunction-ogbfqlrosa-ew.a.run.app/{tenant}/{apikey}/{name}"
        if not name:
            log_data = {"error": "'name' is required in the body"}
            with open(LOG_FILE, "w") as log_file:
                json.dump(log_data, log_file, indent=4)
            return jsonify(log_data), 400

        flattened_data = flatten_request_data(incoming_json)

        # Log the flattened data before forwarding
        log_data = {
            "message": "Flattened data",
            "flattened_data": flattened_data
        }
        with open(LOG_FILE, "a") as log_file:  # Append instead of overwrite
            json.dump(log_data, log_file, indent=4)
            log_file.write("\n")  # Add a newline for better formatting

        # Forward the flattened data to the external URL
        response = requests.post(
            external_url,
            json=flattened_data,
            headers={"Content-Type": "application/json"}
        )

        # Update the log file with response details
        log_data = {
            "message": "Request forwarded successfully",
            "external_status": response.status_code,
            "external_response": response.json() if response.status_code == 200 else "Error in response"
        }
        with open(LOG_FILE, "a") as log_file:
            json.dump(log_data, log_file, indent=4)
            log_file.write("\n")

        # Return the response from the external service
        return jsonify(log_data), response.status_code

    except requests.RequestException as e:
        log_data = {"error": "Failed to forward request", "details": str(e)}
        with open(LOG_FILE, "a") as log_file:
            json.dump(log_data, log_file, indent=4)
            log_file.write("\n")
        return jsonify(log_data), 500


@app.route("/status", methods=["GET"])
def status():
    # Example services to monitor
    services = ["tilt-scanner", "status-api", "hydropi-next", "cloudflared", "ssh"]

    # Fetch system metrics
    memory = psutil.virtual_memory()
    temperature = psutil.sensors_temperatures().get("cpu_thermal", [])[0].current
    uptime = subprocess.run(
        ["uptime", "-p"], stdout=subprocess.PIPE, text=True
    ).stdout.strip()

    # Fetch service statuses
    service_statuses = get_service_status(services)

    # Read the Tilt results
    tilt_results = read_tilt_results()

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
        "tilt_results": tilt_results,  # Add the Tilt results here
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
