#!/usr/bin/env python3
# WRAPD: Main Window for the application

import os
import sys
import asyncio
import platform
import logging
from pathlib import Path
from functools import partial

# PyQt5 imports for GUI
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QSplitter, QTextEdit, QLineEdit, QPushButton, QLabel, 
                           QTabWidget, QComboBox, QCheckBox, QDialog, QFileDialog,
                           QMessageBox, QProgressBar, QSystemTrayIcon, QAction, QMenu,
                           QToolBar, QToolButton, QSizePolicy, QFrame, QGroupBox,
                           QStatusBar, QStyleFactory, QFontComboBox, QSpinBox, QFormLayout,
                           QSlider)
from PyQt5.QtGui import (QFont, QColor, QTextCursor, QIcon, QPalette, QSyntaxHighlighter, 
                        QTextCharFormat, QKeySequence, QClipboard)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QSettings, QTimer, QEvent, QUrl

# Import GUI components
from src.gui.terminal_widget import TerminalWidget
from src.gui.settings_dialog import SettingsDialog
from src.gui.theme_manager import ThemeManager
from src.gui.model_dialog import ModelDialog

class MainWindow(QMainWindow):
    """Main application window for WRAPD"""
    
    def __init__(self, config_manager, llm_interface, command_processor):
        """Initialize the main window
        
        Args:
            config_manager: Configuration manager instance
            llm_interface: LLM interface instance
            command_processor: Command processor instance
        """
        super().__init__()
        
        self.config = config_manager
        self.llm = llm_interface
        self.command_processor = command_processor
        self.logger = logging.getLogger("wrapd.gui")
        
        # Application state
        self.theme_manager = ThemeManager(self.config)
        self.opacity = self.config.get_float('appearance', 'opacity', 0.95)
        
        # Set up window
        self._setup_window()
        self._setup_actions()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_central_widget()
        
        # Apply theme
        self._apply_theme()
        
        # Check first run
        if self.config.get_boolean('general', 'first_run', True):
            self._show_first_run_wizard()
            self.config.set('general', 'first_run', 'false')
    
    def _setup_window(self):
        """Set up the main window properties"""
        # Window title and size
        self.setWindowTitle("WRAPD Terminal")
        self.resize(900, 600)
        
        # Set window opacity
        self.setWindowOpacity(self.opacity)
        
        # Center window on screen
        screen_geometry = self.screen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
    
    def _setup_actions(self):
        """Set up application actions"""
        # File actions
        self.new_tab_action = QAction("New Tab", self)
        self.new_tab_action.setShortcut(QKeySequence(self.config.get('shortcuts', 'new_tab', 'Ctrl+T')))
        self.new_tab_action.triggered.connect(self._add_terminal_tab)
        
        self.close_tab_action = QAction("Close Tab", self)
        self.close_tab_action.setShortcut(QKeySequence(self.config.get('shortcuts', 'close_tab', 'Ctrl+W')))
        self.close_tab_action.triggered.connect(self._close_current_tab)
        
        self.settings_action = QAction("Settings", self)
        self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_action.triggered.connect(self._show_settings_dialog)
        
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence("Alt+F4"))
        self.exit_action.triggered.connect(self.close)
        
        # Edit actions
        self.copy_action = QAction("Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.triggered.connect(self._copy_selection)
        
        self.paste_action = QAction("Paste", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.paste_action.triggered.connect(self._paste_to_terminal)
        
        self.select_all_action = QAction("Select All", self)
        self.select_all_action.setShortcut(QKeySequence.SelectAll)
        self.select_all_action.triggered.connect(self._select_all_terminal)
        
        self.clear_terminal_action = QAction("Clear Terminal", self)
        self.clear_terminal_action.setShortcut(QKeySequence(self.config.get('shortcuts', 'clear_terminal', 'Ctrl+L')))
        self.clear_terminal_action.triggered.connect(self._clear_terminal)
        
        # View actions
        self.increase_font_action = QAction("Increase Font Size", self)
        self.increase_font_action.setShortcut(QKeySequence(self.config.get('shortcuts', 'increase_font_size', 'Ctrl++')))
        self.increase_font_action.triggered.connect(self._increase_font_size)
        
        self.decrease_font_action = QAction("Decrease Font Size", self)
        self.decrease_font_action.setShortcut(QKeySequence(self.config.get('shortcuts', 'decrease_font_size', 'Ctrl+-')))
        self.decrease_font_action.triggered.connect(self._decrease_font_size)
        
        self.reset_font_action = QAction("Reset Font Size", self)
        self.reset_font_action.setShortcut(QKeySequence(self.config.get('shortcuts', 'reset_font_size', 'Ctrl+0')))
        self.reset_font_action.triggered.connect(self._reset_font_size)
        
        self.toggle_transparency_action = QAction("Toggle Transparency", self)
        self.toggle_transparency_action.setShortcut(QKeySequence(self.config.get('shortcuts', 'toggle_transparency', 'Ctrl+Shift+T')))
        self.toggle_transparency_action.triggered.connect(self._toggle_transparency)
        
        # AI actions
        self.select_model_action = QAction("Select AI Model", self)
        self.select_model_action.triggered.connect(self._show_model_dialog)
        
        self.clear_llm_cache_action = QAction("Clear AI Cache", self)
        self.clear_llm_cache_action.triggered.connect(self._clear_llm_cache)
        
        self.clear_history_action = QAction("Clear Dialog History", self)
        self.clear_history_action.triggered.connect(self._clear_dialog_history)
        
        # Help actions
        self.about_action = QAction("About WRAPD", self)
        self.about_action.triggered.connect(self._show_about_dialog)
        
        self.keyboard_shortcuts_action = QAction("Keyboard Shortcuts", self)
        self.keyboard_shortcuts_action.triggered.connect(self._show_keyboard_shortcuts)
    
    def _setup_menus(self):
        """Set up the application menus"""
        self.menubar = self.menuBar()
        
        # File menu
        file_menu = self.menubar.addMenu("&File")
        file_menu.addAction(self.new_tab_action)
        file_menu.addAction(self.close_tab_action)
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # Edit menu
        edit_menu = self.menubar.addMenu("&Edit")
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addAction(self.select_all_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.clear_terminal_action)
        
        # View menu
        view_menu = self.menubar.addMenu("&View")
        view_menu.addAction(self.increase_font_action)
        view_menu.addAction(self.decrease_font_action)
        view_menu.addAction(self.reset_font_action)
        view_menu.addSeparator()
        
        # Theme submenu
        self.theme_menu = view_menu.addMenu("Theme")
        self._update_theme_menu()
        
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_transparency_action)
        
        # AI menu
        ai_menu = self.menubar.addMenu("&AI")
        ai_menu.addAction(self.select_model_action)
        ai_menu.addSeparator()
        ai_menu.addAction(self.clear_llm_cache_action)
        ai_menu.addAction(self.clear_history_action)
        
        # Help menu
        help_menu = self.menubar.addMenu("&Help")
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.keyboard_shortcuts_action)
    
    def _update_theme_menu(self):
        """Update the theme submenu with available themes"""
        self.theme_menu.clear()
        
        # Get available themes
        themes = self.config.get_available_themes()
        current_theme = self.config.get('appearance', 'theme', 'system')
        
        for theme_id, theme_name in themes.items():
            theme_action = QAction(theme_name, self)
            theme_action.setCheckable(True)
            theme_action.setChecked(theme_id == current_theme)
            theme_action.triggered.connect(partial(self._set_theme, theme_id))
            self.theme_menu.addAction(theme_action)
    
    def _setup_toolbar(self):
        """Set up the application toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)
        
        # Add actions to toolbar
        self.toolbar.addAction(self.new_tab_action)
        self.toolbar.addAction(self.close_tab_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.copy_action)
        self.toolbar.addAction(self.paste_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.clear_terminal_action)
        self.toolbar.addSeparator()
        
        # Add opacity slider
        opacity_label = QLabel("Opacity:")
        self.toolbar.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(50)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self.opacity * 100))
        self.opacity_slider.setMaximumWidth(100)
        self.opacity_slider.valueChanged.connect(self._change_opacity)
        self.toolbar.addWidget(self.opacity_slider)
    
    def _setup_status_bar(self):
        """Set up the status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # LLM model indicator
        self.model_label = QLabel()
        self.statusbar.addPermanentWidget(self.model_label)
        
        # Update model label
        llm_provider = self.config.get('llm', 'provider', 'local')
        llm_model = self.config.get('llm', 'model', 'gemma3:1b')
        self.model_label.setText(f"Model: {llm_provider} / {llm_model}")
    
    def _setup_central_widget(self):
        """Set up the central widget with tab container"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.central_widget.setLayout(main_layout)
        
        # Tab widget for terminals
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        main_layout.addWidget(self.tabs)
        
        # Add watermarked branding overlay
        self._add_branding_watermark()
        
        # Add initial terminal tab
        self._add_terminal_tab()
    
    def _add_branding_watermark(self):
        """Add watermarked branding overlay to the top left corner"""
        # Create watermark container
        watermark_frame = QFrame(self.central_widget)
        watermark_frame.setFrameStyle(QFrame.NoFrame)
        watermark_frame.setAttribute(Qt.WA_TransparentForMouseEvents)
        watermark_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        
        # Create layout for watermark
        watermark_layout = QVBoxLayout(watermark_frame)
        watermark_layout.setContentsMargins(8, 8, 8, 8)
        watermark_layout.setSpacing(2)
        
        # Create logo label
        logo_label = QLabel("{ae}")
        logo_label.setFont(QFont("Courier", 16, QFont.Bold))
        logo_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.15);
                background: transparent;
                border: none;
                font-weight: bold;
                font-family: 'Courier', monospace;
            }
        """)
        logo_label.setAlignment(Qt.AlignLeft)
        
        # Create tagline label
        tagline_label = QLabel("forever free. <3 aegntic.ai")
        tagline_label.setFont(QFont("Arial", 8))
        tagline_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.1);
                background: transparent;
                border: none;
                font-size: 8px;
                font-style: italic;
            }
        """)
        tagline_label.setAlignment(Qt.AlignLeft)
        
        # Add labels to layout
        watermark_layout.addWidget(logo_label)
        watermark_layout.addWidget(tagline_label)
        watermark_layout.addStretch()
        
        # Position watermark in top left corner
        watermark_frame.move(0, 0)
        watermark_frame.resize(200, 60)
        watermark_frame.raise_()
        
        # Store reference to watermark for theme updates
        self.watermark_frame = watermark_frame
        self.logo_label = logo_label
        self.tagline_label = tagline_label
    
    def _add_terminal_tab(self):
        """Add a new terminal tab"""
        terminal = TerminalWidget(self.config, self.llm, self.command_processor, parent=self)
        
        # Connect signals
        terminal.statusMessage.connect(self.statusbar.showMessage)
        terminal.commandExecuted.connect(self._update_window_title)
        
        # Add to tabs
        index = self.tabs.addTab(terminal, "Terminal")
        self.tabs.setCurrentIndex(index)
        
        # Set focus to the terminal
        terminal.setFocus()
    
    def _close_tab(self, index):
        """Close a terminal tab
        
        Args:
            index (int): Index of the tab to close
        """
        if self.tabs.count() <= 1:
            # Don't close the last tab, create a new one instead
            terminal = self.tabs.widget(0)
            terminal.clear()
            return
        
        # Remove the tab
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        
        # Clean up
        if widget:
            widget.deleteLater()
    
    def _close_current_tab(self):
        """Close the current terminal tab"""
        current_index = self.tabs.currentIndex()
        if current_index >= 0:
            self._close_tab(current_index)
    
    def _copy_selection(self):
        """Copy selected text to clipboard"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.copy_selection()
    
    def _paste_to_terminal(self):
        """Paste clipboard content to terminal"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.paste_clipboard()
    
    def _select_all_terminal(self):
        """Select all text in terminal"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.select_all()
    
    def _clear_terminal(self):
        """Clear the current terminal"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.clear()
    
    def _increase_font_size(self):
        """Increase the terminal font size"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.increase_font_size()
    
    def _decrease_font_size(self):
        """Decrease the terminal font size"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.decrease_font_size()
    
    def _reset_font_size(self):
        """Reset the terminal font size to default"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.reset_font_size()
    
    def _change_opacity(self, value):
        """Change the window opacity
        
        Args:
            value (int): Opacity value (50-100)
        """
        self.opacity = value / 100
        self.setWindowOpacity(self.opacity)
        self.config.set('appearance', 'opacity', str(self.opacity))
    
    def _toggle_transparency(self):
        """Toggle window transparency on/off"""
        if self.opacity < 1.0:
            # Save current opacity
            self._saved_opacity = self.opacity
            
            # Set to fully opaque
            self.opacity = 1.0
            self.setWindowOpacity(1.0)
            self.opacity_slider.setValue(100)
        else:
            # Restore saved opacity or default
            self.opacity = getattr(self, '_saved_opacity', 0.95)
            self.setWindowOpacity(self.opacity)
            self.opacity_slider.setValue(int(self.opacity * 100))
    
    def _apply_theme(self):
        """Apply the current theme to the application"""
        theme = self.config.get('appearance', 'theme', 'system')
        self.theme_manager.apply_theme(theme, self)
    
    def _set_theme(self, theme_id):
        """Set application theme
        
        Args:
            theme_id (str): Theme identifier
        """
        self.config.set('appearance', 'theme', theme_id)
        self._apply_theme()
        self._update_theme_menu()
    
    def _show_settings_dialog(self):
        """Show the settings dialog"""
        settings_dialog = SettingsDialog(self.config, parent=self)
        if settings_dialog.exec_() == QDialog.Accepted:
            # Apply changes
            self._apply_theme()
            self._update_window_title()
            
            # Update status bar
            llm_provider = self.config.get('llm', 'provider', 'local')
            llm_model = self.config.get('llm', 'model', 'gemma3:1b')
            self.model_label.setText(f"Model: {llm_provider} / {llm_model}")
    
    def _show_model_dialog(self):
        """Show the model selection dialog"""
        model_dialog = ModelDialog(self.config, self.llm, parent=self)
        if model_dialog.exec_() == QDialog.Accepted:
            # Update status bar
            llm_provider = self.config.get('llm', 'provider', 'local')
            llm_model = self.config.get('llm', 'model', 'gemma3:1b')
            self.model_label.setText(f"Model: {llm_provider} / {llm_model}")
    
    def _clear_llm_cache(self):
        """Clear the LLM response cache"""
        self.llm.clear_cache()
        self.statusbar.showMessage("AI cache cleared", 3000)
    
    def _clear_dialog_history(self):
        """Clear the dialog history"""
        self.llm.clear_history()
        self.statusbar.showMessage("Dialog history cleared", 3000)
    
    def _show_about_dialog(self):
        """Show the about dialog"""
        QMessageBox.about(
            self,
            "About WRAPD",
            f"<h1>WRAPD Terminal</h1>"
            f"<p>Version 1.0.0</p>"
            f"<p>A Warp Terminal Replacement with AI-Powered Delivery</p>"
            f"<p>Powered by Gemma 3 1B and OpenRouter</p>"
            f"<p>Copyright &copy; 2025 WRAPD Team</p>"
        )
    
    def _show_keyboard_shortcuts(self):
        """Show the keyboard shortcuts dialog"""
        shortcuts = "<h2>Keyboard Shortcuts</h2>"
        shortcuts += "<table border='0' cellspacing='2' cellpadding='4'>"
        shortcuts += "<tr><th>Action</th><th>Shortcut</th></tr>"
        
        for action_name, shortcut in self.config.items('shortcuts'):
            # Convert action_name to readable format (e.g., "new_tab" -> "New Tab")
            display_name = " ".join(part.capitalize() for part in action_name.split('_'))
            shortcuts += f"<tr><td>{display_name}</td><td>{shortcut}</td></tr>"
        
        shortcuts += "</table>"
        
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)
    
    def _show_first_run_wizard(self):
        """Show the first run wizard"""
        welcome_text = (
            "<h1>Welcome to WRAPD Terminal!</h1>"
            "<p>WRAPD is an AI-powered terminal replacement that provides intelligent "
            "command suggestions, natural language processing, and contextual assistance "
            "while maintaining complete privacy and offline functionality.</p>"
            "<p>You can use Gemma 3 1B (local) or connect to OpenRouter for more powerful models.</p>"
            "<p>Would you like to configure WRAPD now?</p>"
        )
        
        response = QMessageBox.question(
            self,
            "Welcome to WRAPD",
            welcome_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if response == QMessageBox.Yes:
            self._show_settings_dialog()
    
    def _update_window_title(self):
        """Update the window title with current directory"""
        current_dir = os.getcwd()
        self.setWindowTitle(f"WRAPD Terminal - {current_dir}")
    
    def closeEvent(self, event):
        """Handle window close event
        
        Args:
            event: Close event
        """
        if self.config.get_boolean('general', 'confirm_exit', True):
            response = QMessageBox.question(
                self,
                "Confirm Exit",
                "Are you sure you want to exit WRAPD Terminal?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if response == QMessageBox.No:
                event.ignore()
                return
        
        # Accept the event and close
        event.accept()
