import requests
from config import API_URL, API_KEY

def send_data(batch_id, gravity, temperature):
    """Send gravity and temperature data to the Firebase API."""
    headers = {"x-api-key": API_KEY}
    payload = {
        "batchId": batch_id,
        "gravity": gravity,
        "temperature": temperature,
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            print("Data sent successfully!")
        else:
            print(f"Error: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Failed to send data: {e}")

# Example usage
if __name__ == "__main__":
    batch_id = "batch123"
    gravity = 1.015
    temperature = 22.5
    send_data(batch_id, gravity, temperature)
