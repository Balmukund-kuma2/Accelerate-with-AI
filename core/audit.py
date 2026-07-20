import logging
from datetime import datetime
from core.config import BASE_DIR

# Ensure a logs directory exists
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Set up logging configuration
log_file = LOG_DIR / "pipeline.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # This prints logs to your terminal too!
    ]
)

def log_action(agent_name: str, action: str, details: str = ""):
    """Logs a specific action taken by a pipeline agent with a timestamp."""
    message = f"[{agent_name}] Action: {action} | Details: {details}"
    logging.info(message)

def log_error(agent_name: str, error_message: str):
    """Logs errors encountered during execution."""
    message = f"[{agent_name}] ERROR: {error_message}"
    logging.error(message)
