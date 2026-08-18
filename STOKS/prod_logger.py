import logging
import os
from config import LOGS_DIR

log_file = os.path.join(LOGS_DIR, "system.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_info(msg):
    logging.info(msg)
    print(f"[INFO] {msg}")

def log_error(msg):
    logging.error(msg)
    print(f"[ERROR] {msg}")
