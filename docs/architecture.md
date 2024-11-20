# HydroPi Architecture

## Overview

HydroPi is a system designed to integrate sensors with a Raspberry Pi to monitor mead batches. It collects data such as gravity and temperature and sends it to a Firebase backend for live updates and tracking.

## Components

1. **Raspberry Pi**:
   - Runs Python scripts to collect sensor data.
   - Sends data to the Firebase Function API endpoint.
2. **Sensors**:
   - Smart hydrometers or custom setups for gravity and temperature monitoring.
3. **Firebase Functions**:
   - Handles incoming data and stores it in Firestore.

## Data Flow

1. Sensor data is read by the Raspberry Pi.
2. The Raspberry Pi sends the data to a Firebase Function endpoint via an HTTP POST request.
3. Firebase Function processes the data and stores it in Firestore.

## Future Enhancements

- Add support for additional sensors (e.g., humidity, CO2 levels).
- Implement data visualization for historical trends.
