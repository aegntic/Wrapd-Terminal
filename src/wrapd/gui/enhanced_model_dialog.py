#!/usr/bin/env python3
# WRAPD: Enhanced Model Selection Dialog

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QTabWidget, QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QMessageBox, QDialogButtonBox, QListWidget, QProgressBar, QTextEdit,
    QListWidgetItem, QSizePolicy, QApplication, QWidget, QScrollArea,
    QFrame, QSlider, QTableWidget, QTableWidgetItem, QSplitter,
    QTreeWidget, QTreeWidgetItem, QStackedWidget, QToolButton, QMenu
)
from PyQt5.QtGui import QFont, QIcon, QPalette, QPixmap, QPainter, QColor
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QTimer, QPropertyAnimation,
    QEasingCurve, QRect, QPoint
)

from ..models.model_info import ModelInfo
from ..models.model_filter import ModelFilter, SortField, SortOrder, ModelSearchEngine
from ..models.model_repository import ModelRepository
from .model_card import ModelCard
from .model_search import ModelSearchWidget
from .model_comparison import ModelComparisonWidget
from .model_preview import ModelPreviewWidget
from .favorites_widget import FavoritesWidget

class ModelLoadThread(QThread):
    """Thread for loading models asynchronously"""
    
    modelsLoaded = pyqtSignal(dict)
    modelLoadProgress = pyqtSignal(str, int)  # provider, progress
    error = pyqtSignal(str)
    
    def __init__(self, model_repository: ModelRepository, force_refresh: bool = False):
        super().__init__()
        self.repository = model_repository
        self.force_refresh = force_refresh
        self.logger = logging.getLogger("wrapd.model_load_thread")
    
    def run(self):
        """Run the model loading thread"""
        try:
            # Create event loop for async calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Load models with progress updates
            self.modelLoadProgress.emit("Initializing", 0)
            
            models = {}
            providers = ['openrouter', 'ollama']
            
            for i, provider in enumerate(providers):
                try:
                    self.modelLoadProgress.emit(f"Loading {provider} models", 
                                              int((i / len(providers)) * 100))
                    
                    provider_models = loop.run_until_complete(
                        self.repository.get_models_by_provider(provider, self.force_refresh)
                    )
                    models[provider] = provider_models
                    
                except Exception as e:
                    self.logger.error(f"Failed to load {provider} models: {e}")
                    models[provider] = []
            
            self.modelLoadProgress.emit("Complete", 100)
            self.modelsLoaded.emit(models)
            
            # Close event loop
            loop.close()
            
        except Exception as e:
            self.logger.error(f"Model loading failed: {e}")
            self.error.emit(str(e))

