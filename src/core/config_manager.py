#!/usr/bin/env python3
# WRAPD: Configuration Manager

import os
import json
import configparser
import keyring
from pathlib import Path

class ConfigManager:
    """Configuration management for WRAPD application"""
    
    def __init__(self, config_path):
        """Initialize the configuration manager
        
        Args:
            config_path (str): Path to the configuration file
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        
        # If config file doesn't exist, create default configuration
        if not os.path.exists(config_path):
            self._create_default_config()
        else:
            self.config.read(config_path)
    
    def _create_default_config(self):
        """Create default configuration settings"""
        # General settings
        self.config['general'] = {
            'first_run': 'true',
            'auto_update_check': 'true',
            'startup_notification': 'true',
        }
        
        # Appearance settings
        self.config['appearance'] = {
            'theme': 'wutang_dark',  # Default to Wu-Tang dark theme
            'opacity': '0.95',
            'font_family': 'Consolas, Menlo, monospace',
            'font_size': '12',
            'cursor_style': 'block',
            'show_line_numbers': 'true',
            'custom_css_path': '',
        }
        
        # Terminal settings
        self.config['terminal'] = {
            'buffer_size': '10000',
            'scrollback_lines': '5000',
            'cursor_blink': 'true',
            'bell': 'visual',
            'word_wrap': 'true',
            'save_history': 'true',
            'history_size': '1000',
            'clear_selection_after_copy': 'false',
        }
        
        # LLM settings
        self.config['llm'] = {
            'provider': 'openrouter',
            'model': 'anthropic/claude-3-haiku',
            'temperature': '0.1',
            'max_tokens': '256',
            'cache_responses': 'true',
            'cache_size': '500',
            'prompt_prefix': '',
            'prompt_suffix': '',
        }
        
        # API keys (stored in keyring, not in config file)
        self.config['api'] = {
            'openrouter_user': '',
        }
        
        # Shortcuts settings
        self.config['shortcuts'] = {
            'new_tab': 'Ctrl+T',
            'close_tab': 'Ctrl+W',
            'next_tab': 'Ctrl+Tab',
            'previous_tab': 'Ctrl+Shift+Tab',
            'clear_terminal': 'Ctrl+L',
            'toggle_transparency': 'Ctrl+Shift+T',
            'increase_font_size': 'Ctrl++',
            'decrease_font_size': 'Ctrl+-',
            'reset_font_size': 'Ctrl+0',
        }
        
        # Available themes
        self.config['themes'] = {
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
        
        # Save the default configuration
        self.save()
    
    def save(self):
        """Save configuration to file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
    
    def get(self, section, option, default=None):
        """Get a configuration value
        
        Args:
            section (str): Configuration section
            option (str): Configuration option
            default: Default value if section or option doesn't exist
        
        Returns:
            The configuration value or default
        """
        try:
            return self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def get_int(self, section, option, default=None):
        """Get an integer configuration value"""
        try:
            return self.config.getint(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_float(self, section, option, default=None):
        """Get a float configuration value"""
        try:
            return self.config.getfloat(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_boolean(self, section, option, default=None):
        """Get a boolean configuration value"""
        try:
            return self.config.getboolean(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def set(self, section, option, value):
        """Set a configuration value
        
        Args:
            section (str): Configuration section
            option (str): Configuration option
            value: Value to set
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, option, str(value))
        self.save()
    
    def set_api_key(self, service, key):
        """Set an API key in the secure storage
        
        Args:
            service (str): Service name (e.g., 'openrouter')
            key (str): API key value
        """
        username = self.get('api', f'{service}_user', '')
        if not username:
            # Generate a username based on the current timestamp
            import time
            username = f'wrapd_{service}_{int(time.time())}'
            self.set('api', f'{service}_user', username)
        
        keyring.set_password(f'wrapd_{service}', username, key)
    
    def get_api_key(self, service):
        """Get an API key from secure storage
        
        Args:
            service (str): Service name (e.g., 'openrouter')
        
        Returns:
            str: API key or None if not found
        """
        username = self.get('api', f'{service}_user', '')
        if not username:
            return None
        
        try:
            return keyring.get_password(f'wrapd_{service}', username)
        except:
            return None
    
    def get_theme_path(self, theme_name):
        """Get the path to a theme CSS file
        
        Args:
            theme_name (str): Name of the theme
        
        Returns:
            str: Path to the theme CSS file
        """
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        themes_dir = os.path.join(app_dir, 'resources', 'themes')
        
        if theme_name == 'custom':
            custom_path = self.get('appearance', 'custom_css_path', '')
            if custom_path and os.path.exists(custom_path):
                return custom_path
        
        theme_file = f'{theme_name}.css'
        theme_path = os.path.join(themes_dir, theme_file)
        
        if os.path.exists(theme_path):
            return theme_path
        
        # Return default theme if requested theme doesn't exist
        return os.path.join(themes_dir, 'dark.css')
    
    def get_available_themes(self):
        """Get a list of available themes
        
        Returns:
            dict: Dictionary of theme names and labels
        """
        themes = {}
        for option in self.config.options('themes'):
            themes[option] = self.config.get('themes', option)
        return themes
