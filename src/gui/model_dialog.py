#!/usr/bin/env python3
# WRAPD: Model Selection Dialog

import os
import logging
import asyncio
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, 
                           QDoubleSpinBox, QTabWidget, QPushButton, QFileDialog, 
                           QGroupBox, QRadioButton, QButtonGroup, QMessageBox,
                           QDialogButtonBox, QListWidget, QProgressBar, QListWidgetItem,
                           QSizePolicy, QApplication, QWidget)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer

class ModelLoadThread(QThread):
    """Thread for loading available models"""
    
    modelsLoaded = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, llm_interface, parent=None):
        """Initialize the model load thread
        
        Args:
            llm_interface: LLM interface instance
            parent (QObject, optional): Parent object
        """
        super().__init__(parent)
        self.llm = llm_interface
    
    def run(self):
        """Run the thread"""
        try:
            # Create event loop for async calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Get models
            models = loop.run_until_complete(self.llm.get_available_models())
            
            # Emit signal with models
            self.modelsLoaded.emit(models)
            
            # Close event loop
            loop.close()
        except Exception as e:
            self.error.emit(str(e))

class ModelDialog(QDialog):
    """Model selection dialog for WRAPD application"""
    
    def __init__(self, config_manager, llm_interface, parent=None):
        """Initialize the model dialog
        
        Args:
            config_manager: Configuration manager instance
            llm_interface: LLM interface instance
            parent (QWidget, optional): Parent widget
        """
        super().__init__(parent)
        
        self.config = config_manager
        self.llm = llm_interface
        self.logger = logging.getLogger("wrapd.model")
        
        self.setWindowTitle("Select AI Model")
        self.resize(600, 500)
        
        # Current selected values
        self.current_provider = self.config.get('llm', 'provider', 'local')
        self.current_model = self.config.get('llm', 'model', 'gemma3:1b')
        
        # Available models
        self.models = {}
        
        # Create UI
        self._create_ui()
        
        # Load models
        self._load_models()
    
    def _create_ui(self):
        """Create the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create tabs for providers
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create local tab
        self._create_local_tab()
        
        # Create OpenRouter tab
        self._create_openrouter_tab()
        
        # Settings group
        settings_group = QGroupBox("Model Settings")
        settings_layout = QFormLayout()
        settings_group.setLayout(settings_layout)
        
        # Temperature
        self.temperature = QDoubleSpinBox()
        self.temperature.setMinimum(0.0)
        self.temperature.setMaximum(1.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(2)
        self.temperature.setValue(self.config.get_float('llm', 'temperature', 0.1))
        settings_layout.addRow("Temperature:", self.temperature)
        
        # Max tokens
        self.max_tokens = QSpinBox()
        self.max_tokens.setMinimum(10)
        self.max_tokens.setMaximum(4096)
        self.max_tokens.setSingleStep(10)
        self.max_tokens.setValue(self.config.get_int('llm', 'max_tokens', 256))
        settings_layout.addRow("Max Tokens:", self.max_tokens)
        
        # Add settings group to main layout
        main_layout.addWidget(settings_group)
        
        # Status label
        self.status_label = QLabel("Loading models...")
        main_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        main_layout.addWidget(self.progress_bar)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Reset button
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self._reset_settings)
        button_layout.addWidget(self.reset_button)
        
        # Spacer
        button_layout.addStretch()
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Models")
        self.refresh_button.clicked.connect(self._load_models)
        button_layout.addWidget(self.refresh_button)
        
        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
        
        # Initial UI state
        self._update_ui_state(False)
    
    def _create_local_tab(self):
        """Create the local models tab"""
        local_tab = QWidget()
        layout = QVBoxLayout()
        local_tab.setLayout(layout)
        
        # Information label
        info_label = QLabel(
            "Local models run directly on your device using Ollama. "
            "Make sure Ollama is installed and running before selecting a local model."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Models list
        self.local_model_list = QListWidget()
        self.local_model_list.itemClicked.connect(self._on_local_model_clicked)
        layout.addWidget(self.local_model_list)
        
        # Add local tab to tab widget
        self.tab_widget.addTab(local_tab, "Local Models")
    
    def _create_openrouter_tab(self):
        """Create the OpenRouter tab"""
        openrouter_tab = QWidget()
        layout = QVBoxLayout()
        openrouter_tab.setLayout(layout)
        
        # API key group
        api_group = QGroupBox("API Key")
        api_layout = QHBoxLayout()
        api_group.setLayout(api_layout)
        
        # API key input
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter OpenRouter API Key")
        api_layout.addWidget(self.api_key_input)
        
        # Set API key button
        self.set_api_key_button = QPushButton("Set API Key")
        self.set_api_key_button.clicked.connect(self._set_api_key)
        api_layout.addWidget(self.set_api_key_button)
        
        # Add API key group to layout
        layout.addWidget(api_group)
        
        # Information label
        info_label = QLabel(
            "OpenRouter provides access to a variety of AI models through a single API. "
            "You'll need an API key from <a href='https://openrouter.ai'>openrouter.ai</a> to use these models."
        )
        info_label.setTextFormat(Qt.RichText)
        info_label.setWordWrap(True)
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label)
        
        # Models list
        self.openrouter_model_list = QListWidget()
        self.openrouter_model_list.itemClicked.connect(self._on_openrouter_model_clicked)
        layout.addWidget(self.openrouter_model_list)
        
        # Add OpenRouter tab to tab widget
        self.tab_widget.addTab(openrouter_tab, "OpenRouter Models")
        
        # Load API key if available
        api_key = self.config.get_api_key('openrouter')
        if api_key:
            self.api_key_input.setText(api_key)
    
    def _load_models(self):
        """Load available models"""
        # Update UI state
        self._update_ui_state(False)
        
        # Start model load thread
        self.model_thread = ModelLoadThread(self.llm, self)
        self.model_thread.modelsLoaded.connect(self._handle_models_loaded)
        self.model_thread.error.connect(self._handle_model_load_error)
        self.model_thread.start()
    
    def _handle_models_loaded(self, models):
        """Handle loaded models
        
        Args:
            models (dict): Dictionary of available models by provider
        """
        # Store models
        self.models = models
        
        # Update UI
        self._update_model_lists()
        self._update_ui_state(True)
        
        # Set status
        total_models = 0
        for provider in models:
            total_models += len(models.get(provider, []))
        
        self.status_label.setText(f"Loaded {total_models} models")
    
    def _handle_model_load_error(self, error):
        """Handle model load error
        
        Args:
            error (str): Error message
        """
        # Update UI state
        self._update_ui_state(True)
        
        # Set status
        self.status_label.setText(f"Error loading models: {error}")
        
        # Show error dialog
        QMessageBox.warning(
            self,
            "Model Load Error",
            f"Failed to load models: {error}\n\n"
            "Make sure Ollama is installed and running for local models, "
            "and check your API key for OpenRouter models."
        )
    
    def _update_model_lists(self):
        """Update model lists with available models"""
        # Clear lists
        self.local_model_list.clear()
        self.openrouter_model_list.clear()
        
        # Add local models
        local_models = self.models.get('local', [])
        for model in local_models:
            item = QListWidgetItem(model.get('name'))
            item.setData(Qt.UserRole, model)
            
            # Check if this is the current model
            if (self.current_provider.lower() == 'local' and 
                self.current_model == model.get('id')):
                item.setSelected(True)
            
            self.local_model_list.addItem(item)
        
        # Add OpenRouter models
        openrouter_models = self.models.get('openrouter', [])
        for model in openrouter_models:
            model_name = model.get('name', model.get('id'))
            item = QListWidgetItem(model_name)
            item.setData(Qt.UserRole, model)
            
            # Add context length info if available
            context_length = model.get('context_length')
            if context_length:
                item.setToolTip(f"Context Length: {context_length} tokens")
            
            # Check if this is the current model
            if (self.current_provider.lower() == 'openrouter' and 
                self.current_model == model.get('id')):
                item.setSelected(True)
            
            self.openrouter_model_list.addItem(item)
    
    def _update_ui_state(self, enabled):
        """Update UI state based on model loading
        
        Args:
            enabled (bool): Whether UI should be enabled
        """
        # Update list widgets
        self.local_model_list.setEnabled(enabled)
        self.openrouter_model_list.setEnabled(enabled)
        
        # Update buttons
        self.refresh_button.setEnabled(enabled)
        self.button_box.setEnabled(enabled)
        
        # Update progress bar
        self.progress_bar.setVisible(not enabled)
    
    def _on_local_model_clicked(self, item):
        """Handle local model item click
        
        Args:
            item (QListWidgetItem): Clicked item
        """
        # Clear selection in other list
        self.openrouter_model_list.clearSelection()
        
        # Get model data
        model = item.data(Qt.UserRole)
        
        # Set current provider and model
        self.current_provider = 'local'
        self.current_model = model.get('id')
        
        # Set active tab
        self.tab_widget.setCurrentIndex(0)
    
    def _on_openrouter_model_clicked(self, item):
        """Handle OpenRouter model item click
        
        Args:
            item (QListWidgetItem): Clicked item
        """
        # Clear selection in other list
        self.local_model_list.clearSelection()
        
        # Get model data
        model = item.data(Qt.UserRole)
        
        # Set current provider and model
        self.current_provider = 'openrouter'
        self.current_model = model.get('id')
        
        # Set active tab
        self.tab_widget.setCurrentIndex(1)
        
        # Check if API key is set
        api_key = self.config.get_api_key('openrouter')
        if not api_key and not self.api_key_input.text():
            # Show warning
            QMessageBox.warning(
                self,
                "API Key Required",
                "An OpenRouter API key is required to use this model.\n"
                "Please enter your API key in the field above."
            )
    
    def _set_api_key(self):
        """Set the OpenRouter API key"""
        api_key = self.api_key_input.text()
        
        if not api_key:
            # Show warning
            QMessageBox.warning(
                self,
                "API Key Required",
                "Please enter an API key to use OpenRouter models."
            )
            return
        
        # Set API key in config
        self.config.set_api_key('openrouter', api_key)
        
        # Show success message
        self.status_label.setText("API key set successfully")
        
        # Reload models
        QTimer.singleShot(500, self._load_models)
    
    def _reset_settings(self):
        """Reset to default model settings"""
        # Set default values
        self.current_provider = 'local'
        self.current_model = 'gemma3:1b'
        self.temperature.setValue(0.1)
        self.max_tokens.setValue(256)
        
        # Update UI
        self._update_selection()
    
    def _update_selection(self):
        """Update the UI to reflect the current selection"""
        # Clear selections
        self.local_model_list.clearSelection()
        self.openrouter_model_list.clearSelection()
        
        # Update local model selection
        if self.current_provider.lower() == 'local':
            for i in range(self.local_model_list.count()):
                item = self.local_model_list.item(i)
                model = item.data(Qt.UserRole)
                if model.get('id') == self.current_model:
                    item.setSelected(True)
                    self.tab_widget.setCurrentIndex(0)
                    break
        
        # Update OpenRouter model selection
        elif self.current_provider.lower() == 'openrouter':
            for i in range(self.openrouter_model_list.count()):
                item = self.openrouter_model_list.item(i)
                model = item.data(Qt.UserRole)
                if model.get('id') == self.current_model:
                    item.setSelected(True)
                    self.tab_widget.setCurrentIndex(1)
                    break
    
    def accept(self):
        """Save settings and accept dialog"""
        # Check if a model is selected
        if not self.current_model:
            QMessageBox.warning(
                self,
                "No Model Selected",
                "Please select a model to continue."
            )
            return
        
        # For OpenRouter, check if API key is set
        if self.current_provider.lower() == 'openrouter':
            api_key = self.config.get_api_key('openrouter')
            if not api_key and not self.api_key_input.text():
                QMessageBox.warning(
                    self,
                    "API Key Required",
                    "An OpenRouter API key is required to use this model.\n"
                    "Please enter your API key in the field above."
                )
                return
            
            # Set API key if provided in UI
            if self.api_key_input.text():
                self.config.set_api_key('openrouter', self.api_key_input.text())
        
        # Save settings
        self.config.set('llm', 'provider', self.current_provider)
        self.config.set('llm', 'model', self.current_model)
        self.config.set('llm', 'temperature', str(self.temperature.value()))
        self.config.set('llm', 'max_tokens', str(self.max_tokens.value()))
        self.config.save()
        
        # Accept dialog
        super().accept()
