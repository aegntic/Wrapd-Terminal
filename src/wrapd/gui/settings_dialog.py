#!/usr/bin/env python3
# WRAPD: Settings Dialog

import os
import sys
import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, 
                           QDoubleSpinBox, QTabWidget, QPushButton, QFileDialog, 
                           QFontComboBox, QGroupBox, QRadioButton, QButtonGroup,
                           QDialogButtonBox, QColorDialog, QSlider, QSizePolicy,
                           QWidget, QTextEdit, QFrame, QApplication)
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtCore import Qt, QSettings, QSize, QTimer

class SettingsDialog(QDialog):
    """Settings dialog for WRAPD application"""
    
    def __init__(self, config_manager, parent=None):
        """Initialize the settings dialog
        
        Args:
            config_manager: Configuration manager instance
            parent (QWidget, optional): Parent widget
        """
        super().__init__(parent)
        
        self.config = config_manager
        self.logger = logging.getLogger("wrapd.settings")
        
        self.setWindowTitle("WRAPD Settings")
        self.resize(800, 600)
        
        # Store original theme for restoring on cancel
        self.original_theme = self.config.get('appearance', 'theme', 'wutang_dark')
        
        # Timer for delayed preview (to avoid rapid theme changes)
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._apply_preview_theme)
        self.preview_delay = 300  # 300ms delay
        
        # Create UI
        self._create_ui()
        
        # Load settings
        self._load_settings()
    
    def _create_ui(self):
        """Create the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_general_tab()
        self._create_appearance_tab()
        self._create_terminal_tab()
        self._create_llm_tab()
        self._create_shortcuts_tab()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Reset button
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self._reset_settings)
        button_layout.addWidget(self.reset_button)
        
        # Spacer
        button_layout.addStretch()
        
        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
    
    def _create_general_tab(self):
        """Create the general settings tab"""
        general_tab = QWidget()
        layout = QFormLayout()
        general_tab.setLayout(layout)
        
        # Startup settings group
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout()
        startup_group.setLayout(startup_layout)
        
        # Auto update check
        self.auto_update_check = QCheckBox("Check for updates on startup")
        startup_layout.addWidget(self.auto_update_check)
        
        # Startup notification
        self.startup_notification = QCheckBox("Show notification on startup")
        startup_layout.addWidget(self.startup_notification)
        
        # Confirm on exit
        self.confirm_exit = QCheckBox("Confirm before exit")
        startup_layout.addWidget(self.confirm_exit)
        
        # Add startup group to layout
        layout.addRow(startup_group)
        
        # Add general tab to tab widget
        self.tab_widget.addTab(general_tab, "General")
    
    def _create_appearance_tab(self):
        """Create the appearance settings tab"""
        appearance_tab = QWidget()
        main_layout = QHBoxLayout()
        appearance_tab.setLayout(main_layout)
        
        # Left side - settings
        settings_widget = QWidget()
        layout = QFormLayout()
        settings_widget.setLayout(layout)
        
        # Theme selection
        layout.addRow(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        # Themes will be loaded in _load_settings()
        
        # Connect theme selection for live preview
        self.theme_combo.currentTextChanged.connect(self._on_theme_selection_changed)
        self.theme_combo.highlighted.connect(self._on_theme_highlighted)
        
        layout.addRow(self.theme_combo)
        
        # Right side - preview
        preview_group = QGroupBox("Theme Preview")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        
        # Create preview widget
        self.preview_widget = self._create_preview_widget()
        preview_layout.addWidget(self.preview_widget)
        
        # Add both sides to main layout
        main_layout.addWidget(settings_widget, 2)  # 2/3 of the space
        main_layout.addWidget(preview_group, 1)   # 1/3 of the space
        
        # Custom theme path
        layout.addRow(QLabel("Custom Theme:"))
        custom_theme_layout = QHBoxLayout()
        self.custom_theme_path = QLineEdit()
        self.custom_theme_path.setReadOnly(True)
        custom_theme_layout.addWidget(self.custom_theme_path, 1)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_custom_theme)
        custom_theme_layout.addWidget(self.browse_button)
        
        layout.addRow(custom_theme_layout)
        
        # Opacity
        layout.addRow(QLabel("Opacity:"))
        opacity_layout = QHBoxLayout()
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(50)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setSingleStep(1)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        
        self.opacity_label = QLabel("100%")
        
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        
        # Connect opacity slider
        self.opacity_slider.valueChanged.connect(self._update_opacity_label)
        
        layout.addRow(opacity_layout)
        
        # Font settings
        font_group = QGroupBox("Font")
        font_layout = QFormLayout()
        font_group.setLayout(font_layout)
        
        # Font family
        self.font_family = QFontComboBox()
        self.font_family.setFontFilters(QFontComboBox.MonospacedFonts)
        font_layout.addRow("Font Family:", self.font_family)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setMinimum(6)
        self.font_size.setMaximum(36)
        font_layout.addRow("Font Size:", self.font_size)
        
        layout.addRow(font_group)
        
        # Cursor style
        cursor_group = QGroupBox("Cursor Style")
        cursor_layout = QVBoxLayout()
        cursor_group.setLayout(cursor_layout)
        
        self.cursor_style_group = QButtonGroup()
        
        self.block_cursor = QRadioButton("Block")
        self.beam_cursor = QRadioButton("Beam")
        self.underline_cursor = QRadioButton("Underline")
        
        self.cursor_style_group.addButton(self.block_cursor, 0)
        self.cursor_style_group.addButton(self.beam_cursor, 1)
        self.cursor_style_group.addButton(self.underline_cursor, 2)
        
        cursor_layout.addWidget(self.block_cursor)
        cursor_layout.addWidget(self.beam_cursor)
        cursor_layout.addWidget(self.underline_cursor)
        
        # Cursor blink checkbox
        self.cursor_blink = QCheckBox("Blinking Cursor")
        cursor_layout.addWidget(self.cursor_blink)
        
        layout.addRow(cursor_group)
        
        # Other options
        other_group = QGroupBox("Other")
        other_layout = QVBoxLayout()
        other_group.setLayout(other_layout)
        
        self.show_line_numbers = QCheckBox("Show Line Numbers")
        other_layout.addWidget(self.show_line_numbers)
        
        layout.addRow(other_group)
        
        # Add appearance tab to tab widget
        self.tab_widget.addTab(appearance_tab, "Appearance")
    
    def _create_preview_widget(self):
        """Create a preview widget showing theme appearance"""
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.StyledPanel)
        preview_frame.setMinimumSize(250, 200)
        
        preview_layout = QVBoxLayout()
        preview_frame.setLayout(preview_layout)
        
        # Title
        title_label = QLabel("Terminal Preview")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        preview_layout.addWidget(title_label)
        
        # Mock terminal output
        terminal_preview = QTextEdit()
        terminal_preview.setReadOnly(True)
        terminal_preview.setMaximumHeight(120)
        terminal_preview.setFont(QFont("Courier", 10))
        
        # Sample terminal content
        sample_text = """$ ls -la
