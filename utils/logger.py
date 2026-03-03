#!/usr/bin/env python3
"""
Logging Configuration for AI Data Center Routing Experiments

Provides centralized logging setup with both file and console handlers.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


# Color codes for console output
class LogColors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': LogColors.CYAN,
        'INFO': LogColors.GREEN,
        'WARNING': LogColors.YELLOW,
        'ERROR': LogColors.RED,
        'CRITICAL': LogColors.RED + LogColors.BOLD
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{LogColors.RESET}"
        
        # Format the message
        result = super().format(record)
        
        # Reset levelname for next use
        record.levelname = levelname
        
        return result


def setup_logger(
    name='adaptive_routing',
    level=logging.INFO,
    log_dir='logs',
    console=True,
    file_logging=True,
    log_file=None
):
    """
    Set up centralized logging configuration.
    
    Args:
        name: Logger name (default: 'adaptive_routing')
        level: Logging level (default: INFO)
        log_dir: Directory for log files (default: 'logs')
        console: Enable console output (default: True)
        file_logging: Enable file logging (default: True)
        log_file: Specific log file name (default: auto-generated with timestamp)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_logging:
        # Create log directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate log file name with timestamp if not provided
        if log_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f"{name}_{timestamp}.log"
        
        log_path = os.path.join(log_dir, log_file)
        
        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # File logs everything
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to file: {log_path}")
    
    return logger


def get_logger(name=None):
    """
    Get a logger instance with the specified name.
    
    If the logger doesn't exist, creates a basic configured logger.
    
    Args:
        name: Logger name (if None, returns root logger)
        
    Returns:
        Logger instance
    """
    if name is None:
        name = 'adaptive_routing'
    
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set up basic configuration
    if not logger.handlers:
        logger = setup_logger(name)
    
    return logger


def set_log_level(logger, level):
    """
    Set the logging level for a logger and all its handlers.
    
    Args:
        logger: Logger instance or logger name
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    
    logger.setLevel(level)
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(level)


def create_module_logger(module_name):
    """
    Create a logger for a specific module.
    
    Args:
        module_name: Name of the module (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"adaptive_routing.{module_name}")
