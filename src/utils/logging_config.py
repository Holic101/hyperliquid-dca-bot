"""Centralized logging configuration."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(app_name: str = "dca_bot", log_level: int = logging.INFO) -> logging.Logger:
    """Set up robust logging configuration."""
    
    # Create logs directory
    log_directory = Path(__file__).parent.parent.parent / "logs"
    log_directory.mkdir(exist_ok=True)
    
    # Create log file path
    log_file_path = log_directory / f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create and configure stream handler (console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # Create and configure file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)