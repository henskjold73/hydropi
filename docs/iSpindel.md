# iSpindel HydroPi Configuration Guide

This guide explains how to configure your iSpindel to send data to a HydroPi endpoint, which posts it to Firebase. We use Firebase and Producery, but you can rewrite the Flask endpoint to post to another service. There are other guides available to help you connect to Brewfather and similar applications at the [iSpindel homepage](https://www.ispindel.de/docs/README_en.html).

---

## Prerequisites

1. **WiFi Network**: A stable WiFi connection.
2. **HydroPi Endpoint**: A HydroPi or other service with an accessible HTTP endpoint.
3. **iSpindel Assembled and Firmware Installed**: Ensure the iSpindel is fully assembled and the firmware is flashed. Refer to the [iSpindel Setup Guide](https://www.ispindel.de/docs/README_en.html) if needed.

---

## Configuration Steps

### Step 1: Connect to the iSpindel

1. Power on your iSpindel by inserting a charged 18650 battery.
2. The iSpindel will start in configuration mode (if it cannot connect to WiFi).
3. Connect to the `iSpindel` WiFi network using your phone or PC.

### Step 2: Access the Configuration Page

1. Open a browser and navigate to `http://192.168.4.1`.
2. The iSpindel configuration page will appear.

### Step 3: Set WiFi Credentials

1. Enter the **SSID** and **Password** for your WiFi network.
2. Save and restart the iSpindel. It will reconnect to your WiFi.

### Step 4: Configure HTTP Endpoint

1. After saving the WiFi configuration, return to the iSpindel configuration page (`http://192.168.4.1`).

2. Select **"Configuration"** from the menu.

3. Under the **Service Type** dropdown, select `HTTP`.

4. Fill in the following fields:

   - **Name**: The name of the iSpindel (e.g., `horrible-ispindel-white01`).
   - **Interval**: How often it posts readings (e.g., `10` for testing and `7200` for production).
   - **Server Address**: The base URL of your HTTP endpoint (e.g., `hydropi.local` or IP address).
   - **Port**: Specify the port for your HTTP server (e.g., `5000` for HydroPi, `80` for HTTP, or `443` for HTTPS).
   - **Path**: The specific endpoint path to send data to (e.g., `/<tenant>/<api-key>`).

   Example:
   ```
   Server Address: horrible-hydropi.local
   Port: 50
   Path: /Fij2KIOf9p1CMNq56zJF/91ef0305-9532-4620-9b17-04e7d81247fb
   ```

5. Save the configuration.

### Step 5: Test the Connection

1. Reboot the iSpindel to apply the changes.
2. Observe the LED on the iSpindel. A successful connection will be indicated by a series of blinks.
3. Verify that data is being sent to your HTTP server by checking your server logs or API endpoint.

---

## Example HTTP Payload

The iSpindel sends data in JSON format. Below is an example payload:

```json
{
"name": "horrible-ispindel-white01",
"ID": 1234567,
"angle": 87.65,
"temperature": 20.45,
"battery": 3.87,
"gravity": 1.042,
"interval": 10
}
```
### Field Descriptions:

- `name`: The name of your iSpindel.
- `ID`: A unique identifier for the device.
- `angle`: The tilt angle in degrees.
- `temperature`: Measured temperature (in Celsius).
- `battery`: Battery voltage.
- `gravity`: Calculated specific gravity. (Calculated from the formula in configuration)
- `interval`: Reporting interval in seconds.

---

## Common Issues

### iSpindel Not Sending Data
- Ensure the HTTP server is accessible from your network.
- Double-check the server address, port, and path in the configuration.
- Verify the WiFi connection and signal strength.

### Data Not Showing on Server
- Ensure the server is configured to accept POST requests at the specified path.
- Check server logs for incoming requests or errors.

---

**Now your iSpindel is set up to send data to a HydroPi. Horrible brewing!**