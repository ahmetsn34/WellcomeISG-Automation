"""Logger configuration for file and console output."""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """
    Configure logger with both file and console handlers.
    
    Args:
        log_dir: Directory to store log files
        
    Returns:
        Configured logger instance
    """
    Path(log_dir).mkdir(exist_ok=True)
    
    logger = logging.getLogger("WellcomeAutomation")
    logger.setLevel(logging.DEBUG)
    
    if logger.hasHandlers():
        return logger
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"automation_{timestamp}.log")
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
