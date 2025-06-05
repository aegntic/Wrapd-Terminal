#!/usr/bin/env python3
# WRAPD: Warp Replacement with AI-Powered Delivery
# Main application file

import os
import sys
import json
import logging
import platform
from pathlib import Path

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import application modules
from src.gui.main_window import MainWindow
from src.core.config_manager import ConfigManager
from src.core.llm_interface import LLMInterface
from src.core.command_processor import CommandProcessor
from src.utils.logger import setup_logger

# PyQt5 imports
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# Application constants
APP_NAME = "WRAPD Terminal"
APP_VERSION = "1.0.0"
APP_AUTHOR = "WRAPD Team"

def main():
    """Main entry point for the WRAPD application"""
    # Setup application directories
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(os.path.expanduser("~"), ".wrapd")
    os.makedirs(config_dir, exist_ok=True)
    
    # Setup logging
    log_file = os.path.join(config_dir, "wrapd.log")
    logger = setup_logger(log_file)
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    # Initialize configuration
    config_path = os.path.join(config_dir, "config.ini")
    config_manager = ConfigManager(config_path)
    
    # Initialize LLM interface
    llm_interface = LLMInterface(config_manager)
    
    # Initialize command processor
    command_processor = CommandProcessor(config_manager, llm_interface)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_AUTHOR)
    
    # Set application style from config
    theme = config_manager.get("appearance", "theme", "system")
    if theme != "system":
        app.setStyle(theme)
    
    # Create main window
    main_window = MainWindow(config_manager, llm_interface, command_processor)
    
    # Set application icon
    icon_path = os.path.join(app_dir, "resources", "icons", "wrapd.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        main_window.setWindowIcon(QIcon(icon_path))
    
    # Show main window
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
