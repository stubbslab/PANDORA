import logging
import sys

def initialize_central_logger(log_file: str, level_str: str) -> logging.Logger:
    # Convert the string level (e.g., "DEBUG", "INFO") to a numeric level
    level = logging.getLevelName(level_str.upper())
    
    # Create a root logger for the entire Pandora system
    logger = logging.getLogger("pandora")
    logger.setLevel(level)

    # Create a file handler to write logs to a single file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    # You can choose a format that includes logger name so you know which subsystem logs a message
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Optional: also add a console handler if you want logs on stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger if they are not already present
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
