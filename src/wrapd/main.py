#!/usr/bin/env python3
"""
WRAPD: Warp Replacement with AI-Powered Delivery
Main application entry point with comprehensive dependency injection and error handling
"""

import os
import sys
import signal
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import platform

# PyQt5 imports
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

# Core application imports
from .core.config_manager import ConfigManager
from .core.llm_interface import LLMInterface
from .core.command_processor import CommandProcessor
from .gui.main_window import MainWindow
from .gui.theme_manager import ThemeManager
from .utils.logger import Logger
from .utils.error_handling import ErrorHandler, WRAPDError

# Application constants
APP_NAME = "WRAPD Terminal"
APP_VERSION = "2.0.0"
APP_AUTHOR = "WRAPD Team"
APP_DOMAIN = "wrapd.dev"
APP_DESCRIPTION = "AI-powered terminal enhancement inspired by Warp"

class ApplicationContainer:
    """Dependency injection container for WRAPD application components"""
    
    def __init__(self):
        self.components: Dict[str, Any] = {}
        self._initialized = False
        
    def register(self, name: str, component: Any) -> None:
        """Register a component in the container"""
        self.components[name] = component
        
    def get(self, name: str) -> Any:
        """Get a component from the container"""
        if name not in self.components:
            raise ValueError(f"Component {name} not found in container")
        return self.components[name]
        
    def initialize(self, config_dir: Path, app_dir: Path) -> None:
        """Initialize all application components in correct order"""
        if self._initialized:
            return
            
        try:
            # 1. Logger (first, needed by everything)
            logger = Logger(config_dir / "wrapd.log")
            self.register("logger", logger)
            logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
            logger.info(f"Platform: {platform.system()} {platform.release()}")
            logger.info(f"Python: {sys.version}")
            
            # 2. Error Handler (second, needed for error reporting)
            error_handler = ErrorHandler(logger)
            self.register("error_handler", error_handler)
            
            # 3. Configuration Manager (core dependency)
            config_manager = ConfigManager(config_dir / "config.ini", logger)
            self.register("config_manager", config_manager)
            
            # 4. Theme Manager (needed for UI)
            theme_manager = ThemeManager(app_dir / "resources" / "themes", config_manager, logger)
            self.register("theme_manager", theme_manager)
            
            # 5. LLM Interface (AI capabilities)
            llm_interface = LLMInterface(config_manager, logger)
            self.register("llm_interface", llm_interface)
            
            # 6. Command Processor (terminal functionality)
            command_processor = CommandProcessor(config_manager, llm_interface, logger)
            self.register("command_processor", command_processor)
            
            self._initialized = True
            logger.info("All application components initialized successfully")
            
        except Exception as e:
            # Handle initialization errors gracefully
            error_msg = f"Failed to initialize application components: {e}"
            if "logger" in self.components:
                self.components["logger"].error(error_msg, exc_info=True)
            else:
                print(f"CRITICAL ERROR: {error_msg}", file=sys.stderr)
                traceback.print_exc()
            raise WRAPDError(error_msg) from e

class SplashScreen(QSplashScreen):
    """Custom splash screen for WRAPD application startup"""
    
    def __init__(self, app_dir: Path):
        # Create splash screen pixmap
        splash_path = app_dir / "resources" / "icons" / "splash.png"
        if splash_path.exists():
            pixmap = QPixmap(str(splash_path))
        else:
            # Create a simple colored pixmap if splash image doesn't exist
            pixmap = QPixmap(600, 400)
            pixmap.fill(Qt.darkBlue)
            
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)
        
        # Setup splash screen
        self.setFont(QFont("Arial", 12))
        self.show()
        
    def show_message(self, message: str) -> None:
        """Show a message on the splash screen"""
        self.showMessage(
            message,
            Qt.AlignBottom | Qt.AlignCenter,
            Qt.white
        )
        QApplication.processEvents()

class WRAPDApplication:
    """Main WRAPD application class with lifecycle management"""
    
    def __init__(self):
        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
        self.container = ApplicationContainer()
        self.app_dir = Path(__file__).parent.parent.parent.resolve()
        self.config_dir = Path.home() / ".wrapd"
        
    def setup_application_paths(self) -> None:
        """Setup application directories and paths"""
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Create necessary subdirectories
        (self.config_dir / "themes").mkdir(exist_ok=True)
        (self.config_dir / "plugins").mkdir(exist_ok=True)
        (self.config_dir / "sessions").mkdir(exist_ok=True)
        (self.config_dir / "cache").mkdir(exist_ok=True)
        
    def setup_qt_application(self) -> QApplication:
        """Setup and configure Qt application"""
        # Handle high DPI displays
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Set application metadata
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName(APP_AUTHOR)
        app.setOrganizationDomain(APP_DOMAIN)
        app.setApplicationDisplayName(APP_NAME)
        
        # Set application icon
        icon_path = self.app_dir / "resources" / "icons" / "wrapd.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            
        return app
        
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger = self.container.get("logger")
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            if self.main_window:
                self.main_window.close()
            if self.app:
                self.app.quit()
                
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def run(self) -> int:
        """Main application entry point"""
        try:
            # Setup application paths
            self.setup_application_paths()
            
            # Create Qt application
            self.app = self.setup_qt_application()
            
            # Show splash screen
            splash = SplashScreen(self.app_dir)
            splash.show_message("Initializing WRAPD...")
            
            # Initialize application components
            splash.show_message("Loading configuration...")
            self.container.initialize(self.config_dir, self.app_dir)
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Apply theme
            splash.show_message("Applying theme...")
            theme_manager = self.container.get("theme_manager")
            theme_manager.apply_current_theme(self.app)
            
            # Create main window
            splash.show_message("Creating main window...")
            self.main_window = MainWindow(
                config_manager=self.container.get("config_manager"),
                llm_interface=self.container.get("llm_interface"),
                command_processor=self.container.get("command_processor"),
                theme_manager=self.container.get("theme_manager"),
                logger=self.container.get("logger")
            )
            
            # Setup error handling for the main window
            error_handler = self.container.get("error_handler")
            error_handler.setup_global_exception_handler(self.main_window)
            
            # Hide splash and show main window
            splash.show_message("Ready!")
            QTimer.singleShot(1000, splash.close)  # Close splash after 1 second
            QTimer.singleShot(500, self.main_window.show)  # Show window after 0.5 seconds
            
            # Log successful startup
            logger = self.container.get("logger")
            logger.info("WRAPD application started successfully")
            
            # Start Qt event loop
            return self.app.exec_()
            
        except WRAPDError as e:
            # Handle application-specific errors
            error_msg = f"WRAPD initialization failed: {e}"
            self._show_critical_error(error_msg)
            return 1
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error during startup: {e}"
            self._show_critical_error(error_msg)
            traceback.print_exc()
            return 1
            
    def _show_critical_error(self, message: str) -> None:
        """Show critical error dialog"""
        if self.app:
            QMessageBox.critical(None, "WRAPD - Critical Error", message)
        else:
            print(f"CRITICAL ERROR: {message}", file=sys.stderr)

def main() -> int:
    """Main entry point for WRAPD application"""
    app = WRAPDApplication()
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
