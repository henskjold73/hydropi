import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ["API_URL"]
TENANT_ID = os.environ["TENANT_ID"]
API_KEY = os.environ["API_KEY"]

# Timing configurations
SCAN_DURATION = 15  # Scan duration in seconds
SCAN_INTERVAL = 60 * 60  # Interval between scans in seconds

IGNORE_DUPLICATES = True  # Skip sending data if identical to the last sent data
TIME_THRESHOLD = 3600 * 10  # Minimum time (in seconds) between consecutive API requests (10 hours)
