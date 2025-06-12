#!/usr/bin/env python3
# WRAPD: Theme Manager for handling application themes

import os
import logging
from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

class ThemeManager:
    """Theme manager for WRAPD application"""
    
    def __init__(self, config_manager):
        """Initialize the theme manager
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = logging.getLogger("wrapd.theme")
        
        # Available themes
        self.themes = {
            'system': self._apply_system_theme,
            'dark': self._apply_dark_theme,
            'light': self._apply_light_theme,
            'dracula': self._apply_dracula_theme,
            'nord': self._apply_nord_theme,
            'solarized_light': self._apply_solarized_light_theme,
            'solarized_dark': self._apply_solarized_dark_theme,
            'monokai': self._apply_monokai_theme,
            'warp_glass': self._apply_warp_glass_theme,
            
            # Wu-Tang Clan / Killa Bee themes
            'wutang_dark': self._apply_css_theme,
            'wutang_light': self._apply_css_theme,
            'wutang_pastel': self._apply_css_theme,
            'wutang_contrast': self._apply_css_theme,
            
            # Teenage Mutant Ninja Turtles themes
            'tmnt_dark': self._apply_css_theme,
            'tmnt_light': self._apply_css_theme,
            'tmnt_pastel': self._apply_css_theme,
            'tmnt_contrast': self._apply_css_theme,
            
            # Rocko's Modern Life themes
            'rocko_dark': self._apply_css_theme,
            'rocko_light': self._apply_css_theme,
            'rocko_pastel': self._apply_css_theme,
            'rocko_contrast': self._apply_css_theme,
            
            # Sesame Street themes
            'sesame_dark': self._apply_css_theme,
            'sesame_light': self._apply_css_theme,
            'sesame_pastel': self._apply_css_theme,
            'sesame_contrast': self._apply_css_theme,
            
            # Nine Inch Nails themes
            'nin_dark': self._apply_css_theme,
            'nin_light': self._apply_css_theme,
            'nin_pastel': self._apply_css_theme,
            'nin_contrast': self._apply_css_theme,
            
            'custom': self._apply_custom_theme,
        }
        
        # Theme display names for UI
        self.theme_names = {
            'system': 'System',
            'dark': 'Dark',
            'light': 'Light',
            'dracula': 'Dracula',
            'nord': 'Nord',
            'solarized_light': 'Solarized Light',
            'solarized_dark': 'Solarized Dark',
            'monokai': 'Monokai',
            'warp_glass': 'Warp Glass',
            
            'wutang_dark': 'Wu-Tang (Dark)',
            'wutang_light': 'Wu-Tang (Light)',
            'wutang_pastel': 'Wu-Tang (Pastel)',
            'wutang_contrast': 'Wu-Tang (Contrast)',
            
            'tmnt_dark': 'TMNT (Dark)',
            'tmnt_light': 'TMNT (Light)',
            'tmnt_pastel': 'TMNT (Pastel)',
            'tmnt_contrast': 'TMNT (Contrast)',
            
            'rocko_dark': 'Rocko (Dark)',
            'rocko_light': 'Rocko (Light)',
            'rocko_pastel': 'Rocko (Pastel)',
            'rocko_contrast': 'Rocko (Contrast)',
            
            'sesame_dark': 'Sesame Street (Dark)',
            'sesame_light': 'Sesame Street (Light)',
            'sesame_pastel': 'Sesame Street (Pastel)',
            'sesame_contrast': 'Sesame Street (Contrast)',
            
            'nin_dark': 'Nine Inch Nails (Dark)',
            'nin_light': 'Nine Inch Nails (Light)',
            'nin_pastel': 'Nine Inch Nails (Pastel)',
            'nin_contrast': 'Nine Inch Nails (Contrast)',
            
            'custom': 'Custom',
        }
    
    def apply_theme(self, theme_name, window=None):
        """Apply a theme to the application
        
        Args:
            theme_name (str): Name of the theme to apply
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Check if theme exists
        if theme_name not in self.themes:
            self.logger.warning(f"Theme '{theme_name}' not found, falling back to dark theme")
            theme_name = 'dark'
        
        # Store current theme name
        self._current_theme = theme_name
        
        # Apply the theme
        if theme_name in ['wutang_dark', 'wutang_light', 'wutang_pastel', 'wutang_contrast',
                         'tmnt_dark', 'tmnt_light', 'tmnt_pastel', 'tmnt_contrast',
                         'rocko_dark', 'rocko_light', 'rocko_pastel', 'rocko_contrast',
                         'sesame_dark', 'sesame_light', 'sesame_pastel', 'sesame_contrast',
                         'nin_dark', 'nin_light', 'nin_pastel', 'nin_contrast']:
            self._apply_css_theme(window, theme_name)
        else:
            self.themes[theme_name](window)
        
        # Log theme change
        self.logger.info(f"Applied theme: {theme_name}")
    
    def get_available_themes(self):
        """Get a dictionary of available themes with display names
        
        Returns:
            dict: Dictionary mapping theme IDs to display names
        """
        return self.theme_names.copy()
    
    def _get_theme_path(self, theme_name):
        """Get the path to a theme CSS file
        
        Args:
            theme_name (str): Name of the theme
        
        Returns:
            str: Path to the theme CSS file
        """
        # Get the application directory
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        theme_path = os.path.join(app_dir, 'resources', 'themes', f'{theme_name}.css')
        return theme_path
    
    def _apply_css_theme(self, window=None, theme_name=None):
        """Apply a CSS theme from file
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
            theme_name (str, optional): Name of the theme to apply
        """
        # If theme_name is not provided, use the current theme
        if not theme_name:
            theme_name = getattr(self, '_current_theme', self.config.get('appearance', 'theme', 'dark'))
        
        # Get theme file path
        theme_path = self._get_theme_path(theme_name)
        
        # Check if theme file exists
        if not os.path.exists(theme_path):
            self.logger.warning(f"Theme file not found: {theme_path}")
            self._apply_dark_theme(window)  # Fallback to dark theme
            return
        
        try:
            # Read CSS file
            with open(theme_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            
            # Apply stylesheet
            app = QApplication.instance()
            app.setStyleSheet(stylesheet)
            
            # Set fusion style for better appearance
            app.setStyle("Fusion")
            
            # Update watermark colors for the current theme
            if window and hasattr(window, 'watermark_frame'):
                self._update_watermark_theme(window, theme_name)
                
        except Exception as e:
            self.logger.error(f"Failed to apply CSS theme '{theme_name}': {str(e)}")
            self._apply_dark_theme(window)  # Fallback to dark theme
    
    def _update_watermark_theme(self, window, theme_name):
        """Update watermark styling based on current theme
        
        Args:
            window (QMainWindow): Main window containing watermark
            theme_name (str): Name of the current theme
        """
        if not hasattr(window, 'logo_label') or not hasattr(window, 'tagline_label'):
            return
        
        # Define theme-specific watermark colors
        watermark_styles = {
            'wutang_dark': ('rgba(255, 215, 0, 0.2)', 'rgba(255, 215, 0, 0.15)'),
            'wutang_light': ('rgba(139, 69, 19, 0.2)', 'rgba(139, 69, 19, 0.15)'),
            'wutang_pastel': ('rgba(139, 115, 85, 0.2)', 'rgba(139, 115, 85, 0.15)'),
            'wutang_contrast': ('rgba(255, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.2)'),
            
            'tmnt_dark': ('rgba(124, 252, 0, 0.2)', 'rgba(124, 252, 0, 0.15)'),
            'tmnt_light': ('rgba(45, 90, 45, 0.2)', 'rgba(45, 90, 45, 0.15)'),
            'tmnt_pastel': ('rgba(74, 124, 89, 0.2)', 'rgba(74, 124, 89, 0.15)'),
            'tmnt_contrast': ('rgba(0, 255, 0, 0.3)', 'rgba(0, 255, 0, 0.2)'),
            
            'rocko_dark': ('rgba(255, 107, 53, 0.25)', 'rgba(255, 107, 53, 0.2)'),
            'rocko_light': ('rgba(255, 69, 0, 0.25)', 'rgba(255, 69, 0, 0.2)'),
            'rocko_pastel': ('rgba(255, 140, 105, 0.2)', 'rgba(255, 140, 105, 0.15)'),
            'rocko_contrast': ('rgba(255, 0, 102, 0.35)', 'rgba(255, 0, 102, 0.25)'),
            
            'sesame_dark': ('rgba(255, 193, 7, 0.25)', 'rgba(255, 193, 7, 0.2)'),
            'sesame_light': ('rgba(255, 152, 0, 0.3)', 'rgba(255, 152, 0, 0.25)'),
            'sesame_pastel': ('rgba(255, 183, 77, 0.2)', 'rgba(255, 183, 77, 0.15)'),
            'sesame_contrast': ('rgba(255, 235, 59, 0.4)', 'rgba(255, 235, 59, 0.3)'),
            
            'nin_dark': ('rgba(255, 140, 0, 0.3)', 'rgba(255, 140, 0, 0.2)'),
            'nin_light': ('rgba(139, 0, 0, 0.3)', 'rgba(139, 0, 0, 0.2)'),
            'nin_pastel': ('rgba(184, 134, 11, 0.25)', 'rgba(184, 134, 11, 0.2)'),
            'nin_contrast': ('rgba(255, 0, 0, 0.4)', 'rgba(255, 0, 0, 0.3)'),
        }
        
        # Get colors for current theme
        if theme_name in watermark_styles:
            logo_color, tagline_color = watermark_styles[theme_name]
        else:
            # Default colors
            logo_color, tagline_color = 'rgba(255, 255, 255, 0.15)', 'rgba(255, 255, 255, 0.1)'
        
        # Update watermark styles
        window.logo_label.setStyleSheet(f"""
            QLabel {{
                color: {logo_color};
                background: transparent;
                border: none;
                font-weight: bold;
                font-family: 'Courier', monospace;
            }}
        """)
        
        window.tagline_label.setStyleSheet(f"""
            QLabel {{
                color: {tagline_color};
                background: transparent;
                border: none;
                font-size: 8px;
                font-style: italic;
            }}
        """)
    
    def _apply_system_theme(self, window=None):
        """Apply the system theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        app = QApplication.instance()
        app.setStyle(app.style().objectName())
        app.setPalette(app.style().standardPalette())
    
    def _apply_dark_theme(self, window=None):
        """Apply the dark theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create dark palette
        palette = QPalette()
        
        # Set colors
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
    
    def _apply_light_theme(self, window=None):
        """Apply the light theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create light palette
        palette = QPalette()
        
        # Set colors
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
    
    def _apply_dracula_theme(self, window=None):
        """Apply the Dracula theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create Dracula palette
        palette = QPalette()
        
        # Dracula colors
        background = QColor(40, 42, 54)
        foreground = QColor(248, 248, 242)
        selection = QColor(68, 71, 90)
        comment = QColor(98, 114, 164)
        cyan = QColor(139, 233, 253)
        green = QColor(80, 250, 123)
        orange = QColor(255, 184, 108)
        pink = QColor(255, 121, 198)
        purple = QColor(189, 147, 249)
        red = QColor(255, 85, 85)
        yellow = QColor(241, 250, 140)
        
        # Set colors
        palette.setColor(QPalette.Window, background)
        palette.setColor(QPalette.WindowText, foreground)
        palette.setColor(QPalette.Base, QColor(21, 22, 30))
        palette.setColor(QPalette.AlternateBase, background)
        palette.setColor(QPalette.ToolTipBase, background)
        palette.setColor(QPalette.ToolTipText, foreground)
        palette.setColor(QPalette.Text, foreground)
        palette.setColor(QPalette.Button, background)
        palette.setColor(QPalette.ButtonText, foreground)
        palette.setColor(QPalette.BrightText, red)
        palette.setColor(QPalette.Link, cyan)
        palette.setColor(QPalette.Highlight, purple)
        palette.setColor(QPalette.HighlightedText, foreground)
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
    
    def _apply_nord_theme(self, window=None):
        """Apply the Nord theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create Nord palette
        palette = QPalette()
        
        # Nord colors
        polar_night_1 = QColor(46, 52, 64)  # nord0
        polar_night_2 = QColor(59, 66, 82)  # nord1
        polar_night_3 = QColor(67, 76, 94)  # nord2
        polar_night_4 = QColor(76, 86, 106)  # nord3
        snow_storm_1 = QColor(216, 222, 233)  # nord4
        snow_storm_2 = QColor(229, 233, 240)  # nord5
        snow_storm_3 = QColor(236, 239, 244)  # nord6
        frost_1 = QColor(143, 188, 187)  # nord7
        frost_2 = QColor(136, 192, 208)  # nord8
        frost_3 = QColor(129, 161, 193)  # nord9
        frost_4 = QColor(94, 129, 172)  # nord10
        aurora_red = QColor(191, 97, 106)  # nord11
        aurora_orange = QColor(208, 135, 112)  # nord12
        aurora_yellow = QColor(235, 203, 139)  # nord13
        aurora_green = QColor(163, 190, 140)  # nord14
        aurora_purple = QColor(180, 142, 173)  # nord15
        
        # Set colors
        palette.setColor(QPalette.Window, polar_night_1)
        palette.setColor(QPalette.WindowText, snow_storm_3)
        palette.setColor(QPalette.Base, polar_night_2)
        palette.setColor(QPalette.AlternateBase, polar_night_3)
        palette.setColor(QPalette.ToolTipBase, polar_night_3)
        palette.setColor(QPalette.ToolTipText, snow_storm_3)
        palette.setColor(QPalette.Text, snow_storm_3)
        palette.setColor(QPalette.Button, polar_night_2)
        palette.setColor(QPalette.ButtonText, snow_storm_3)
        palette.setColor(QPalette.BrightText, aurora_red)
        palette.setColor(QPalette.Link, frost_2)
        palette.setColor(QPalette.Highlight, frost_3)
        palette.setColor(QPalette.HighlightedText, snow_storm_3)
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
    
    def _apply_solarized_light_theme(self, window=None):
        """Apply the Solarized Light theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create Solarized Light palette
        palette = QPalette()
        
        # Solarized colors
        base03 = QColor(0, 43, 54)
        base02 = QColor(7, 54, 66)
        base01 = QColor(88, 110, 117)
        base00 = QColor(101, 123, 131)
        base0 = QColor(131, 148, 150)
        base1 = QColor(147, 161, 161)
        base2 = QColor(238, 232, 213)
        base3 = QColor(253, 246, 227)
        yellow = QColor(181, 137, 0)
        orange = QColor(203, 75, 22)
        red = QColor(220, 50, 47)
        magenta = QColor(211, 54, 130)
        violet = QColor(108, 113, 196)
        blue = QColor(38, 139, 210)
        cyan = QColor(42, 161, 152)
        green = QColor(133, 153, 0)
        
        # Set colors (light theme)
        palette.setColor(QPalette.Window, base3)
        palette.setColor(QPalette.WindowText, base00)
        palette.setColor(QPalette.Base, base3)
        palette.setColor(QPalette.AlternateBase, base2)
        palette.setColor(QPalette.ToolTipBase, base3)
        palette.setColor(QPalette.ToolTipText, base00)
        palette.setColor(QPalette.Text, base00)
        palette.setColor(QPalette.Button, base2)
        palette.setColor(QPalette.ButtonText, base00)
        palette.setColor(QPalette.BrightText, red)
        palette.setColor(QPalette.Link, blue)
        palette.setColor(QPalette.Highlight, blue)
        palette.setColor(QPalette.HighlightedText, base3)
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
    
    def _apply_solarized_dark_theme(self, window=None):
        """Apply the Solarized Dark theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create Solarized Dark palette
        palette = QPalette()
        
        # Solarized colors
        base03 = QColor(0, 43, 54)
        base02 = QColor(7, 54, 66)
        base01 = QColor(88, 110, 117)
        base00 = QColor(101, 123, 131)
        base0 = QColor(131, 148, 150)
        base1 = QColor(147, 161, 161)
        base2 = QColor(238, 232, 213)
        base3 = QColor(253, 246, 227)
        yellow = QColor(181, 137, 0)
        orange = QColor(203, 75, 22)
        red = QColor(220, 50, 47)
        magenta = QColor(211, 54, 130)
        violet = QColor(108, 113, 196)
        blue = QColor(38, 139, 210)
        cyan = QColor(42, 161, 152)
        green = QColor(133, 153, 0)
        
        # Set colors (dark theme)
        palette.setColor(QPalette.Window, base03)
        palette.setColor(QPalette.WindowText, base0)
        palette.setColor(QPalette.Base, base02)
        palette.setColor(QPalette.AlternateBase, base01)
        palette.setColor(QPalette.ToolTipBase, base02)
        palette.setColor(QPalette.ToolTipText, base0)
        palette.setColor(QPalette.Text, base0)
        palette.setColor(QPalette.Button, base02)
        palette.setColor(QPalette.ButtonText, base0)
        palette.setColor(QPalette.BrightText, red)
        palette.setColor(QPalette.Link, blue)
        palette.setColor(QPalette.Highlight, blue)
        palette.setColor(QPalette.HighlightedText, base03)
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
    
    def _apply_monokai_theme(self, window=None):
        """Apply the Monokai theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create Monokai palette
        palette = QPalette()
        
        # Monokai colors
        background = QColor(39, 40, 34)
        foreground = QColor(248, 248, 242)
        comment = QColor(117, 113, 94)
        red = QColor(249, 38, 114)
        orange = QColor(253, 151, 31)
        yellow = QColor(230, 219, 116)
        green = QColor(166, 226, 46)
        blue = QColor(102, 217, 239)
        purple = QColor(174, 129, 255)
        
        # Set colors
        palette.setColor(QPalette.Window, background)
        palette.setColor(QPalette.WindowText, foreground)
        palette.setColor(QPalette.Base, QColor(23, 24, 20))
        palette.setColor(QPalette.AlternateBase, background)
        palette.setColor(QPalette.ToolTipBase, background)
        palette.setColor(QPalette.ToolTipText, foreground)
        palette.setColor(QPalette.Text, foreground)
        palette.setColor(QPalette.Button, background)
        palette.setColor(QPalette.ButtonText, foreground)
        palette.setColor(QPalette.BrightText, red)
        palette.setColor(QPalette.Link, blue)
        palette.setColor(QPalette.Highlight, purple)
        palette.setColor(QPalette.HighlightedText, foreground)
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
    
    def _apply_warp_glass_theme(self, window=None):
        """Apply the Warp Glass theme
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Create Warp Glass palette
        palette = QPalette()
        
        # Warp Glass colors
        background = QColor(20, 20, 30)
        foreground = QColor(230, 230, 240)
        selection = QColor(100, 120, 200, 128)
        highlight = QColor(80, 100, 180)
        link = QColor(100, 150, 255)
        
        # Set colors
        palette.setColor(QPalette.Window, background)
        palette.setColor(QPalette.WindowText, foreground)
        palette.setColor(QPalette.Base, QColor(15, 15, 25))
        palette.setColor(QPalette.AlternateBase, QColor(30, 30, 45))
        palette.setColor(QPalette.ToolTipBase, QColor(15, 15, 25))
        palette.setColor(QPalette.ToolTipText, foreground)
        palette.setColor(QPalette.Text, foreground)
        palette.setColor(QPalette.Button, QColor(40, 40, 60))
        palette.setColor(QPalette.ButtonText, foreground)
        palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, link)
        palette.setColor(QPalette.Highlight, highlight)
        palette.setColor(QPalette.HighlightedText, foreground)
        
        # Apply palette
        app = QApplication.instance()
        app.setPalette(palette)
        
        # Set fusion style for better appearance
        app.setStyle("Fusion")
        
        # Apply custom stylesheet
        theme_path = self.config.get_theme_path('warp_glass')
        if os.path.exists(theme_path):
            with open(theme_path, 'r') as file:
                stylesheet = file.read()
                app = QApplication.instance()
                app.setStyleSheet(stylesheet)
        else:
            self.logger.warning(f"Warp Glass theme file not found: {theme_path}")
            self._apply_dark_theme(window)  # Fallback to dark theme
    
    def _apply_custom_theme(self, window=None):
        """Apply a custom theme from CSS file
        
        Args:
            window (QMainWindow, optional): Main window to apply theme to
        """
        # Get custom CSS file path
        css_path = self.config.get('appearance', 'custom_css_path', '')
        
        # Check if file exists
        if not css_path or not os.path.exists(css_path):
            self.logger.warning(f"Custom theme file not found: {css_path}")
            self._apply_dark_theme(window)
            return
        
        try:
            # Read CSS file
            with open(css_path, 'r') as f:
                stylesheet = f.read()
            
            # Apply stylesheet
            app = QApplication.instance()
            app.setStyleSheet(stylesheet)
            
            # Set fusion style for better appearance
            app.setStyle("Fusion")
        except Exception as e:
            self.logger.error(f"Failed to apply custom theme: {str(e)}")
            self._apply_dark_theme(window)
