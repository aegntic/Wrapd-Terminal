#!/usr/bin/env python3
# WRAPD: Logger utility module

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(log_file, level=logging.INFO):
    """Configure and return a logger instance for the application
    
    Args:
        log_file (str): Path to the log file
        level (int): Logging level (default: logging.INFO)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("wrapd")
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create file handler (rotating log files, max 5MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_exception(logger, exception, context=""):
    """Log an exception with context
    
    Args:
        logger (logging.Logger): Logger instance
        exception (Exception): Exception to log
        context (str): Additional context information
    """
    if context:
        logger.error(f"{context}: {type(exception).__name__}: {exception}")
    else:
        logger.error(f"{type(exception).__name__}: {exception}")
    logger.debug("Exception details:", exc_info=True)

def create_null_logger():
    """Create a null logger that doesn't output anything
    
    Returns:
        logging.Logger: Null logger
    """
    null_logger = logging.getLogger("null_logger")
    null_logger.addHandler(logging.NullHandler())
    return null_logger
