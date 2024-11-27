# HydroPi Architecture

## Overview

HydroPi is a system designed to integrate sensors with a Raspberry Pi to monitor mead batches. It collects data such as gravity and temperature from smart hydrometers and sends it to a Firebase backend for live updates, logging, and batch tracking.

## Components

1. **Raspberry Pi**:
   - Runs Python scripts (e.g., `scan.py`) to collect sensor data.
   - Utilizes a systemd service (`tilt-scanner.service`) for automated scanning and data posting.
   - Sends data to the Firebase Function API endpoint via HTTP POST requests.
   - Logs data locally for debugging and redundancy (`/home/horrible/hydropi/logs`).
2. **Sensors**:
   - Smart hydrometers (e.g., Tilt) measure specific gravity and temperature of the mead batches.
   - Custom sensor setups can be integrated in the future.
3. **Firebase Functions**:
   - Processes incoming data from the Raspberry Pi.
   - Stores data in Firestore for real-time updates and historical tracking.
4. **Local Logging**:
   - Provides error and debug logs to track service operations and data transmission.

## Data Flow

1. Sensor data is scanned and read by the Raspberry Pi using BLE (Bluetooth Low Energy).
2. The data is processed locally and logged for redundancy.
3. The Raspberry Pi sends the processed data to a Firebase Function endpoint via an HTTP POST request.
4. Firebase Function validates the data and stores it in Firestore.
5. Real-time updates are available through Firestore listeners for UI components or alerts.

## Service Management

- The `tilt-scanner.service` systemd service:
  - Automates the scanning and data posting process.
  - Ensures the script (`scan.py`) restarts on failure.
  - Logs output and errors to files located in `/home/horrible/hydropi/logs`.

## Future Enhancements

- **Support for Additional Sensors**:
  - Add monitoring for environmental metrics such as humidity and CO2 levels.
- **Historical Data Visualization**:
  - Develop a dashboard to graph trends over time for gravity, temperature, and other metrics.
- **Alerts and Notifications**:
  - Integrate alerting for thresholds (e.g., abnormal gravity or temperature levels).
- **Edge Processing**:
  - Preprocess data on the Raspberry Pi for faster insights and reduced backend load.
- **Cloud Backup**:
  - Implement automated backups of Firestore data to secure storage.
