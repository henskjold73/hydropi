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
    Flatten incoming iSpindel data, save it to a JSON file named <name>.json,
    compare gravity values, forward it to an external URL if necessary, and log the process.
    """
    try:
        # Parse the incoming JSON payload
        incoming_json = request.get_json(silent=True)
        if not incoming_json:
            log_error("Invalid or missing JSON payload")
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        # Validate and extract the required 'name' field
        name = incoming_json.get("name")
        if not name:
            log_error("'name' is required in the body")
            return jsonify({"error": "'name' is required in the body"}), 400

        # Flatten the incoming JSON data
        flattened_data = flatten_request_data(incoming_json)
        new_gravity = round(flattened_data.get("gravity", 0), 2)

        # Filepath for the <name>.json file
        filename = f"/home/horrible/hydropi/{name}.json"

        # Check the previous gravity value
        previous_gravity = None
        if os.path.exists(filename):
            with open(filename, "r") as file:
                try:
                    previous_data = json.load(file)
                    previous_gravity = round(previous_data.get("gravity", 0), 2)
                except Exception as e:
                    log_error(f"Error reading previous data from {filename}", str(e))

        # Compare new and previous gravity values
        if previous_gravity == new_gravity:
            log_info(f"No significant change in gravity for {name}. Skipping forward.")
            return jsonify({"message": "No change in gravity. Request not forwarded."}), 200

        # Save the flattened data to a JSON file
        with open(filename, "w") as file:
            json.dump(flattened_data, file, indent=4)

        # Log the save action
        log_info(f"Saved request data to {filename}")

        # Construct the external URL
        external_url = f"https://ispindelfunction-ogbfqlrosa-ew.a.run.app/{tenant}/{apikey}/{name}"

        # Forward the request to the external service
        response = requests.post(
            external_url,
            json=flattened_data,
            headers={"Content-Type": "application/json"}
        )

        # Log the response details
        external_response = (
            response.json() if response.status_code == 200 else "Error in response"
        )
        log_info("Request forwarded successfully", {
            "status_code": response.status_code,
            "response": external_response
        })

        return jsonify({"message": "Request forwarded", "status": response.status_code}), response.status_code

    except requests.RequestException as e:
        log_error("Failed to forward request", str(e))
        return jsonify({"error": "Failed to forward request", "details": str(e)}), 500


def log_error(message, details=None):
    """
    Log an error message with optional details.
    """
    log_data = {"error": message}
    if details:
        log_data["details"] = details
    with open(LOG_FILE, "a") as log_file:
        json.dump(log_data, log_file, indent=4)
        log_file.write("\n")


def log_info(message, details=None):
    """
    Log an informational message with optional details.
    """
    log_data = {"message": message}
    if details:
        log_data["details"] = details
    with open(LOG_FILE, "a") as log_file:
        json.dump(log_data, log_file, indent=4)
        log_file.write("\n")


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
