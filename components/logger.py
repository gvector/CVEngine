import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
f_handler = logging.FileHandler("syslog_usage_control.log")

# Logger levels in ascending order of severity
if os.getenv("LOGGER_LEVEL") == "DEBUG":
    logger.setLevel(logging.DEBUG)
    c_handler.setLevel(logging.DEBUG)
    f_handler.setLevel(logging.DEBUG)

elif os.getenv("LOGGER_LEVEL") == "INFO":
    logger.setLevel(logging.INFO)
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.INFO)

elif os.getenv("LOGGER_LEVEL") == "WARNING":
    logger.setLevel(logging.WARNING)
    c_handler.setLevel(logging.WARNING)
    f_handler.setLevel(logging.WARNING)

elif os.getenv("LOGGER_LEVEL") == "ERROR":
    logger.setLevel(logging.ERROR)
    c_handler.setLevel(logging.ERROR)
    f_handler.setLevel(logging.ERROR)

elif os.getenv("LOGGER_LEVEL") == "CRITICAL":
    logger.setLevel(logging.CRITICAL)
    c_handler.setLevel(logging.CRITICAL)
    f_handler.setLevel(logging.CRITICAL)

# Create formatters and add it to handlers
c_format = logging.Formatter('%(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)
