# HydroPi

HydroPi is a Raspberry Pi-based system designed for monitoring mead batches. It collects gravity and temperature data using sensors or smart hydrometers and sends the data to a Firebase API for real-time updates.

## Features
- Gravity and temperature monitoring.
- Real-time data updates to a Firebase backend.
- Easy setup with automated installation scripts.
- Modular and extensible for additional sensors or data points.

## Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/henskjold73/hydropi.git
   cd hydropi
   ```

2. Run the setup script:
   ```bash
   bash setup/setup.sh
   ```

3. Edit `scripts/config.py` to include your API URL and API key.

4. Start the script:
   ```bash
   python3 scripts/main.py
   ```

## Contributing
Contributions are welcome! Feel free to fork this repository, make changes, and submit a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.