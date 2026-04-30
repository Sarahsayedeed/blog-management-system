import sys
from loguru import logger

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # Add new handler with JSON formatting
    logger.add(
        sys.stdout,
        format="{message}",
        serialize=True,
        level="INFO",
        backtrace=True,
        diagnose=True,
    )