drwxr-xr-x  5 user  staff   160 Dec  6 12:30 .
drwxr-xr-x  3 user  staff    96 Dec  6 12:25 ..
-rw-r--r--  1 user  staff   123 Dec  6 12:30 config.py
-rwxr-xr-x  1 user  staff  2048 Dec  6 12:29 main.py
drwxr-xr-x  2 user  staff    64 Dec  6 12:25 themes/

$ python main.py
Starting WRAPD Terminal...
✓ Theme loaded successfully"""
        
        terminal_preview.setPlainText(sample_text)
        preview_layout.addWidget(terminal_preview)
        
        # UI Elements preview
        ui_group = QGroupBox("UI Elements")
        ui_layout = QVBoxLayout()
        ui_group.setLayout(ui_layout)
        
        # Sample button
        sample_button = QPushButton("Sample Button")
        ui_layout.addWidget(sample_button)
        
        # Sample checkbox
        sample_checkbox = QCheckBox("Sample Checkbox")
        sample_checkbox.setChecked(True)
        ui_layout.addWidget(sample_checkbox)
        
        # Sample combo
        sample_combo = QComboBox()
        sample_combo.addItems(["Option 1", "Option 2", "Option 3"])
        ui_layout.addWidget(sample_combo)
        
        preview_layout.addWidget(ui_group)
        
        # Store references to update them
        self.preview_terminal = terminal_preview
        self.preview_title = title_label
        self.preview_button = sample_button
        self.preview_checkbox = sample_checkbox
        self.preview_combo = sample_combo
        self.preview_ui_group = ui_group
        
        return preview_frame
    
    def _on_theme_selection_changed(self, theme_name):
        """Handle theme selection change (when user selects)"""
        self.preview_timer.stop()
        self.pending_theme = self._get_theme_id_from_name(theme_name)
        self.preview_timer.start(self.preview_delay)
    
    def _on_theme_highlighted(self, index):
        """Handle theme highlight (when user hovers with keyboard)"""
        theme_name = self.theme_combo.itemText(index)
        self.preview_timer.stop()
        self.pending_theme = self._get_theme_id_from_name(theme_name)
        self.preview_timer.start(self.preview_delay)
    
    def _get_theme_id_from_name(self, theme_name):
        """Get theme ID from display name"""
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemText(i) == theme_name:
                return self.theme_combo.itemData(i)
        return 'wutang_dark'  # fallback
    
    def _apply_preview_theme(self):
        """Apply the pending theme for preview"""
        if hasattr(self, 'pending_theme') and self.pending_theme:
            # Apply theme to the application
            from .theme_manager import ThemeManager
            theme_manager = ThemeManager(self.config)
            
            # Get main window reference
            main_window = None
            for widget in QApplication.instance().topLevelWidgets():
                if hasattr(widget, 'central_widget'):  # Main window identifier
                    main_window = widget
                    break
            
            theme_manager.apply_theme(self.pending_theme, main_window)
    
    def _create_terminal_tab(self):
        """Create the terminal settings tab"""
        terminal_tab = QWidget()
        layout = QFormLayout()
        terminal_tab.setLayout(layout)
        
        # Terminal buffer size
        self.buffer_size = QSpinBox()
        self.buffer_size.setMinimum(1000)
        self.buffer_size.setMaximum(1000000)
        self.buffer_size.setSingleStep(1000)
        layout.addRow("Buffer Size (lines):", self.buffer_size)
        
        # Scrollback lines
        self.scrollback_lines = QSpinBox()
        self.scrollback_lines.setMinimum(100)
        self.scrollback_lines.setMaximum(100000)
        self.scrollback_lines.setSingleStep(100)
        layout.addRow("Scrollback Lines:", self.scrollback_lines)
        
        # Bell type
        self.bell_type = QComboBox()
        self.bell_type.addItems(["None", "Visual", "Audible", "Both"])
        layout.addRow("Bell Type:", self.bell_type)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        options_group.setLayout(options_layout)
        
        self.word_wrap = QCheckBox("Word Wrap")
        options_layout.addWidget(self.word_wrap)
        
        self.save_history = QCheckBox("Save Command History")
        options_layout.addWidget(self.save_history)
        
        self.clear_selection_after_copy = QCheckBox("Clear Selection After Copy")
        options_layout.addWidget(self.clear_selection_after_copy)
        
        layout.addRow(options_group)
        
        # History size
        self.history_size = QSpinBox()
        self.history_size.setMinimum(10)
        self.history_size.setMaximum(10000)
        self.history_size.setSingleStep(10)
        layout.addRow("History Size (commands):", self.history_size)
        
        # Shell selection
        self.default_shell = QComboBox()
        self.default_shell.addItems(["System Default", "CMD", "PowerShell", "WSL Bash"])
        
        # Add items based on platform
        if os.name == 'posix':
            self.default_shell.clear()
            self.default_shell.addItems(["System Default", "Bash", "Zsh", "Fish"])
        
        layout.addRow("Default Shell:", self.default_shell)
        
        # Add terminal tab to tab widget
        self.tab_widget.addTab(terminal_tab, "Terminal")
    
    def _create_llm_tab(self):
        """Create the LLM settings tab"""
        llm_tab = QWidget()
        layout = QVBoxLayout()
        llm_tab.setLayout(layout)
        
        # Provider group
        provider_group = QGroupBox("AI Provider")
        provider_layout = QVBoxLayout()
        provider_group.setLayout(provider_layout)
        
        # Provider selection
        provider_form = QFormLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Local", "OpenRouter"])
        provider_form.addRow("Provider:", self.provider_combo)
        
        # Connect provider combo
        self.provider_combo.currentTextChanged.connect(self._update_provider_settings)
        
        provider_layout.addLayout(provider_form)
        
        # Provider settings container
        self.provider_settings = QWidget()
        self.provider_settings_layout = QVBoxLayout()
        self.provider_settings.setLayout(self.provider_settings_layout)
        
        provider_layout.addWidget(self.provider_settings)
        
        # Add provider group to layout
        layout.addWidget(provider_group)
        
        # Model settings group
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout()
        model_group.setLayout(model_layout)
        
        # Temperature
        self.temperature = QDoubleSpinBox()
        self.temperature.setMinimum(0.0)
        self.temperature.setMaximum(1.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(2)
        model_layout.addRow("Temperature:", self.temperature)
        
        # Max tokens
        self.max_tokens = QSpinBox()
        self.max_tokens.setMinimum(10)
        self.max_tokens.setMaximum(4096)
        self.max_tokens.setSingleStep(10)
        model_layout.addRow("Max Tokens:", self.max_tokens)
        
        # Add model group to layout
        layout.addWidget(model_group)
        
        # Cache settings group
        cache_group = QGroupBox("Cache Settings")
        cache_layout = QFormLayout()
        cache_group.setLayout(cache_layout)
        
        # Cache responses
        self.cache_responses = QCheckBox("Cache Responses")
        cache_layout.addRow(self.cache_responses)
        
        # Cache size
        self.cache_size = QSpinBox()
        self.cache_size.setMinimum(10)
        self.cache_size.setMaximum(10000)
        self.cache_size.setSingleStep(10)
        cache_layout.addRow("Cache Size (entries):", self.cache_size)
        
        # Add cache group to layout
        layout.addWidget(cache_group)
        
        # Add llm tab to tab widget
        self.tab_widget.addTab(llm_tab, "AI")
    
    def _create_shortcuts_tab(self):
        """Create the shortcuts settings tab"""
        shortcuts_tab = QWidget()
        layout = QFormLayout()
        shortcuts_tab.setLayout(layout)
        
        # Create shortcut fields
        self.shortcuts = {}
        
        shortcut_keys = [
            ('new_tab', 'New Tab'),
            ('close_tab', 'Close Tab'),
            ('next_tab', 'Next Tab'),
            ('previous_tab', 'Previous Tab'),
            ('clear_terminal', 'Clear Terminal'),
            ('toggle_transparency', 'Toggle Transparency'),
            ('increase_font_size', 'Increase Font Size'),
            ('decrease_font_size', 'Decrease Font Size'),
            ('reset_font_size', 'Reset Font Size')
        ]
        
        for key, label in shortcut_keys:
            shortcut_edit = QLineEdit()
            shortcut_edit.setPlaceholderText("Enter keyboard shortcut")
            layout.addRow(f"{label}:", shortcut_edit)
            self.shortcuts[key] = shortcut_edit
        
        # Add shortcuts tab to tab widget
        self.tab_widget.addTab(shortcuts_tab, "Shortcuts")
    
    def _load_settings(self):
        """Load settings from configuration"""
        # General settings
        self.auto_update_check.setChecked(self.config.get_boolean('general', 'auto_update_check', True))
        self.startup_notification.setChecked(self.config.get_boolean('general', 'startup_notification', True))
        self.confirm_exit.setChecked(self.config.get_boolean('general', 'confirm_exit', True))
        
        # Appearance settings
        # Load available themes
        themes = self.config.get_available_themes()
        for theme_id, theme_name in themes.items():
            self.theme_combo.addItem(theme_name, theme_id)
        
        # Set current theme
        current_theme = self.config.get('appearance', 'theme', 'system')
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        # Custom theme path
        custom_path = self.config.get('appearance', 'custom_css_path', '')
        self.custom_theme_path.setText(custom_path)
        
        # Opacity
        opacity = int(float(self.config.get('appearance', 'opacity', '0.95')) * 100)
        self.opacity_slider.setValue(opacity)
        
        # Font settings
        font_family = self.config.get('appearance', 'font_family', 'Consolas, Menlo, monospace')
        font_size = self.config.get_int('appearance', 'font_size', 12)
        
        # Set font family (use first font in list)
        first_font = font_family.split(',')[0].strip()
        index = self.font_family.findText(first_font, Qt.MatchContains)
        if index >= 0:
            self.font_family.setCurrentIndex(index)
        
        # Set font size
        self.font_size.setValue(font_size)
        
        # Cursor style
        cursor_style = self.config.get('appearance', 'cursor_style', 'block')
        if cursor_style == 'block':
            self.block_cursor.setChecked(True)
        elif cursor_style == 'beam':
            self.beam_cursor.setChecked(True)
        elif cursor_style == 'underline':
            self.underline_cursor.setChecked(True)
        
        # Cursor blink
        self.cursor_blink.setChecked(self.config.get_boolean('terminal', 'cursor_blink', True))
        
        # Line numbers
        self.show_line_numbers.setChecked(self.config.get_boolean('appearance', 'show_line_numbers', True))
        
        # Terminal settings
        self.buffer_size.setValue(self.config.get_int('terminal', 'buffer_size', 10000))
        self.scrollback_lines.setValue(self.config.get_int('terminal', 'scrollback_lines', 5000))
        
        # Bell type
        bell_type = self.config.get('terminal', 'bell', 'visual')
        if bell_type == 'none':
            self.bell_type.setCurrentIndex(0)
        elif bell_type == 'visual':
            self.bell_type.setCurrentIndex(1)
        elif bell_type == 'audible':
            self.bell_type.setCurrentIndex(2)
        elif bell_type == 'both':
            self.bell_type.setCurrentIndex(3)
        
        # Options
        self.word_wrap.setChecked(self.config.get_boolean('terminal', 'word_wrap', True))
        self.save_history.setChecked(self.config.get_boolean('terminal', 'save_history', True))
        self.clear_selection_after_copy.setChecked(self.config.get_boolean('terminal', 'clear_selection_after_copy', False))
        
        # History size
        self.history_size.setValue(self.config.get_int('terminal', 'history_size', 1000))
        
        # Default shell
        default_shell = self.config.get('terminal', 'default_shell', '')
        if default_shell:
            index = self.default_shell.findText(default_shell, Qt.MatchFixedString)
            if index >= 0:
                self.default_shell.setCurrentIndex(index)
        
        # LLM settings
        # Provider
        provider = self.config.get('llm', 'provider', 'local')
        if provider.lower() == 'local':
            self.provider_combo.setCurrentIndex(0)
        elif provider.lower() == 'openrouter':
            self.provider_combo.setCurrentIndex(1)
        
        # Update provider settings
        self._update_provider_settings(self.provider_combo.currentText())
        
        # Temperature
        self.temperature.setValue(self.config.get_float('llm', 'temperature', 0.1))
        
        # Max tokens
        self.max_tokens.setValue(self.config.get_int('llm', 'max_tokens', 256))
        
        # Cache settings
        self.cache_responses.setChecked(self.config.get_boolean('llm', 'cache_responses', True))
        self.cache_size.setValue(self.config.get_int('llm', 'cache_size', 500))
        
        # Shortcuts
        for key in self.shortcuts:
            value = self.config.get('shortcuts', key, '')
            self.shortcuts[key].setText(value)
    
    def _update_provider_settings(self, provider_text):
        """Update provider settings UI based on selected provider
        
        Args:
            provider_text (str): Selected provider text
        """
        # Clear current settings
        for i in reversed(range(self.provider_settings_layout.count())):
            widget = self.provider_settings_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Local provider settings
        if provider_text.lower() == 'local':
            form = QFormLayout()
            
            # Model selection
            self.local_model = QComboBox()
            self.local_model.addItems(["gemma3:1b", "gemma3:3b", "phi3:3b", "qwen2:7b"])
            
            # Set current model
            current_model = self.config.get('llm', 'model', 'gemma3:1b')
            index = self.local_model.findText(current_model, Qt.MatchFixedString)
            if index >= 0:
                self.local_model.setCurrentIndex(index)
            
            form.addRow("Model:", self.local_model)
            
            # Add to layout
            self.provider_settings_layout.addLayout(form)
        
        # OpenRouter provider settings
        elif provider_text.lower() == 'openrouter':
            form = QFormLayout()
            
            # API key
            self.openrouter_api_key = QLineEdit()
            self.openrouter_api_key.setEchoMode(QLineEdit.Password)
            self.openrouter_api_key.setPlaceholderText("Enter API key")
            
            # Set API key if available
            api_key = self.config.get_api_key('openrouter')
            if api_key:
                self.openrouter_api_key.setText(api_key)
            
            form.addRow("API Key:", self.openrouter_api_key)
            
            # Model selection
            self.openrouter_model = QComboBox()
            
            # Define models with costs (input/output per 1M tokens)
            openrouter_models = [
                # FREE MODELS (prioritized at top)
                ("🆓 Meta: Llama 3.1 8B", "meta-llama/llama-3.1-8b-instruct:free", "FREE - Community supported"),
                ("🆓 Microsoft: Phi-3 Mini", "microsoft/phi-3-mini-128k-instruct:free", "FREE - 3.8B params"),
                ("🆓 Qwen: Qwen 2 7B", "qwen/qwen-2-7b-instruct:free", "FREE - 7B params"),
                ("🆓 Google: Gemma 2 9B", "google/gemma-2-9b-it:free", "FREE - 9B params"),
                
                # SEPARATOR
                ("─ PREMIUM MODELS ─", "", ""),
                
                # ANTHROPIC MODELS
                ("Anthropic: Claude 3.5 Sonnet", "anthropic/claude-3.5-sonnet", "$3.00 / $15.00 per 1M tokens"),
                ("Anthropic: Claude 3.5 Haiku", "anthropic/claude-3.5-haiku", "$0.25 / $1.25 per 1M tokens"),
                ("Anthropic: Claude 3 Opus", "anthropic/claude-3-opus", "$15.00 / $75.00 per 1M tokens"),
                ("Anthropic: Claude 3 Sonnet", "anthropic/claude-3-sonnet", "$3.00 / $15.00 per 1M tokens"),
                ("Anthropic: Claude 3 Haiku", "anthropic/claude-3-haiku", "$0.25 / $1.25 per 1M tokens"),
                
                # OPENAI MODELS
                ("OpenAI: GPT-4o", "openai/gpt-4o", "$2.50 / $10.00 per 1M tokens"),
                ("OpenAI: GPT-4o Mini", "openai/gpt-4o-mini", "$0.15 / $0.60 per 1M tokens"),
                ("OpenAI: GPT-4 Turbo", "openai/gpt-4-turbo", "$10.00 / $30.00 per 1M tokens"),
                ("OpenAI: GPT-4", "openai/gpt-4", "$30.00 / $60.00 per 1M tokens"),
                ("OpenAI: GPT-3.5 Turbo", "openai/gpt-3.5-turbo", "$0.50 / $1.50 per 1M tokens"),
                
                # GOOGLE MODELS
                ("Google: Gemini Pro 1.5", "google/gemini-pro-1.5", "$1.25 / $5.00 per 1M tokens"),
                ("Google: Gemini Flash 1.5", "google/gemini-flash-1.5", "$0.075 / $0.30 per 1M tokens"),
                ("Google: Gemma 2 27B", "google/gemma-2-27b-it", "$0.27 / $0.27 per 1M tokens"),
                
                # META MODELS
                ("Meta: Llama 3.1 405B", "meta-llama/llama-3.1-405b-instruct", "$2.70 / $2.70 per 1M tokens"),
                ("Meta: Llama 3.1 70B", "meta-llama/llama-3.1-70b-instruct", "$0.40 / $0.40 per 1M tokens"),
                ("Meta: Llama 3.1 8B", "meta-llama/llama-3.1-8b-instruct", "$0.055 / $0.055 per 1M tokens"),
                ("Meta: Llama 3 70B", "meta-llama/llama-3-70b-instruct", "$0.59 / $0.79 per 1M tokens"),
                ("Meta: Llama 3 8B", "meta-llama/llama-3-8b-instruct", "$0.055 / $0.055 per 1M tokens"),
                
                # MISTRAL MODELS  
                ("Mistral: Large 2", "mistralai/mistral-large", "$2.00 / $6.00 per 1M tokens"),
                ("Mistral: Medium", "mistralai/mistral-medium", "$2.70 / $8.10 per 1M tokens"),
                ("Mistral: Small", "mistralai/mistral-small", "$0.20 / $0.60 per 1M tokens"),
                ("Mistral: 7B Instruct", "mistralai/mistral-7b-instruct", "$0.065 / $0.065 per 1M tokens"),
                ("Mistral: Mixtral 8x7B", "mistralai/mixtral-8x7b-instruct", "$0.24 / $0.24 per 1M tokens"),
                ("Mistral: Mixtral 8x22B", "mistralai/mixtral-8x22b-instruct", "$0.65 / $0.65 per 1M tokens"),
                
                # PERPLEXITY MODELS
                ("Perplexity: Llama 3.1 Sonar 70B", "perplexity/llama-3.1-sonar-large-128k-online", "$1.00 / $1.00 per 1M tokens"),
                ("Perplexity: Llama 3.1 Sonar 8B", "perplexity/llama-3.1-sonar-small-128k-online", "$0.20 / $0.20 per 1M tokens"),
                
                # COHERE MODELS
                ("Cohere: Command R+", "cohere/command-r-plus", "$2.50 / $10.00 per 1M tokens"),
                ("Cohere: Command R", "cohere/command-r", "$0.15 / $0.60 per 1M tokens"),
                
                # DATABRICKS MODELS
                ("Databricks: DBRX Instruct", "databricks/dbrx-instruct", "$0.75 / $2.25 per 1M tokens"),
                
                # SPECIALIZED MODELS
                ("DeepSeek: Coder V2", "deepseek/deepseek-coder", "$0.14 / $0.28 per 1M tokens"),
                ("01.AI: Yi Large", "01-ai/yi-large", "$0.60 / $0.60 per 1M tokens"),
                ("Nous: Hermes 2 Mixtral 8x7B", "nousresearch/nous-hermes-2-mixtral-8x7b-dpo", "$0.27 / $0.27 per 1M tokens"),
                ("Teknium: OpenHermes 2.5 Mistral 7B", "teknium/openhermes-2.5-mistral-7b", "$0.065 / $0.065 per 1M tokens"),
                
                # BUDGET-FRIENDLY OPTIONS
                ("💰 Budget: Zephyr 7B Beta", "huggingfaceh4/zephyr-7b-beta", "$0.065 / $0.065 per 1M tokens"),
                ("💰 Budget: Toppy M 7B", "undi95/toppy-m-7b", "$0.065 / $0.065 per 1M tokens"),
            ]
            
            for display_name, model_id, cost_info in openrouter_models:
                if model_id:  # Skip separator
                    full_display = f"{display_name} - {cost_info}"
                    self.openrouter_model.addItem(full_display, model_id)
                else:
                    # Add separator (disabled item)
                    self.openrouter_model.addItem(display_name)
                    self.openrouter_model.model().item(self.openrouter_model.count() - 1).setEnabled(False)
            
            # Set current model
            current_model = self.config.get('llm', 'model', 'anthropic/claude-3-haiku')
            # Find by data (model ID) instead of text
            for i in range(self.openrouter_model.count()):
                if self.openrouter_model.itemData(i) == current_model:
                    self.openrouter_model.setCurrentIndex(i)
                    break
            
            form.addRow("Model:", self.openrouter_model)
            
            # Add to layout
            self.provider_settings_layout.addLayout(form)
    
    def _update_opacity_label(self, value):
        """Update opacity label with current value
        
        Args:
            value (int): Opacity value (0-100)
        """
        self.opacity_label.setText(f"{value}%")
    
    def _browse_custom_theme(self):
        """Browse for custom theme CSS file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Theme File",
            "",
            "CSS Files (*.css);;All Files (*)"
        )
        
        if file_path:
            self.custom_theme_path.setText(file_path)
    
    def _reset_settings(self):
        """Reset settings to defaults"""
        # Create temporary config with defaults
        import tempfile
        import os
        
        # Create temp file
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        
        # Create config with defaults
        temp_config = type(self.config)(temp_path)
        temp_config._create_default_config()
        
        # Load default settings
        self.config = temp_config
        self._load_settings()
        
        # Clean up
        os.unlink(temp_path)
    
    def accept(self):
        """Save settings and accept dialog"""
        # Save settings
        self._save_settings()
        
        # Accept dialog
        super().accept()
    
    def reject(self):
        """Cancel dialog and restore original theme"""
        # Restore original theme
        from .theme_manager import ThemeManager
        theme_manager = ThemeManager(self.config)
        
        # Get main window reference
        main_window = None
        for widget in QApplication.instance().topLevelWidgets():
            if hasattr(widget, 'central_widget'):  # Main window identifier
                main_window = widget
                break
        
        theme_manager.apply_theme(self.original_theme, main_window)
        
        # Reject dialog
        super().reject()
    
    def _save_settings(self):
        """Save settings to configuration"""
        # General settings
        self.config.set('general', 'auto_update_check', str(self.auto_update_check.isChecked()))
        self.config.set('general', 'startup_notification', str(self.startup_notification.isChecked()))
        self.config.set('general', 'confirm_exit', str(self.confirm_exit.isChecked()))
        
        # Appearance settings
        theme_id = self.theme_combo.currentData()
        self.config.set('appearance', 'theme', theme_id)
        
        # Custom theme path
        self.config.set('appearance', 'custom_css_path', self.custom_theme_path.text())
        
        # Opacity
        opacity = self.opacity_slider.value() / 100
        self.config.set('appearance', 'opacity', str(opacity))
        
        # Font settings
        font_family = self.font_family.currentText()
        self.config.set('appearance', 'font_family', font_family)
        
        font_size = self.font_size.value()
        self.config.set('appearance', 'font_size', str(font_size))
        
        # Cursor style
        if self.block_cursor.isChecked():
            cursor_style = 'block'
        elif self.beam_cursor.isChecked():
            cursor_style = 'beam'
        elif self.underline_cursor.isChecked():
            cursor_style = 'underline'
        else:
            cursor_style = 'block'
        
        self.config.set('appearance', 'cursor_style', cursor_style)
        
        # Cursor blink
        self.config.set('terminal', 'cursor_blink', str(self.cursor_blink.isChecked()))
        
        # Line numbers
        self.config.set('appearance', 'show_line_numbers', str(self.show_line_numbers.isChecked()))
        
        # Terminal settings
        self.config.set('terminal', 'buffer_size', str(self.buffer_size.value()))
        self.config.set('terminal', 'scrollback_lines', str(self.scrollback_lines.value()))
        
        # Bell type
        bell_types = ['none', 'visual', 'audible', 'both']
        bell_type = bell_types[self.bell_type.currentIndex()]
        self.config.set('terminal', 'bell', bell_type)
        
        # Options
        self.config.set('terminal', 'word_wrap', str(self.word_wrap.isChecked()))
        self.config.set('terminal', 'save_history', str(self.save_history.isChecked()))
        self.config.set('terminal', 'clear_selection_after_copy', str(self.clear_selection_after_copy.isChecked()))
        
        # History size
        self.config.set('terminal', 'history_size', str(self.history_size.value()))
        
        # Default shell
        if self.default_shell.currentText() != "System Default":
            self.config.set('terminal', 'default_shell', self.default_shell.currentText())
        else:
            self.config.set('terminal', 'default_shell', '')
        
        # LLM settings
        # Provider
        provider = self.provider_combo.currentText().lower()
        self.config.set('llm', 'provider', provider)
        
        # Provider-specific settings
        if provider == 'local':
            # Model
            self.config.set('llm', 'model', self.local_model.currentText())
        elif provider == 'openrouter':
            # API key
            if self.openrouter_api_key.text():
                self.config.set_api_key('openrouter', self.openrouter_api_key.text())
            
            # Model
            model_data = self.openrouter_model.currentData()
            if model_data:  # Make sure it's not a separator
                self.config.set('llm', 'model', model_data)
        
        # Temperature
        self.config.set('llm', 'temperature', str(self.temperature.value()))
        
        # Max tokens
        self.config.set('llm', 'max_tokens', str(self.max_tokens.value()))
        
        # Cache settings
        self.config.set('llm', 'cache_responses', str(self.cache_responses.isChecked()))
        self.config.set('llm', 'cache_size', str(self.cache_size.value()))
        
        # Shortcuts
        for key, widget in self.shortcuts.items():
            value = widget.text()
            if value:
                self.config.set('shortcuts', key, value)
        
        # Save configuration
        self.config.save()
