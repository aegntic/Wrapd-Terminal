#!/usr/bin/env python3
# WRAPD: Model Card Widget

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QToolButton, QSizePolicy
)
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt, pyqtSignal, QRect

from ..models.model_info import ModelInfo

class ModelCard(QFrame):
    """Rich model information card widget"""
    
    modelSelected = pyqtSignal(ModelInfo)
    favoriteToggled = pyqtSignal(ModelInfo, bool)
    
    def __init__(self, model_info: ModelInfo, parent=None):
        super().__init__(parent)
        
        self.model = model_info
        self.is_selected = False
        
        self.setObjectName("modelCard")
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self._create_ui()
        self._apply_style()
        
        # Make clickable
        self.setCursor(Qt.PointingHandCursor)
    
    def _create_ui(self):
        """Create the card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # Header with name and favorite button
        header_layout = QHBoxLayout()
        
        # Model name
        self.name_label = QLabel(self.model.get_display_name())
        self.name_label.setObjectName("cardModelName")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setWordWrap(True)
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        # Favorite button
        self.favorite_btn = QToolButton()
        self.favorite_btn.setText("★" if self.model.is_favorite else "☆")
        self.favorite_btn.setObjectName("cardFavoriteBtn")
        self.favorite_btn.setMaximumSize(24, 24)
        self.favorite_btn.clicked.connect(self._toggle_favorite)
        header_layout.addWidget(self.favorite_btn)
        
        layout.addLayout(header_layout)
        
        # Provider and status
        status_layout = QHBoxLayout()
        
        self.provider_label = QLabel(self.model.provider.title())
        self.provider_label.setObjectName("cardProvider")
        status_layout.addWidget(self.provider_label)
        
        status_layout.addStretch()
        
        # Availability indicator
        self.status_indicator = QLabel("●")
        if self.model.performance.availability_score >= 0.9:
            self.status_indicator.setStyleSheet("color: #4CAF50;")  # Green
            self.status_indicator.setToolTip("Online")
        elif self.model.performance.availability_score >= 0.5:
            self.status_indicator.setStyleSheet("color: #FF9800;")  # Orange
            self.status_indicator.setToolTip("Degraded")
        else:
            self.status_indicator.setStyleSheet("color: #F44336;")  # Red
            self.status_indicator.setToolTip("Offline")
        
        status_layout.addWidget(self.status_indicator)
        
        layout.addLayout(status_layout)
        
        # Key specifications
        specs_layout = QVBoxLayout()
        specs_layout.setSpacing(4)
        
        # Context length
        context_text = f"Context: {self.model.capabilities.context_length:,} tokens"
        context_label = QLabel(context_text)
        context_label.setObjectName("cardSpec")
        specs_layout.addWidget(context_label)
        
        # Pricing
        if self.model.pricing.input_price_per_1m > 0:
            price_text = f"Cost: {self.model.get_cost_per_1k_tokens()}/1K tokens"
        else:
            price_text = "Cost: Free"
        
        price_label = QLabel(price_text)
        price_label.setObjectName("cardSpec")
        specs_layout.addWidget(price_label)
        
        # Performance
        if self.model.performance.response_time_avg > 0:
            perf_text = f"Speed: {self.model.performance.response_time_avg:.1f}s"
        else:
            perf_text = "Speed: Unknown"
        
        perf_label = QLabel(perf_text)
        perf_label.setObjectName("cardSpec")
        specs_layout.addWidget(perf_label)
        
        layout.addLayout(specs_layout)
        
        # Capabilities badges
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(4)
        
        if self.model.capabilities.supports_images:
            image_badge = self._create_badge("Images", "#2196F3")
            badges_layout.addWidget(image_badge)
        
        if self.model.capabilities.supports_function_calling:
            func_badge = self._create_badge("Functions", "#9C27B0")
            badges_layout.addWidget(func_badge)
        
        if self.model.provider == 'ollama' and self.model.local_info:
            if self.model.local_info.is_installed:
                local_badge = self._create_badge("Installed", "#4CAF50")
            else:
                local_badge = self._create_badge("Available", "#FF9800")
            badges_layout.addWidget(local_badge)
        
        badges_layout.addStretch()
        
        # User rating
        if self.model.user_rating:
            rating_text = "★" * self.model.user_rating
            rating_label = QLabel(rating_text)
            rating_label.setObjectName("cardRating")
            rating_label.setStyleSheet("color: #FFD700;")
            badges_layout.addWidget(rating_label)
        
        layout.addLayout(badges_layout)
        
        layout.addStretch()
    
    def _create_badge(self, text: str, color: str) -> QLabel:
        """Create a capability badge"""
        badge = QLabel(text)
        badge.setObjectName("cardBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setMinimumWidth(60)
        badge.setMaximumHeight(20)
        badge.setStyleSheet(f"""
            QLabel#cardBadge {{
                background-color: {color};
                color: white;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }}
        """)
        return badge
    
    def _toggle_favorite(self):
        """Toggle favorite status"""
        self.model.is_favorite = not self.model.is_favorite
        self.favorite_btn.setText("★" if self.model.is_favorite else "☆")
        self.favoriteToggled.emit(self.model, self.model.is_favorite)
    
    def _apply_style(self):
        """Apply card styling"""
        self.setStyleSheet("""
            QFrame#modelCard {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 8px;
                margin: 2px;
            }
            
            QFrame#modelCard:hover {
                border-color: #4CAF50;
                background-color: #404040;
            }
            
            QLabel#cardModelName {
                color: #ffffff;
                font-weight: bold;
            }
            
            QLabel#cardProvider {
                color: #4CAF50;
                font-size: 10px;
                font-weight: bold;
            }
            
            QLabel#cardSpec {
                color: #cccccc;
                font-size: 10px;
            }
            
            QLabel#cardRating {
                font-size: 12px;
            }
            
            QToolButton#cardFavoriteBtn {
                border: none;
                background: transparent;
                color: #FFD700;
                font-size: 16px;
            }
            
            QToolButton#cardFavoriteBtn:hover {
                background-color: rgba(255, 215, 0, 0.2);
                border-radius: 12px;
            }
        """)
    
    def set_selected(self, selected: bool):
        """Set card selection state"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet(self.styleSheet() + """
                QFrame#modelCard {
                    border: 2px solid #4CAF50;
                    background-color: #454545;
                }
            """)
        else:
            self._apply_style()
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.LeftButton:
            self.modelSelected.emit(self.model)
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event for additional visual effects"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw selection indicator
        if self.is_selected:
            pen = QPen(QColor("#4CAF50"), 3)
            painter.setPen(pen)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        
        # Draw performance indicator bar
        if self.model.performance.availability_score > 0:
            bar_rect = QRect(8, self.height() - 4, self.width() - 16, 2)
            
            # Background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#555555")))
            painter.drawRect(bar_rect)
            
            # Performance bar
            perf_width = int(bar_rect.width() * self.model.performance.availability_score)
            perf_rect = QRect(bar_rect.x(), bar_rect.y(), perf_width, bar_rect.height())
            
            if self.model.performance.availability_score >= 0.9:
                color = QColor("#4CAF50")  # Green
            elif self.model.performance.availability_score >= 0.7:
                color = QColor("#FF9800")  # Orange
            else:
                color = QColor("#F44336")  # Red
            
            painter.setBrush(QBrush(color))
            painter.drawRect(perf_rect)