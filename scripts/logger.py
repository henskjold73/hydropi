import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)

# Example usage
if __name__ == "__main__":
    log_info("This is an info message.")
    log_error("This is an error message.")
