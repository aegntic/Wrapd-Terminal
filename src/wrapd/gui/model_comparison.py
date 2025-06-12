#!/usr/bin/env python3
# WRAPD: Model Comparison Widget

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QLabel, QPushButton, QHeaderView,
    QScrollArea, QFrame, QGroupBox, QTextEdit, QSplitter
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, pyqtSignal

from ..models.model_info import ModelInfo

class ModelComparisonWidget(QWidget):
    """Widget for comparing multiple models side by side"""
    
    modelRemoved = pyqtSignal(ModelInfo)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.models = []
        self.max_models = 4  # Maximum number of models to compare
        
        self._create_ui()
        self._apply_style()
    
    def _create_ui(self):
        """Create the comparison UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Model Comparison")
        title_label.setObjectName("comparisonTitle")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Clear all button
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        header_layout.addWidget(self.clear_btn)
        
        layout.addLayout(header_layout)
        
        # Instructions
        self.instructions_label = QLabel(
            "Add models to compare their specifications, pricing, and performance side by side."
        )
        self.instructions_label.setObjectName("instructionsLabel")
        self.instructions_label.setWordWrap(True)
        layout.addWidget(self.instructions_label)
        
        # Splitter for comparison table and details
        splitter = QSplitter(Qt.Vertical)
        
        # Comparison table
        self.comparison_table = QTableWidget()
        self.comparison_table.setAlternatingRowColors(True)
        self.comparison_table.verticalHeader().setVisible(True)
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.comparison_table)
        
        # Detailed comparison text
        details_group = QGroupBox("Detailed Analysis")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)
        
        splitter.addWidget(details_group)
        
        # Set splitter proportions
        splitter.setSizes([400, 200])
        
        layout.addWidget(splitter)
        
        # Initially hide the widget
        self._update_visibility()
    
    def add_model(self, model: ModelInfo):
        """Add a model to the comparison"""
        if len(self.models) >= self.max_models:
            # Remove oldest model if at capacity
            self.models.pop(0)
        
        # Check if model is already in comparison
        for existing_model in self.models:
            if existing_model.id == model.id and existing_model.provider == model.provider:
                return  # Already in comparison
        
        self.models.append(model)
        self._update_comparison_table()
        self._update_detailed_analysis()
        self._update_visibility()
    
    def remove_model(self, model: ModelInfo):
        """Remove a model from comparison"""
        self.models = [m for m in self.models if not (m.id == model.id and m.provider == model.provider)]
        self._update_comparison_table()
        self._update_detailed_analysis()
        self._update_visibility()
        self.modelRemoved.emit(model)
    
    def clear_all(self):
        """Clear all models from comparison"""
        self.models.clear()
        self._update_comparison_table()
        self._update_detailed_analysis()
        self._update_visibility()
    
    def _update_comparison_table(self):
        """Update the comparison table with current models"""
        if not self.models:
            self.comparison_table.setRowCount(0)
            self.comparison_table.setColumnCount(0)
            return
        
        # Set up table structure
        self.comparison_table.setColumnCount(len(self.models))
        
        # Set column headers (model names)
        headers = []
        for model in self.models:
            header = f"{model.get_display_name()}\n({model.provider})"
            headers.append(header)
        self.comparison_table.setHorizontalHeaderLabels(headers)
        
        # Define comparison categories
        categories = [
            ("Basic Info", [
                ("Name", lambda m: m.get_display_name()),
                ("Provider", lambda m: m.provider.title()),
                ("Organization", lambda m: m.organization or "N/A"),
                ("Version", lambda m: m.version or "N/A"),
                ("Category", lambda m: m.category or "N/A"),
            ]),
            ("Capabilities", [
                ("Context Length", lambda m: f"{m.capabilities.context_length:,} tokens"),
                ("Max Output", lambda m: f"{m.capabilities.max_output_tokens:,} tokens"),
                ("Supports Images", lambda m: "✓" if m.capabilities.supports_images else "✗"),
                ("Function Calling", lambda m: "✓" if m.capabilities.supports_function_calling else "✗"),
                ("Streaming", lambda m: "✓" if m.capabilities.supports_streaming else "✗"),
                ("JSON Mode", lambda m: "✓" if m.capabilities.supports_json_mode else "✗"),
            ]),
            ("Pricing", [
                ("Input Cost", lambda m: f"${m.pricing.input_price_per_1m:.6f}/1M" if m.pricing.input_price_per_1m > 0 else "Free"),
                ("Output Cost", lambda m: f"${m.pricing.output_price_per_1m:.6f}/1M" if m.pricing.output_price_per_1m > 0 else "Free"),
                ("Cost per 1K", lambda m: m.get_cost_per_1k_tokens()),
            ]),
            ("Performance", [
                ("Availability", lambda m: f"{m.performance.availability_score:.1%}"),
                ("Reliability", lambda m: f"{m.performance.reliability_score:.1%}"),
                ("Avg Response Time", lambda m: f"{m.performance.response_time_avg:.2f}s" if m.performance.response_time_avg > 0 else "Unknown"),
                ("Popularity Score", lambda m: str(m.performance.popularity_score)),
                ("Performance Rating", lambda m: m.get_performance_rating()),
            ]),
            ("User Data", [
                ("Favorite", lambda m: "★" if m.is_favorite else "☆"),
                ("Usage Count", lambda m: str(m.usage_count)),
                ("User Rating", lambda m: "★" * m.user_rating if m.user_rating else "Not rated"),
                ("Last Used", lambda m: m.last_used.strftime("%Y-%m-%d") if m.last_used else "Never"),
            ]),
        ]
        
        # Add local model info if any model has it
        if any(m.local_info for m in self.models):
            categories.append(("Local Model Info", [
                ("Size", lambda m: f"{m.local_info.size_gb:.1f} GB" if m.local_info else "N/A"),
                ("Memory Usage", lambda m: f"{m.local_info.memory_usage_gb:.1f} GB" if m.local_info else "N/A"),
                ("Installed", lambda m: "✓" if m.local_info and m.local_info.is_installed else "✗"),
                ("Quantization", lambda m: m.local_info.quantization if m.local_info else "N/A"),
            ]))
        
        # Calculate total rows
        total_rows = sum(len(items) + 1 for _, items in categories)  # +1 for category header
        self.comparison_table.setRowCount(total_rows)
        
        # Populate table
        current_row = 0
        
        for category_name, items in categories:
            # Category header row
            category_item = QTableWidgetItem(category_name)
            category_item.setFont(QFont("", -1, QFont.Bold))
            category_item.setBackground(QColor("#4CAF50"))
            category_item.setForeground(QColor("#FFFFFF"))
            self.comparison_table.setVerticalHeaderItem(current_row, category_item)
            
            # Merge cells for category header
            for col in range(len(self.models)):
                item = QTableWidgetItem("")
                item.setBackground(QColor("#4CAF50"))
                self.comparison_table.setItem(current_row, col, item)
            
            current_row += 1
            
            # Data rows
            for item_name, item_func in items:
                # Set row header
                row_item = QTableWidgetItem(item_name)
                self.comparison_table.setVerticalHeaderItem(current_row, row_item)
                
                # Set data for each model
                for col, model in enumerate(self.models):
                    try:
                        value = item_func(model)
                        cell_item = QTableWidgetItem(str(value))
                        
                        # Color code some values
                        if item_name in ["Supports Images", "Function Calling", "Streaming", "JSON Mode", "Installed"]:
                            if value == "✓":
                                cell_item.setForeground(QColor("#4CAF50"))
                            else:
                                cell_item.setForeground(QColor("#F44336"))
                        elif item_name == "Favorite":
                            if value == "★":
                                cell_item.setForeground(QColor("#FFD700"))
                        elif item_name in ["Cost per 1K"]:
                            if "Free" in value:
                                cell_item.setForeground(QColor("#4CAF50"))
                            else:
                                cell_item.setForeground(QColor("#FF9800"))
                        
                        self.comparison_table.setItem(current_row, col, cell_item)
                        
                    except Exception as e:
                        error_item = QTableWidgetItem("Error")
                        error_item.setForeground(QColor("#F44336"))
                        self.comparison_table.setItem(current_row, col, error_item)
                
                current_row += 1
        
        # Auto-resize columns
        header = self.comparison_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Auto-resize rows
        self.comparison_table.resizeRowsToContents()
    
    def _update_detailed_analysis(self):
        """Update detailed analysis text"""
        if not self.models:
            self.details_text.clear()
            return
        
        analysis = []
        
        # Summary
        analysis.append("## Comparison Summary")
        analysis.append(f"Comparing {len(self.models)} models:")
        for i, model in enumerate(self.models, 1):
            analysis.append(f"{i}. {model.get_display_name()} ({model.provider})")
        analysis.append("")
        
        # Cost analysis
        analysis.append("## Cost Analysis")
        free_models = [m for m in self.models if m.pricing.input_price_per_1m == 0]
        paid_models = [m for m in self.models if m.pricing.input_price_per_1m > 0]
        
        if free_models:
            analysis.append(f"Free models: {', '.join(m.name for m in free_models)}")
        
        if paid_models:
            cheapest = min(paid_models, key=lambda m: m.pricing.input_price_per_1m)
            most_expensive = max(paid_models, key=lambda m: m.pricing.input_price_per_1m)
            
            analysis.append(f"Cheapest: {cheapest.name} ({cheapest.get_cost_per_1k_tokens()}/1K tokens)")
            analysis.append(f"Most expensive: {most_expensive.name} ({most_expensive.get_cost_per_1k_tokens()}/1K tokens)")
        
        analysis.append("")
        
        # Capability analysis
        analysis.append("## Capability Analysis")
        
        # Context length comparison
        max_context = max(self.models, key=lambda m: m.capabilities.context_length)
        min_context = min(self.models, key=lambda m: m.capabilities.context_length)
        
        analysis.append(f"Largest context: {max_context.name} ({max_context.capabilities.context_length:,} tokens)")
        analysis.append(f"Smallest context: {min_context.name} ({min_context.capabilities.context_length:,} tokens)")
        
        # Feature support
        image_models = [m for m in self.models if m.capabilities.supports_images]
        function_models = [m for m in self.models if m.capabilities.supports_function_calling]
        
        if image_models:
            analysis.append(f"Image support: {', '.join(m.name for m in image_models)}")
        
        if function_models:
            analysis.append(f"Function calling: {', '.join(m.name for m in function_models)}")
        
        analysis.append("")
        
        # Performance analysis
        analysis.append("## Performance Analysis")
        
        # Response time comparison (if available)
        models_with_times = [m for m in self.models if m.performance.response_time_avg > 0]
        if models_with_times:
            fastest = min(models_with_times, key=lambda m: m.performance.response_time_avg)
            slowest = max(models_with_times, key=lambda m: m.performance.response_time_avg)
            
            analysis.append(f"Fastest: {fastest.name} ({fastest.performance.response_time_avg:.2f}s)")
            analysis.append(f"Slowest: {slowest.name} ({slowest.performance.response_time_avg:.2f}s)")
        
        # Availability comparison
        most_available = max(self.models, key=lambda m: m.performance.availability_score)
        analysis.append(f"Most available: {most_available.name} ({most_available.performance.availability_score:.1%})")
        
        analysis.append("")
        
        # Recommendations
        analysis.append("## Recommendations")
        
        if free_models:
            best_free = max(free_models, key=lambda m: m.capabilities.context_length)
            analysis.append(f"🆓 Best free model: {best_free.name}")
        
        if paid_models:
            # Best value (capability per dollar)
            best_value = max(paid_models, key=lambda m: m.capabilities.context_length / max(m.pricing.input_price_per_1m, 0.000001))
            analysis.append(f"💰 Best value: {best_value.name}")
        
        # Most capable
        most_capable = max(self.models, key=lambda m: (
            m.capabilities.context_length +
            (50000 if m.capabilities.supports_images else 0) +
            (30000 if m.capabilities.supports_function_calling else 0)
        ))
        analysis.append(f"🚀 Most capable: {most_capable.name}")
        
        # User favorites
        favorites = [m for m in self.models if m.is_favorite]
        if favorites:
            analysis.append(f"⭐ Your favorites: {', '.join(m.name for m in favorites)}")
        
        self.details_text.setPlainText("\n".join(analysis))
    
    def _update_visibility(self):
        """Update widget visibility based on model count"""
        has_models = len(self.models) > 0
        self.comparison_table.setVisible(has_models)
        self.details_text.parent().setVisible(has_models)
        self.instructions_label.setVisible(not has_models)
        
        if has_models:
            self.clear_btn.setEnabled(True)
        else:
            self.clear_btn.setEnabled(False)
    
    def _apply_style(self):
        """Apply styling to the widget"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            QLabel#comparisonTitle {
                color: #ffffff;
                font-weight: bold;
            }
            
            QLabel#instructionsLabel {
                color: #cccccc;
                font-style: italic;
                padding: 20px;
                text-align: center;
            }
            
            QTableWidget {
                background-color: #3a3a3a;
                alternate-background-color: #404040;
                selection-background-color: #4CAF50;
                gridline-color: #555555;
                border: 1px solid #555555;
            }
            
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: #4CAF50;
            }
            
            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #555555;
                font-weight: bold;
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
            
            QTextEdit {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
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
        """)