# app/logger.py
import sys
from loguru import logger

# Remove the default Loguru configuration
logger.remove()

# Add a new configuration that outputs structured JSON to the console

logger.add(
    sys.stdout,
    format="{message}", 
    level="INFO",
    serialize=True,     
    enqueue=True,       
)



custom_logger = logger