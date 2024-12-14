from bleak import BleakScanner
import struct
from datetime import datetime
import asyncio
import statistics
import httpx  # For sending HTTP requests
import json  # For writing results to a file
import config

# Known Tilt hydrometer IDs
TILT_MANUFACTURER_IDS = {
    "Red": "a495bb10c5b14b44b5121370f02d74de",
    "Green": "a495bb20c5b14b5121370f02d74de",
    "Black": "a495bb30c5b14b5121370f02d74de",
    "Purple": "a495bb40c5b14b5121370f02d74de",
    "Orange": "a495bb50c5b14b5121370f02d74de",
    "Blue": "a495bb60c5b14b5121370f02d74de",
    "Yellow": "a495bb70c5b14b5121370f02d74de",
    "Pink": "a495bb80c5b14b5121370f02d74de",
}

RESULTS_FILE = "/home/horrible/hydropi/tilt_results.json"
LAST_SENT_FILE = "/home/horrible/hydropi/last_sent_time.json"

last_sent_data = None
last_sent_time = None

data_store = {}  # Store gathered data by UUID

def load_last_sent_time():
    """
    Load the last sent time from a file.
    """
    try:
        with open(LAST_SENT_FILE, "r") as file:  # Use LAST_SENT_FILE from this script
            timestamp = json.load(file).get("last_sent_time")
            if timestamp:
                return datetime.fromisoformat(timestamp)
    except FileNotFoundError:
        print("Last sent time file not found. Starting fresh.")
    except (json.JSONDecodeError, ValueError):
        print("Error decoding last sent time file. Starting fresh.")
    return None

def save_last_sent_time(last_sent_time):
    """
    Save the last sent time to a file.
    """
    try:
        with open(LAST_SENT_FILE, "w") as file:  # Use LAST_SENT_FILE from this script
            json.dump({"last_sent_time": last_sent_time.isoformat()}, file, indent=4)
        print(f"Last sent time recorded in {LAST_SENT_FILE}")
    except Exception as e:
        print(f"Error saving last sent time: {e}")

def get_color_from_data(raw_data):
    """
    Identify the color of the Tilt device by matching the first part of the UUID.
    """
    raw_hex = raw_data.hex().lower()
    for color, uuid in TILT_MANUFACTURER_IDS.items():
        unique_identifier = uuid[:8]  # Match the first 8 characters of the UUID
        if unique_identifier in raw_hex:
            return color
    return "Unknown"

def decode_tilt_data(raw_data):
    if len(raw_data) < 23:
        return None
    
    color = get_color_from_data(raw_data)
    if color == "Unknown":
        return None

    temp_raw = raw_data[18:20]
    temp_f = struct.unpack(">H", temp_raw)[0]
    temp_c = (temp_f - 32) * 5.0 / 9.0  # Convert to Celsius

    gravity_raw = raw_data[20:22]
    gravity = struct.unpack(">H", gravity_raw)[0] / 1000.0  # Divide by 1000

    uuid = raw_data[4:20].hex()

    return {
        "uuid": uuid,
        "color": color,
        "gravity": round(gravity, 3),
        "temp_f": temp_f,
        "temp_c": round(temp_c, 1),
    }

def detection_callback(device, advertisement_data):
    global data_store
    manufacturer_data = advertisement_data.manufacturer_data
    for manufacturer_id, data in manufacturer_data.items():
        if manufacturer_id == 76:  # Check for Tilt manufacturer ID
            decoded_data = decode_tilt_data(data)
            if decoded_data:
                uuid = decoded_data['uuid']
                if uuid not in data_store:
                    data_store[uuid] = {
                        "color": decoded_data["color"],
                        "gravity": [],
                        "temp_c": []
                    }
                data_store[uuid]["gravity"].append(decoded_data["gravity"])
                data_store[uuid]["temp_c"].append(decoded_data["temp_c"])


async def scan_tilts():
    global data_store
    print("Scanning for Tilt hydrometers...")
    data_store = {}  # Reset data store before each scan
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(config.SCAN_DURATION)
    await scanner.stop()
    return process_collected_data()