class EnhancedModelDialog(QDialog):
    """Enhanced model selection dialog with rich features"""
    
    def __init__(self, config_manager, llm_interface, parent=None):
        super().__init__(parent)
        
        self.config = config_manager
        self.llm = llm_interface
        self.logger = logging.getLogger("wrapd.enhanced_model_dialog")
        
        # Initialize repository
        self.repository = ModelRepository(config_manager)
        
        # Current state
        self.current_provider = self.config.get('llm', 'provider', 'openrouter')
        self.current_model = self.config.get('llm', 'model', 'anthropic/claude-3-haiku')
        self.selected_models = []  # For comparison
        
        # UI state
        self.filter_obj = ModelFilter()
        self.all_models = {}
        self.filtered_models = []
        
        # Setup dialog
        self.setWindowTitle("Enhanced Model Selection")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Create UI
        self._create_ui()
        
        # Load models
        self._load_models()
        
        # Apply theme
        self._apply_theme()
    
    def _create_ui(self):
        """Create the enhanced UI"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Title and status bar
        self._create_title_bar()
        main_layout.addWidget(self.title_frame)
        
        # Main content area with splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Left panel (search and filters)
        self._create_left_panel()
        
        # Center panel (model list)
        self._create_center_panel()
        
        # Right panel (details)
        self._create_right_panel()
        
        # Add panels to splitter
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.center_panel)
        self.main_splitter.addWidget(self.right_panel)
        
        # Set splitter proportions (20%, 50%, 30%)
        self.main_splitter.setSizes([280, 700, 420])
        
        # Bottom panel (actions)
        self._create_bottom_panel()
        main_layout.addWidget(self.bottom_panel)
        
        # Loading overlay
        self._create_loading_overlay()
    
    def _create_title_bar(self):
        """Create title bar with status"""
        self.title_frame = QFrame()
        self.title_frame.setObjectName("titleFrame")
        layout = QHBoxLayout(self.title_frame)
        
        # Title
        title_label = QLabel("Enhanced Model Selection")
        title_label.setObjectName("titleLabel")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Status indicators
        self.status_label = QLabel("Loading models...")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
    
    def _create_left_panel(self):
        """Create left panel with search and filters"""
        self.left_panel = QWidget()
        layout = QVBoxLayout(self.left_panel)
        
        # Search widget
        self.search_widget = ModelSearchWidget(self.filter_obj)
        self.search_widget.filterChanged.connect(self._on_filter_changed)
        layout.addWidget(self.search_widget)
        
        # Favorites widget
        self.favorites_widget = FavoritesWidget(self.config)
        self.favorites_widget.favoriteSelected.connect(self._on_favorite_selected)
        layout.addWidget(self.favorites_widget)
        
        layout.addStretch()
    
    def _create_center_panel(self):
        """Create center panel with model list"""
        self.center_panel = QWidget()
        layout = QVBoxLayout(self.center_panel)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        # View mode buttons
        self.card_view_btn = QToolButton()
        self.card_view_btn.setText("Cards")
        self.card_view_btn.setCheckable(True)
        self.card_view_btn.setChecked(True)
        self.card_view_btn.clicked.connect(self._set_card_view)
        toolbar_layout.addWidget(self.card_view_btn)
        
        self.list_view_btn = QToolButton()
        self.list_view_btn.setText("List")
        self.list_view_btn.setCheckable(True)
        self.list_view_btn.clicked.connect(self._set_list_view)
        toolbar_layout.addWidget(self.list_view_btn)
        
        # View button group
        self.view_group = QButtonGroup()
        self.view_group.addButton(self.card_view_btn)
        self.view_group.addButton(self.list_view_btn)
        
        toolbar_layout.addStretch()
        
        # Sort controls
        sort_label = QLabel("Sort by:")
        toolbar_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Name", "Provider", "Price (Input)", "Price (Output)",
            "Context Length", "Response Time", "Popularity", "Rating"
        ])
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        toolbar_layout.addWidget(self.sort_combo)
        
        self.sort_order_btn = QToolButton()
        self.sort_order_btn.setText("↑")
        self.sort_order_btn.setToolTip("Sort Order")
        self.sort_order_btn.clicked.connect(self._toggle_sort_order)
        toolbar_layout.addWidget(self.sort_order_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Model display area
        self.model_stack = QStackedWidget()
        
        # Card view
        self.card_scroll = QScrollArea()
        self.card_scroll.setWidgetResizable(True)
        self.card_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.card_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.card_container = QWidget()
        self.card_layout = QGridLayout(self.card_container)
        self.card_layout.setSpacing(10)
        self.card_scroll.setWidget(self.card_container)
        
        # List view
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_list_item_clicked)
        
        self.model_stack.addWidget(self.card_scroll)
        self.model_stack.addWidget(self.list_widget)
        
        layout.addWidget(self.model_stack)
        
        # Results info
        self.results_label = QLabel("No models loaded")
        layout.addWidget(self.results_label)
    
    def _create_right_panel(self):
        """Create right panel with model details"""
        self.right_panel = QWidget()
        layout = QVBoxLayout(self.right_panel)
        
        # Tab widget for different views
        self.detail_tabs = QTabWidget()
        
        # Model details tab
        self.details_widget = self._create_details_widget()
        self.detail_tabs.addTab(self.details_widget, "Details")
        
        # Comparison tab
        self.comparison_widget = ModelComparisonWidget()
        self.detail_tabs.addTab(self.comparison_widget, "Compare")
        
        # Preview tab
        self.preview_widget = ModelPreviewWidget(self.repository)
        self.detail_tabs.addTab(self.preview_widget, "Preview")
        
        layout.addWidget(self.detail_tabs)
    
    def _create_details_widget(self) -> QWidget:
        """Create model details widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Model header
        header_frame = QFrame()
        header_frame.setObjectName("modelHeader")
        header_layout = QVBoxLayout(header_frame)
        
        self.model_name_label = QLabel("Select a model")
        self.model_name_label.setObjectName("modelNameLabel")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.model_name_label.setFont(font)
        header_layout.addWidget(self.model_name_label)
        
        self.model_provider_label = QLabel("")
        self.model_provider_label.setObjectName("modelProviderLabel")
        header_layout.addWidget(self.model_provider_label)
        
        layout.addWidget(header_frame)
        
        # Scrollable details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        details_container = QWidget()
        self.details_layout = QVBoxLayout(details_container)
        
        # Placeholder content
        placeholder = QLabel("Select a model to view details")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setObjectName("placeholderLabel")
        self.details_layout.addWidget(placeholder)
        
        scroll.setWidget(details_container)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_bottom_panel(self):
        """Create bottom panel with actions"""
        self.bottom_panel = QFrame()
        self.bottom_panel.setObjectName("bottomPanel")
        layout = QHBoxLayout(self.bottom_panel)
        
        # Model settings
        settings_group = QGroupBox("Model Settings")
        settings_layout = QFormLayout(settings_group)
        
        # Temperature
        self.temperature_slider = QSlider(Qt.Horizontal)
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(int(self.config.get_float('llm', 'temperature', 0.1) * 100))
        self.temperature_slider.valueChanged.connect(self._on_temperature_changed)
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temperature_slider)
        self.temperature_label = QLabel("0.10")
        temp_layout.addWidget(self.temperature_label)
        
        settings_layout.addRow("Temperature:", temp_layout)
        
        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(10, 8192)
        self.max_tokens_spin.setValue(self.config.get_int('llm', 'max_tokens', 256))
        settings_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        layout.addWidget(settings_group)
        
        layout.addStretch()
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Install button (for Ollama models)
        self.install_btn = QPushButton("Install Model")
        self.install_btn.setVisible(False)
        self.install_btn.clicked.connect(self._install_model)
        button_layout.addWidget(self.install_btn)
        
        # Favorite button
        self.favorite_btn = QPushButton("★")
        self.favorite_btn.setCheckable(True)
        self.favorite_btn.setMaximumWidth(40)
        self.favorite_btn.clicked.connect(self._toggle_favorite)
        button_layout.addWidget(self.favorite_btn)
        
        # Compare button
        self.compare_btn = QPushButton("Compare")
        self.compare_btn.clicked.connect(self._add_to_comparison)
        button_layout.addWidget(self.compare_btn)
        
        # Test button
        self.test_btn = QPushButton("Test")
        self.test_btn.clicked.connect(self._test_model)
        button_layout.addWidget(self.test_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_models)
        button_layout.addWidget(self.refresh_btn)
        
        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)
        
        layout.addLayout(button_layout)
    
    def _create_loading_overlay(self):
        """Create loading overlay"""
        self.loading_overlay = QWidget(self)
        self.loading_overlay.setObjectName("loadingOverlay")
        self.loading_overlay.setGeometry(self.rect())
        
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.addStretch()
        
        loading_label = QLabel("Loading models...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setObjectName("loadingLabel")
        overlay_layout.addWidget(loading_label)
        
        loading_progress = QProgressBar()
        loading_progress.setRange(0, 0)  # Indeterminate
        loading_progress.setMaximumWidth(300)
        loading_progress.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(loading_progress, alignment=Qt.AlignCenter)
        
        overlay_layout.addStretch()
        
        self.loading_overlay.hide()
    
    def _load_models(self):
        """Load models asynchronously"""
        self._show_loading(True)
        
        # Start model loading thread
        self.model_thread = ModelLoadThread(self.repository)
        self.model_thread.modelsLoaded.connect(self._on_models_loaded)
        self.model_thread.modelLoadProgress.connect(self._on_load_progress)
        self.model_thread.error.connect(self._on_load_error)
        self.model_thread.start()
    
    def _refresh_models(self):
        """Refresh models from all providers"""
        self._show_loading(True)
        
        # Start model loading thread with force refresh
        self.model_thread = ModelLoadThread(self.repository, force_refresh=True)
        self.model_thread.modelsLoaded.connect(self._on_models_loaded)
        self.model_thread.modelLoadProgress.connect(self._on_load_progress)
        self.model_thread.error.connect(self._on_load_error)
        self.model_thread.start()
    
    def _show_loading(self, show: bool):
        """Show/hide loading overlay"""
        if show:
            self.loading_overlay.setGeometry(self.rect())
            self.loading_overlay.show()
            self.progress_bar.setRange(0, 0)  # Indeterminate
        else:
            self.loading_overlay.hide()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
    
    def _on_load_progress(self, provider: str, progress: int):
        """Handle load progress updates"""
        self.status_label.setText(f"Loading {provider}...")
        if progress >= 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)
    
    def _on_models_loaded(self, models: Dict[str, List[ModelInfo]]):
        """Handle loaded models"""
        self.all_models = models
        self._update_model_display()
        self._show_loading(False)
        
        # Update status
        total_models = sum(len(provider_models) for provider_models in models.values())
        self.status_label.setText(f"Loaded {total_models} models")
        
        # Update favorites widget
        all_models_list = []
        for provider_models in models.values():
            all_models_list.extend(provider_models)
        self.favorites_widget.update_models(all_models_list)
    
    def _on_load_error(self, error: str):
        """Handle load error"""
        self._show_loading(False)
        self.status_label.setText(f"Error: {error}")
        
        QMessageBox.warning(
            self,
            "Model Load Error",
            f"Failed to load models: {error}\n\n"
            "Some providers may be unavailable. Check your connection and API keys."
        )
    
    def _on_filter_changed(self, filter_obj: ModelFilter):
        """Handle filter changes"""
        self.filter_obj = filter_obj
        self._update_model_display()
    
    def _on_sort_changed(self, sort_text: str):
        """Handle sort field changes"""
        sort_map = {
            "Name": SortField.NAME,
            "Provider": SortField.PROVIDER,
            "Price (Input)": SortField.PRICE_INPUT,
            "Price (Output)": SortField.PRICE_OUTPUT,
            "Context Length": SortField.CONTEXT_LENGTH,
            "Response Time": SortField.RESPONSE_TIME,
            "Popularity": SortField.POPULARITY,
            "Rating": SortField.RATING
        }
        
        self.filter_obj.sort_field = sort_map.get(sort_text, SortField.NAME)
        self._update_model_display()
    
    def _toggle_sort_order(self):
        """Toggle sort order"""
        if self.filter_obj.sort_order == SortOrder.ASCENDING:
            self.filter_obj.sort_order = SortOrder.DESCENDING
            self.sort_order_btn.setText("↓")
        else:
            self.filter_obj.sort_order = SortOrder.ASCENDING
            self.sort_order_btn.setText("↑")
        
        self._update_model_display()
    
    def _update_model_display(self):
        """Update model display with current filter"""
        # Get all models as flat list
        all_models_list = []
        for provider_models in self.all_models.values():
            all_models_list.extend(provider_models)
        
        # Apply filter
        self.filtered_models = self.filter_obj.apply(all_models_list)
        
        # Update displays
        self._update_card_view()
        self._update_list_view()
        
        # Update results label
        total_models = len(all_models_list)
        filtered_count = len(self.filtered_models)
        
        if self.filter_obj.get_active_filter_count() > 0:
            self.results_label.setText(f"Showing {filtered_count} of {total_models} models")
        else:
            self.results_label.setText(f"Showing all {total_models} models")
    
    def _update_card_view(self):
        """Update card view with filtered models"""
        # Clear existing cards
        for i in reversed(range(self.card_layout.count())):
            self.card_layout.itemAt(i).widget().setParent(None)
        
        # Add new cards
        columns = 2  # Number of columns
        for i, model in enumerate(self.filtered_models):
            row = i // columns
            col = i % columns
            
            card = ModelCard(model)
            card.modelSelected.connect(self._on_model_selected)
            self.card_layout.addWidget(card, row, col)
        
        # Add stretch to fill remaining space
        self.card_layout.setRowStretch(len(self.filtered_models) // columns + 1, 1)
    
    def _update_list_view(self):
        """Update list view with filtered models"""
        self.list_widget.clear()
        
        for model in self.filtered_models:
            item_text = f"{model.get_display_name()} ({model.provider})"
            if model.pricing.input_price_per_1m > 0:
                item_text += f" - ${model.get_cost_per_1k_tokens()}/1K tokens"
            else:
                item_text += " - Free"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, model)
            
            # Highlight current model
            if model.id == self.current_model and model.provider == self.current_provider:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            
            self.list_widget.addItem(item)
    
    def _set_card_view(self):
        """Switch to card view"""
        self.model_stack.setCurrentIndex(0)
        self.list_view_btn.setChecked(False)
    
    def _set_list_view(self):
        """Switch to list view"""
        self.model_stack.setCurrentIndex(1)
        self.card_view_btn.setChecked(False)
    
    def _on_model_selected(self, model: ModelInfo):
        """Handle model selection"""
        self.current_provider = model.provider
        self.current_model = model.id
        
        # Update UI
        self._update_model_details(model)
        self._update_action_buttons(model)
        
        # Update selection in list view
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_model = item.data(Qt.UserRole)
            
            font = item.font()
            font.setBold(item_model.id == model.id and item_model.provider == model.provider)
            item.setFont(font)
    
    def _on_list_item_clicked(self, item: QListWidgetItem):
        """Handle list item click"""
        model = item.data(Qt.UserRole)
        self._on_model_selected(model)
    
    def _on_favorite_selected(self, model_id: str, provider: str):
        """Handle favorite selection"""
        # Find and select the model
        for provider_models in self.all_models.values():
            for model in provider_models:
                if model.id == model_id and model.provider == provider:
                    self._on_model_selected(model)
                    return
    
    def _update_model_details(self, model: ModelInfo):
        """Update model details panel"""
        # Clear existing details
        for i in reversed(range(self.details_layout.count())):
            self.details_layout.itemAt(i).widget().setParent(None)
        
        # Update header
        self.model_name_label.setText(model.get_display_name())
        self.model_provider_label.setText(f"Provider: {model.provider.title()}")
        
        # Add detailed information
        self._add_detail_section("Description", model.description or "No description available")
        
        # Capabilities
        caps = model.capabilities
        cap_items = [
            f"Context Length: {caps.context_length:,} tokens",
            f"Max Output: {caps.max_output_tokens:,} tokens",
            f"Images: {'✓' if caps.supports_images else '✗'}",
            f"Functions: {'✓' if caps.supports_function_calling else '✗'}",
            f"Streaming: {'✓' if caps.supports_streaming else '✗'}",
            f"JSON Mode: {'✓' if caps.supports_json_mode else '✗'}",
        ]
        self._add_detail_section("Capabilities", "\n".join(cap_items))
        
        # Pricing
        if model.pricing.input_price_per_1m > 0:
            pricing_text = (
                f"Input: ${model.pricing.input_price_per_1m:.6f} per 1M tokens\n"
                f"Output: ${model.pricing.output_price_per_1m:.6f} per 1M tokens\n"
                f"Cost per 1K tokens: {model.get_cost_per_1k_tokens()}"
            )
        else:
            pricing_text = "Free to use"
        self._add_detail_section("Pricing", pricing_text)
        
        # Performance
        perf = model.performance
        perf_text = (
            f"Availability: {perf.availability_score:.1%}\n"
            f"Reliability: {perf.reliability_score:.1%}\n"
            f"Response Time: {perf.response_time_avg:.2f}s\n"
            f"Rating: {model.get_performance_rating()}"
        )
        self._add_detail_section("Performance", perf_text)
        
        # Local model info
        if model.local_info:
            local_text = (
                f"Size: {model.local_info.size_gb:.1f} GB\n"
                f"Memory Usage: {model.local_info.memory_usage_gb:.1f} GB\n"
                f"Installed: {'✓' if model.local_info.is_installed else '✗'}\n"
                f"Quantization: {model.local_info.quantization}"
            )
            self._add_detail_section("Local Model Info", local_text)
        
        # Tags
        if model.tags:
            self._add_detail_section("Tags", ", ".join(model.tags))
        
        # User data
        if model.usage_count > 0 or model.user_rating:
            user_items = []
            if model.usage_count > 0:
                user_items.append(f"Used {model.usage_count} times")
            if model.last_used:
                user_items.append(f"Last used: {model.last_used.strftime('%Y-%m-%d %H:%M')}")
            if model.user_rating:
                user_items.append(f"Your rating: {'★' * model.user_rating}")
            if model.user_notes:
                user_items.append(f"Notes: {model.user_notes}")
            
            self._add_detail_section("Usage", "\n".join(user_items))
    
    def _add_detail_section(self, title: str, content: str):
        """Add a detail section to the layout"""
        # Section header
        header = QLabel(title)
        header.setObjectName("detailSectionHeader")
        font = QFont()
        font.setBold(True)
        header.setFont(font)
        self.details_layout.addWidget(header)
        
        # Section content
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setObjectName("detailSectionContent")
        content_label.setMargin(10)
        self.details_layout.addWidget(content_label)
        
        # Spacing
        self.details_layout.addSpacing(10)
    
    def _update_action_buttons(self, model: ModelInfo):
        """Update action buttons based on selected model"""
        # Install button (for Ollama models)
        if model.provider == 'ollama' and model.local_info:
            self.install_btn.setVisible(True)
            self.install_btn.setEnabled(not model.local_info.is_installed)
            self.install_btn.setText("Install" if not model.local_info.is_installed else "Installed")
        else:
            self.install_btn.setVisible(False)
        
        # Favorite button
        self.favorite_btn.setChecked(model.is_favorite)
        
        # Test button
        self.test_btn.setEnabled(True)
    
    def _on_temperature_changed(self, value: int):
        """Handle temperature slider change"""
        temp = value / 100.0
        self.temperature_label.setText(f"{temp:.2f}")
    
    def _toggle_favorite(self):
        """Toggle favorite status of current model"""
        if not hasattr(self, 'current_model_obj'):
            return
        
        model = self.current_model_obj
        model.is_favorite = self.favorite_btn.isChecked()
        
        # Update favorites widget
        self.favorites_widget.update_favorite(model.id, model.provider, model.is_favorite)
    
    def _add_to_comparison(self):
        """Add current model to comparison"""
        if hasattr(self, 'current_model_obj'):
            self.comparison_widget.add_model(self.current_model_obj)
            self.detail_tabs.setCurrentIndex(1)  # Switch to comparison tab
    
    def _test_model(self):
        """Test current model performance"""
        if hasattr(self, 'current_model_obj'):
            self.preview_widget.test_model(self.current_model_obj)
            self.detail_tabs.setCurrentIndex(2)  # Switch to preview tab
    
    def _install_model(self):
        """Install selected Ollama model"""
        if not hasattr(self, 'current_model_obj'):
            return
        
        model = self.current_model_obj
        if model.provider != 'ollama' or not model.local_info:
            return
        
        # Start installation
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Installing...")
        
        # This would trigger the actual installation
        # For now, just simulate
        QTimer.singleShot(2000, lambda: self._installation_complete(model))
    
    def _installation_complete(self, model: ModelInfo):
        """Handle installation completion"""
        model.local_info.is_installed = True
        self.install_btn.setText("Installed")
        
        QMessageBox.information(
            self,
            "Installation Complete",
            f"Model {model.name} has been installed successfully."
        )
    
    def _apply_theme(self):
        """Apply theme styling"""
        # This would load theme from the config
        # For now, apply basic styling
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            #titleFrame {
                background-color: #3c3c3c;
                border-bottom: 1px solid #555555;
                padding: 10px;
            }
            
            #titleLabel {
                color: #ffffff;
            }
            
            #statusLabel {
                color: #cccccc;
            }
            
            #bottomPanel {
                background-color: #3c3c3c;
                border-top: 1px solid #555555;
                padding: 10px;
            }
            
            #loadingOverlay {
                background-color: rgba(0, 0, 0, 0.8);
            }
            
            #loadingLabel {
                color: #ffffff;
                font-size: 18px;
            }
            
            #modelHeader {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 10px;
            }
            
            #modelNameLabel {
                color: #ffffff;
            }
            
            #modelProviderLabel {
                color: #cccccc;
            }
            
            #detailSectionHeader {
                color: #4CAF50;
                font-size: 12px;
                margin-top: 5px;
            }
            
            #detailSectionContent {
                color: #cccccc;
                background-color: #3a3a3a;
                border-radius: 3px;
                padding: 5px;
            }
            
            #placeholderLabel {
                color: #888888;
                font-style: italic;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #45a049;
            }
            
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
            
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            
            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #555555;
                border-bottom: none;
            }
            
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            
            QTabBar::tab:hover {
                background-color: #505050;
            }
        """)
    
    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(self.rect())
    
    def accept(self):
        """Save settings and accept dialog"""
        # Validate selection
        if not self.current_model:
            QMessageBox.warning(
                self,
                "No Model Selected",
                "Please select a model to continue."
            )
            return
        
        # Save settings
        self.config.set('llm', 'provider', self.current_provider)
        self.config.set('llm', 'model', self.current_model)
        self.config.set('llm', 'temperature', str(self.temperature_slider.value() / 100.0))
        self.config.set('llm', 'max_tokens', str(self.max_tokens_spin.value()))
        self.config.save()
        
        # Track model usage
        asyncio.create_task(
            self.repository.track_model_usage(self.current_model, self.current_provider)
        )
        
        super().accept()
    
    def closeEvent(self, event):
        """Handle close event"""
        # Clean up
        if hasattr(self, 'repository'):
            asyncio.create_task(self.repository.cache.cache.close())
        
        super().closeEvent(event)