#!/usr/bin/env python3
# WRAPD: Model Search and Filter Widget

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QSlider, QPushButton,
    QScrollArea, QFrame, QCompleter, QToolButton,
    QButtonGroup, QRadioButton
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel, QTimer

from ..models.model_filter import ModelFilter, SortField, SortOrder

class ModelSearchWidget(QWidget):
    """Advanced search and filter widget for models"""
    
    filterChanged = pyqtSignal(ModelFilter)
    
    def __init__(self, filter_obj: ModelFilter, parent=None):
        super().__init__(parent)
        
        self.filter_obj = filter_obj
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._emit_filter_changed)
        
        self._create_ui()
        self._connect_signals()
        
    def _create_ui(self):
        """Create the search and filter UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("Search & Filter")
        title_label.setObjectName("searchTitle")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        layout.addWidget(title_label)
        
        # Search input
        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search models, providers, tags...")
        search_layout.addWidget(self.search_input)
        
        # Search suggestions (auto-complete)
        self.search_completer = QCompleter()
        self.search_input.setCompleter(self.search_completer)
        
        layout.addWidget(search_group)
        
        # Quick filters
        quick_group = QGroupBox("Quick Filters")
        quick_layout = QVBoxLayout(quick_group)
        
        # Provider filters
        provider_layout = QHBoxLayout()
        self.openrouter_cb = QCheckBox("OpenRouter")
        self.ollama_cb = QCheckBox("Ollama")
        self.all_providers_cb = QCheckBox("All")
        self.all_providers_cb.setChecked(True)
        
        provider_layout.addWidget(self.openrouter_cb)
        provider_layout.addWidget(self.ollama_cb)
        provider_layout.addWidget(self.all_providers_cb)
        
        quick_layout.addLayout(provider_layout)
        
        # Special filters
        self.favorites_only_cb = QCheckBox("Favorites only")
        self.free_only_cb = QCheckBox("Free models only")
        self.available_only_cb = QCheckBox("Available only")
        self.available_only_cb.setChecked(True)
        
        quick_layout.addWidget(self.favorites_only_cb)
        quick_layout.addWidget(self.free_only_cb)
        quick_layout.addWidget(self.available_only_cb)
        
        layout.addWidget(quick_group)
        
        # Advanced filters (collapsible)
        self.advanced_group = QGroupBox("Advanced Filters")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        
        # Scroll area for advanced filters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarNever)
        
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)
        
        # Pricing filters
        pricing_group = QGroupBox("Pricing")
        pricing_layout = QFormLayout(pricing_group)
        
        # Price range
        self.max_input_price = QDoubleSpinBox()
        self.max_input_price.setRange(0, 1000)
        self.max_input_price.setDecimals(6)
        self.max_input_price.setSuffix(" per 1M tokens")
        self.max_input_price.setSpecialValueText("No limit")
        pricing_layout.addRow("Max Input Price:", self.max_input_price)
        
        self.max_output_price = QDoubleSpinBox()
        self.max_output_price.setRange(0, 1000)
        self.max_output_price.setDecimals(6)
        self.max_output_price.setSuffix(" per 1M tokens")
        self.max_output_price.setSpecialValueText("No limit")
        pricing_layout.addRow("Max Output Price:", self.max_output_price)
        
        advanced_layout.addWidget(pricing_group)
        
        # Capabilities filters
        caps_group = QGroupBox("Capabilities")
        caps_layout = QVBoxLayout(caps_group)
        
        # Context length
        context_layout = QHBoxLayout()
        context_layout.addWidget(QLabel("Min Context Length:"))
        
        self.min_context_slider = QSlider(Qt.Horizontal)
        self.min_context_slider.setRange(0, 200)  # 0 to 200K tokens
        self.min_context_slider.setValue(0)
        context_layout.addWidget(self.min_context_slider)
        
        self.min_context_label = QLabel("0K")
        context_layout.addWidget(self.min_context_label)
        
        caps_layout.addLayout(context_layout)
        
        # Feature checkboxes
        self.supports_images_cb = QCheckBox("Supports Images")
        self.supports_images_cb.setTristate(True)
        self.supports_functions_cb = QCheckBox("Supports Function Calling")
        self.supports_functions_cb.setTristate(True)
        self.supports_streaming_cb = QCheckBox("Supports Streaming")
        self.supports_streaming_cb.setTristate(True)
        self.supports_json_cb = QCheckBox("Supports JSON Mode")
        self.supports_json_cb.setTristate(True)
        
        caps_layout.addWidget(self.supports_images_cb)
        caps_layout.addWidget(self.supports_functions_cb)
        caps_layout.addWidget(self.supports_streaming_cb)
        caps_layout.addWidget(self.supports_json_cb)
        
        advanced_layout.addWidget(caps_group)
        
        # Performance filters
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout(perf_group)
        
        # Availability threshold
        availability_layout = QHBoxLayout()
        self.min_availability_slider = QSlider(Qt.Horizontal)
        self.min_availability_slider.setRange(0, 100)
        self.min_availability_slider.setValue(0)
        availability_layout.addWidget(self.min_availability_slider)
        
        self.min_availability_label = QLabel("0%")
        availability_layout.addWidget(self.min_availability_label)
        
        perf_layout.addRow("Min Availability:", availability_layout)
        
        # Response time threshold
        self.max_response_time = QDoubleSpinBox()
        self.max_response_time.setRange(0, 60)
        self.max_response_time.setDecimals(1)
        self.max_response_time.setSuffix(" seconds")
        self.max_response_time.setSpecialValueText("No limit")
        perf_layout.addRow("Max Response Time:", self.max_response_time)
        
        advanced_layout.addWidget(perf_group)
        
        # Local model filters
        local_group = QGroupBox("Local Models (Ollama)")
        local_layout = QVBoxLayout(local_group)
        
        self.installed_only_cb = QCheckBox("Installed only")
        local_layout.addWidget(self.installed_only_cb)
        
        # Size limit
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Max Size:"))
        
        self.max_size_slider = QSlider(Qt.Horizontal)
        self.max_size_slider.setRange(0, 70)  # 0 to 70 GB
        self.max_size_slider.setValue(70)
        size_layout.addWidget(self.max_size_slider)
        
        self.max_size_label = QLabel("No limit")
        size_layout.addWidget(self.max_size_label)
        
        local_layout.addLayout(size_layout)
        
        advanced_layout.addWidget(local_group)
        
        # User filters
        user_group = QGroupBox("User Data")
        user_layout = QVBoxLayout(user_group)
        
        self.used_only_cb = QCheckBox("Previously used only")
        user_layout.addWidget(self.used_only_cb)
        
        # Minimum rating
        rating_layout = QHBoxLayout()
        rating_layout.addWidget(QLabel("Min Rating:"))
        
        self.min_rating_combo = QComboBox()
        self.min_rating_combo.addItems(["Any", "1★", "2★", "3★", "4★", "5★"])
        rating_layout.addWidget(self.min_rating_combo)
        
        user_layout.addLayout(rating_layout)
        
        advanced_layout.addWidget(user_group)
        
        scroll.setWidget(advanced_widget)
        
        advanced_scroll_layout = QVBoxLayout(self.advanced_group)
        advanced_scroll_layout.addWidget(scroll)
        
        layout.addWidget(self.advanced_group)
        
        # Clear filters button
        self.clear_btn = QPushButton("Clear All Filters")
        self.clear_btn.setObjectName("clearFiltersBtn")
        layout.addWidget(self.clear_btn)
        
        # Active filters count
        self.active_filters_label = QLabel("No active filters")
        self.active_filters_label.setObjectName("activeFiltersLabel")
        layout.addWidget(self.active_filters_label)
        
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect widget signals"""
        # Search input with delay
        self.search_input.textChanged.connect(self._on_search_delayed)
        
        # Quick filters
        self.openrouter_cb.toggled.connect(self._on_provider_filter_changed)
        self.ollama_cb.toggled.connect(self._on_provider_filter_changed)
        self.all_providers_cb.toggled.connect(self._on_all_providers_changed)
        
        self.favorites_only_cb.toggled.connect(self._on_filter_changed)
        self.free_only_cb.toggled.connect(self._on_filter_changed)
        self.available_only_cb.toggled.connect(self._on_filter_changed)
        
        # Advanced filters
        self.max_input_price.valueChanged.connect(self._on_filter_changed)
        self.max_output_price.valueChanged.connect(self._on_filter_changed)
        
        self.min_context_slider.valueChanged.connect(self._update_context_label)
        self.min_context_slider.valueChanged.connect(self._on_filter_changed)
        
        self.supports_images_cb.stateChanged.connect(self._on_filter_changed)
        self.supports_functions_cb.stateChanged.connect(self._on_filter_changed)
        self.supports_streaming_cb.stateChanged.connect(self._on_filter_changed)
        self.supports_json_cb.stateChanged.connect(self._on_filter_changed)
        
        self.min_availability_slider.valueChanged.connect(self._update_availability_label)
        self.min_availability_slider.valueChanged.connect(self._on_filter_changed)
        self.max_response_time.valueChanged.connect(self._on_filter_changed)
        
        self.installed_only_cb.toggled.connect(self._on_filter_changed)
        self.max_size_slider.valueChanged.connect(self._update_size_label)
        self.max_size_slider.valueChanged.connect(self._on_filter_changed)
        
        self.used_only_cb.toggled.connect(self._on_filter_changed)
        self.min_rating_combo.currentTextChanged.connect(self._on_filter_changed)
        
        # Clear button
        self.clear_btn.clicked.connect(self._clear_filters)
    
    def _on_search_delayed(self):
        """Handle search input with delay"""
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms delay
    
    def _on_provider_filter_changed(self):
        """Handle provider filter changes"""
        if self.sender() != self.all_providers_cb:
            # Update all providers checkbox
            all_checked = self.openrouter_cb.isChecked() and self.ollama_cb.isChecked()
            none_checked = not self.openrouter_cb.isChecked() and not self.ollama_cb.isChecked()
            
            self.all_providers_cb.blockSignals(True)
            if all_checked:
                self.all_providers_cb.setChecked(True)
            elif none_checked:
                # At least one provider must be selected
                self.sender().setChecked(True)
                return
            else:
                self.all_providers_cb.setChecked(False)
            self.all_providers_cb.blockSignals(False)
        
        self._on_filter_changed()
    
    def _on_all_providers_changed(self, checked: bool):
        """Handle all providers checkbox"""
        if checked:
            self.openrouter_cb.setChecked(True)
            self.ollama_cb.setChecked(True)
        
        self._on_filter_changed()
    
    def _update_context_label(self, value: int):
        """Update context length label"""
        if value == 0:
            self.min_context_label.setText("0K")
        else:
            self.min_context_label.setText(f"{value}K")
    
    def _update_availability_label(self, value: int):
        """Update availability label"""
        self.min_availability_label.setText(f"{value}%")
    
    def _update_size_label(self, value: int):
        """Update size label"""
        if value >= 70:
            self.max_size_label.setText("No limit")
        else:
            self.max_size_label.setText(f"{value} GB")
    
    def _on_filter_changed(self):
        """Handle filter changes"""
        self._update_filter_object()
        self._update_active_filters_label()
        self._emit_filter_changed()
    
    def _update_filter_object(self):
        """Update the filter object with current UI values"""
        # Search query
        self.filter_obj.search_query = self.search_input.text()
        
        # Provider filters
        providers = []
        if self.openrouter_cb.isChecked():
            providers.append("openrouter")
        if self.ollama_cb.isChecked():
            providers.append("ollama")
        self.filter_obj.providers = providers
        
        # Quick filters
        self.filter_obj.favorites_only = self.favorites_only_cb.isChecked()
        self.filter_obj.free_only = self.free_only_cb.isChecked()
        self.filter_obj.available_only = self.available_only_cb.isChecked()
        
        # Advanced filters
        if self.advanced_group.isChecked():
            # Pricing
            if self.max_input_price.value() > 0:
                self.filter_obj.max_input_price = self.max_input_price.value()
            else:
                self.filter_obj.max_input_price = None
            
            if self.max_output_price.value() > 0:
                self.filter_obj.max_output_price = self.max_output_price.value()
            else:
                self.filter_obj.max_output_price = None
            
            # Context length
            if self.min_context_slider.value() > 0:
                self.filter_obj.min_context_length = self.min_context_slider.value() * 1000
            else:
                self.filter_obj.min_context_length = None
            
            # Capabilities
            self.filter_obj.supports_images = self._get_tristate_value(self.supports_images_cb)
            self.filter_obj.supports_function_calling = self._get_tristate_value(self.supports_functions_cb)
            self.filter_obj.supports_streaming = self._get_tristate_value(self.supports_streaming_cb)
            self.filter_obj.supports_json_mode = self._get_tristate_value(self.supports_json_cb)
            
            # Performance
            if self.min_availability_slider.value() > 0:
                self.filter_obj.min_availability = self.min_availability_slider.value() / 100.0
            else:
                self.filter_obj.min_availability = None
            
            if self.max_response_time.value() > 0:
                self.filter_obj.max_response_time = self.max_response_time.value()
            else:
                self.filter_obj.max_response_time = None
            
            # Local model filters
            self.filter_obj.installed_only = self.installed_only_cb.isChecked()
            
            if self.max_size_slider.value() < 70:
                self.filter_obj.max_size_gb = float(self.max_size_slider.value())
            else:
                self.filter_obj.max_size_gb = None
            
            # User filters
            self.filter_obj.used_only = self.used_only_cb.isChecked()
            
            rating_text = self.min_rating_combo.currentText()
            if rating_text != "Any":
                self.filter_obj.min_rating = int(rating_text[0])
            else:
                self.filter_obj.min_rating = None
        else:
            # Reset advanced filters
            self.filter_obj.max_input_price = None
            self.filter_obj.max_output_price = None
            self.filter_obj.min_context_length = None
            self.filter_obj.supports_images = None
            self.filter_obj.supports_function_calling = None
            self.filter_obj.supports_streaming = None
            self.filter_obj.supports_json_mode = None
            self.filter_obj.min_availability = None
            self.filter_obj.max_response_time = None
            self.filter_obj.installed_only = False
            self.filter_obj.max_size_gb = None
            self.filter_obj.used_only = False
            self.filter_obj.min_rating = None
    
    def _get_tristate_value(self, checkbox: QCheckBox) -> bool:
        """Get tristate checkbox value"""
        state = checkbox.checkState()
        if state == Qt.Checked:
            return True
        elif state == Qt.Unchecked:
            return False
        else:  # Qt.PartiallyChecked
            return None
    
    def _update_active_filters_label(self):
        """Update active filters count label"""
        count = self.filter_obj.get_active_filter_count()
        if count == 0:
            self.active_filters_label.setText("No active filters")
        elif count == 1:
            self.active_filters_label.setText("1 active filter")
        else:
            self.active_filters_label.setText(f"{count} active filters")
    
    def _clear_filters(self):
        """Clear all filters"""
        # Block signals temporarily
        self.blockSignals(True)
        
        # Reset search
        self.search_input.clear()
        
        # Reset quick filters
        self.all_providers_cb.setChecked(True)
        self.openrouter_cb.setChecked(True)
        self.ollama_cb.setChecked(True)
        self.favorites_only_cb.setChecked(False)
        self.free_only_cb.setChecked(False)
        self.available_only_cb.setChecked(True)
        
        # Reset advanced filters
        self.max_input_price.setValue(0)
        self.max_output_price.setValue(0)
        self.min_context_slider.setValue(0)
        
        self.supports_images_cb.setCheckState(Qt.PartiallyChecked)
        self.supports_functions_cb.setCheckState(Qt.PartiallyChecked)
        self.supports_streaming_cb.setCheckState(Qt.PartiallyChecked)
        self.supports_json_cb.setCheckState(Qt.PartiallyChecked)
        
        self.min_availability_slider.setValue(0)
        self.max_response_time.setValue(0)
        
        self.installed_only_cb.setChecked(False)
        self.max_size_slider.setValue(70)
        
        self.used_only_cb.setChecked(False)
        self.min_rating_combo.setCurrentIndex(0)
        
        # Reset filter object
        self.filter_obj.clear_filters()
        
        # Re-enable signals and emit change
        self.blockSignals(False)
        self._update_active_filters_label()
        self._emit_filter_changed()
    
    def _emit_filter_changed(self):
        """Emit filter changed signal"""
        self.filterChanged.emit(self.filter_obj)
    
    def update_search_suggestions(self, suggestions: list):
        """Update search auto-complete suggestions"""
        model = QStringListModel(suggestions)
        self.search_completer.setModel(model)