def load_last_sent_data():
    """
    Load the last sent data from the results file if it exists.
    """
    try:
        with open(RESULTS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("Results file not found. Starting fresh.")
        return None
    except json.JSONDecodeError:
        print("Error decoding the results file. Starting fresh.")
        return None

def process_collected_data():
    global data_store
    results = {}
    for uuid, data in data_store.items():
        try:
            gravity_stddev = statistics.stdev(data["gravity"]) if len(data["gravity"]) > 1 else 0
            temp_stddev = statistics.stdev(data["temp_c"]) if len(data["temp_c"]) > 1 else 0

            results[uuid] = {
                "color": data["color"],
                "avg_gravity": round(statistics.mean(data["gravity"]), 3),
                "avg_temp_c": round(statistics.mean(data["temp_c"]), 1),
                "gravity_stddev": gravity_stddev,
                "temp_stddev": temp_stddev
            }
        except statistics.StatisticsError:
            pass  # Handle case where there are insufficient values for stddev
    return results

async def post_results(results):
    """
    Post the processed results to the endpoint, respecting configuration settings.
    """
    global last_sent_data, last_sent_time

    # Load last sent time if not already set
    if last_sent_time is None:
        print("Loading last sent time from file...")
        last_sent_time = load_last_sent_time()

    # Initialize data_changed
    data_changed = False

    # If last_sent_data is None, attempt to load it from the results file
    if last_sent_data is None:
        print("Loading last sent data from file...")
        last_sent_data = load_last_sent_data()

    # Get current time
    current_time = datetime.now()

    # Check if data has changed
    data_changed = results != last_sent_data

    # Check time threshold
    if last_sent_time:
        elapsed_time = (current_time - last_sent_time).total_seconds()
        if not data_changed and elapsed_time < config.TIME_THRESHOLD:
            print("Skipping API request: No data change and time threshold not reached.")
            return
        elif not data_changed:
            print("Time threshold exceeded. Sending unchanged data.")
    else:
        print("First API request. Sending data.")


    print(f"Last Sent Data: {last_sent_data}")
    print(f"Current Results: {results}")
    print(f"Data Changed: {data_changed}")
    if last_sent_time:
        print(f"Time Since Last Send: {elapsed_time} seconds")
    else:
        print("No previous send time recorded.")

    # API request logic
    endpoint = f"{config.API_URL}/{config.TENANT_ID}/{config.API_KEY}"
    print(endpoint)
    async with httpx.AsyncClient() as client:
        try:
            print("Sending data to API:", results)
            response = await client.post(endpoint, json=results)
            # After a successful API request
            if response.status_code == 200:
                print("Data successfully posted to the server.")
                last_sent_time = current_time  # Update the in-memory last sent time
                save_last_sent_time(last_sent_time)  # Persist the last sent time
            else:
                print(f"Failed to post data: {response.status_code} - {response.text}")
        except httpx.RequestError as e:
            print(f"An error occurred while posting data: {e}")



def write_results_to_file(results):
    """
    Overwrite the JSON file with the latest scan results after a successful API post.
    """
    try:
        with open(RESULTS_FILE, "w") as file:
            json.dump(results, file, indent=4)
        print(f"Results written to {RESULTS_FILE}")
    except Exception as e:
        print(f"Error writing results to file: {e}")


async def main():
    while True:
        scan_results = await scan_tilts()
        print("Scan completed. Results:")
        for uuid, result in scan_results.items():
            print(f"UUID: {uuid}, Color: {result['color']}, Avg Gravity: {result['avg_gravity']}, "
                  f"Avg Temp (°C): {result['avg_temp_c']}, "
                  f"Gravity StdDev: {result['gravity_stddev']}, Temp StdDev: {result['temp_stddev']}")

        # Write results to a file
        write_results_to_file(scan_results)

        # Post results to the endpoint
        await post_results(scan_results)

        print(f"Waiting for {config.SCAN_INTERVAL // 60} minutes...")
        await asyncio.sleep(config.SCAN_INTERVAL - config.SCAN_DURATION)


# Run the main loop
asyncio.run(main())
