from bleak import BleakScanner
import struct
from datetime import datetime
import asyncio
import statistics
import httpx  # For sending HTTP requests
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

data_store = {}  # Store gathered data by UUID

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
    Post the processed results to the endpoint.
    """
    endpoint = f"{config.API_URL}/{config.TENANT_ID}/{config.API_KEY}"
    async with httpx.AsyncClient() as client:
        try:
            print(results)
            response = await client.post(endpoint, json=results)
            if response.status_code == 200:
                print("Data successfully posted to the server.")
            else:
                print(f"Failed to post data: {response.status_code} - {response.text}")
        except httpx.RequestError as e:
            print(f"An error occurred while posting data: {e}")

async def main():
    while True:
        scan_results = await scan_tilts()
        print("Scan completed. Results:")
        for uuid, result in scan_results.items():
            print(f"UUID: {uuid}, Color: {result['color']}, Avg Gravity: {result['avg_gravity']}, "
                  f"Avg Temp (°C): {result['avg_temp_c']}, "
                  f"Gravity StdDev: {result['gravity_stddev']}, Temp StdDev: {result['temp_stddev']}")
        
        # Post results to the endpoint
        await post_results(scan_results)

        print(f"Waiting for {config.SCAN_INTERVAL // 60} minutes...")
        await asyncio.sleep(config.SCAN_INTERVAL)

# Run the main loop
asyncio.run(main())
