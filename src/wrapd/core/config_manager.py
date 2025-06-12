#!/usr/bin/env python3
"""
WRAPD: Comprehensive configuration management system with secure keyring integration,
environment variable support, and validation
"""

import os
import sys
import json
import configparser
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass, asdict
from enum import Enum
import keyring
import platform

from ..utils.error_handling import ConfigurationError, WRAPDError


class ModelProvider(Enum):
    """Supported model providers"""
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    FALLBACK = "fallback"


@dataclass
class ModelConfig:
    """Configuration for AI models"""
    provider: ModelProvider
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class TerminalConfig:
    """Terminal configuration"""
    shell: str = "auto"  # auto, bash, zsh, fish, cmd, powershell
    working_directory: str = "~"
    history_size: int = 1000
    enable_syntax_highlighting: bool = True
    enable_auto_suggestions: bool = True
    confirm_dangerous_commands: bool = True
    dangerous_command_patterns: List[str] = None
    
    def __post_init__(self):
        if self.dangerous_command_patterns is None:
            self.dangerous_command_patterns = [
                r"rm\s+-rf\s+/",
                r"sudo\s+rm\s+-rf",
                r"dd\s+if=.*of=/dev/",
                r"mkfs\.",
                r"format\s+[c-z]:",
                r"del\s+/[sqf]",
                r"shutdown",
                r"reboot",
                r"halt"
            ]


@dataclass
class UIConfig:
    """User interface configuration"""
    theme: str = "default"
    font_family: str = "Consolas, Monaco, 'Courier New'"
    font_size: int = 12
    window_width: int = 1200
    window_height: int = 800
    window_x: int = -1  # -1 means center
    window_y: int = -1  # -1 means center
    maximized: bool = False
    opacity: float = 1.0
    enable_transparency: bool = False
    show_line_numbers: bool = True
    show_minimap: bool = False
    auto_save_layout: bool = True


@dataclass
class AIConfig:
    """AI integration configuration"""
    primary_model: ModelConfig = None
    fallback_models: List[ModelConfig] = None
    enable_command_suggestions: bool = True
    enable_error_analysis: bool = True
    enable_auto_completion: bool = True
    context_length: int = 10  # Number of previous commands to include
    response_timeout: int = 30
    retry_attempts: int = 3
    enable_streaming: bool = True
    
    def __post_init__(self):
        if self.primary_model is None:
            # Default to Ollama with gemma2:2b
            self.primary_model = ModelConfig(
                provider=ModelProvider.OLLAMA,
                model_id="gemma2:2b",
                base_url="http://localhost:11434"
            )
        
        if self.fallback_models is None:
            self.fallback_models = []


@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_keyring: bool = True
    keyring_service: str = "wrapd-terminal"
    encrypt_config: bool = False
    api_key_storage: str = "keyring"  # keyring, env, config
    session_timeout: int = 3600  # 1 hour
    auto_lock: bool = False
    require_auth: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    enable_file_logging: bool = True
    enable_console_logging: bool = True
    enable_structured_logging: bool = False
    enable_performance_logging: bool = True
    log_file_max_size: int = 10 * 1024 * 1024  # 10MB
    log_file_backup_count: int = 10
    log_retention_days: int = 30


class ConfigManager:
    """
    Comprehensive configuration management system for WRAPD with:
    - Secure API key storage via keyring
    - Environment variable support
    - Configuration validation
    - Auto-migration and backup
    - Real-time configuration updates
    """
    
    def __init__(self, config_file: Union[str, Path], logger):
        self.config_file = Path(config_file)
        self.logger = logger
        
        # Configuration objects
        self.model_config: ModelConfig = None
        self.terminal_config: TerminalConfig = None
        self.ui_config: UIConfig = None
        self.ai_config: AIConfig = None
        self.security_config: SecurityConfig = None
        self.logging_config: LoggingConfig = None
        
        # Internal state
        self.config_parser = configparser.ConfigParser()
        self.config_version = "2.0"
        self.callbacks: List[callable] = []
        
        # Platform-specific defaults
        self._platform_defaults = self._get_platform_defaults()
        
        # Initialize configuration
        self._initialize()
        
        self.logger.info("ConfigManager initialized successfully")
    
    def _initialize(self) -> None:
        """Initialize configuration system"""
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load or create configuration
            if self.config_file.exists():
                self.load_config()
            else:
                self.create_default_config()
                self.save_config()
            
            # Validate configuration
            self.validate_config()
            
            # Setup keyring if enabled
            if self.security_config.enable_keyring:
                self._setup_keyring()
            
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize configuration: {e}")
    
    def _get_platform_defaults(self) -> Dict[str, Any]:
        """Get platform-specific default values"""
        system = platform.system().lower()
        
        defaults = {
            "shell": "bash",
            "font_family": "Consolas, Monaco, 'Courier New'",
            "config_dir": str(Path.home() / ".wrapd")
        }
        
        if system == "windows":
            defaults.update({
                "shell": "cmd",
                "font_family": "Consolas, 'Courier New'"
            })
        elif system == "darwin":  # macOS
            defaults.update({
                "shell": "zsh",
                "font_family": "SF Mono, Monaco, Menlo"
            })
        
        return defaults
    
    def create_default_config(self) -> None:
        """Create default configuration"""
        self.logger.info("Creating default configuration")
        
        # Create default configurations
        self.terminal_config = TerminalConfig(
            shell=self._platform_defaults["shell"]
        )
        
        self.ui_config = UIConfig(
            font_family=self._platform_defaults["font_family"]
        )
        
        self.ai_config = AIConfig()
        self.security_config = SecurityConfig()
        self.logging_config = LoggingConfig()
        
        # Set primary model configuration
        self.model_config = self.ai_config.primary_model
    
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            self.logger.info(f"Loading configuration from {self.config_file}")
            
            # Read config file
            self.config_parser.read(self.config_file, encoding='utf-8')
            
            # Check version and migrate if necessary
            file_version = self.config_parser.get('general', 'version', fallback='1.0')
            if file_version != self.config_version:
                self._migrate_config(file_version)
            
            # Load each configuration section
            self._load_terminal_config()
            self._load_ui_config()
            self._load_ai_config()
            self._load_security_config()
            self._load_logging_config()
            
            # Load primary model config
            self.model_config = self.ai_config.primary_model
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Fall back to defaults
            self.create_default_config()
    
    def _load_terminal_config(self) -> None:
        """Load terminal configuration section"""
        section = 'terminal'
        if not self.config_parser.has_section(section):
            self.terminal_config = TerminalConfig()
            return
        
        try:
            # Load dangerous command patterns from JSON
            patterns_json = self.config_parser.get(section, 'dangerous_command_patterns', 
                                                 fallback='[]')
            patterns = json.loads(patterns_json)
            
            self.terminal_config = TerminalConfig(
                shell=self.config_parser.get(section, 'shell', fallback='auto'),
                working_directory=self.config_parser.get(section, 'working_directory', 
                                                       fallback='~'),
                history_size=self.config_parser.getint(section, 'history_size', fallback=1000),
                enable_syntax_highlighting=self.config_parser.getboolean(
                    section, 'enable_syntax_highlighting', fallback=True),
                enable_auto_suggestions=self.config_parser.getboolean(
                    section, 'enable_auto_suggestions', fallback=True),
                confirm_dangerous_commands=self.config_parser.getboolean(
                    section, 'confirm_dangerous_commands', fallback=True),
                dangerous_command_patterns=patterns
            )
        except Exception as e:
            self.logger.warning(f"Error loading terminal config: {e}, using defaults")
            self.terminal_config = TerminalConfig()
    
    def _load_ui_config(self) -> None:
        """Load UI configuration section"""
        section = 'ui'
        if not self.config_parser.has_section(section):
            self.ui_config = UIConfig()
            return
        
        try:
            self.ui_config = UIConfig(
                theme=self.config_parser.get(section, 'theme', fallback='default'),
                font_family=self.config_parser.get(section, 'font_family', 
                                                 fallback=self._platform_defaults["font_family"]),
                font_size=self.config_parser.getint(section, 'font_size', fallback=12),
                window_width=self.config_parser.getint(section, 'window_width', fallback=1200),
                window_height=self.config_parser.getint(section, 'window_height', fallback=800),
                window_x=self.config_parser.getint(section, 'window_x', fallback=-1),
                window_y=self.config_parser.getint(section, 'window_y', fallback=-1),
                maximized=self.config_parser.getboolean(section, 'maximized', fallback=False),
                opacity=self.config_parser.getfloat(section, 'opacity', fallback=1.0),
                enable_transparency=self.config_parser.getboolean(
                    section, 'enable_transparency', fallback=False),
                show_line_numbers=self.config_parser.getboolean(
                    section, 'show_line_numbers', fallback=True),
                show_minimap=self.config_parser.getboolean(section, 'show_minimap', fallback=False),
                auto_save_layout=self.config_parser.getboolean(
                    section, 'auto_save_layout', fallback=True)
            )
        except Exception as e:
            self.logger.warning(f"Error loading UI config: {e}, using defaults")
            self.ui_config = UIConfig()
    
    def _load_ai_config(self) -> None:
        """Load AI configuration section"""
        section = 'ai'
        if not self.config_parser.has_section(section):
            self.ai_config = AIConfig()
            return
        
        try:
            # Load primary model
            primary_model = self._load_model_config('primary_model')
            
            # Load fallback models
            fallback_models = []
            fallback_count = self.config_parser.getint(section, 'fallback_models_count', fallback=0)
            for i in range(fallback_count):
                fallback_model = self._load_model_config(f'fallback_model_{i}')
                if fallback_model:
                    fallback_models.append(fallback_model)
            
            self.ai_config = AIConfig(
                primary_model=primary_model,
                fallback_models=fallback_models,
                enable_command_suggestions=self.config_parser.getboolean(
                    section, 'enable_command_suggestions', fallback=True),
                enable_error_analysis=self.config_parser.getboolean(
                    section, 'enable_error_analysis', fallback=True),
                enable_auto_completion=self.config_parser.getboolean(
                    section, 'enable_auto_completion', fallback=True),
                context_length=self.config_parser.getint(section, 'context_length', fallback=10),
                response_timeout=self.config_parser.getint(section, 'response_timeout', fallback=30),
                retry_attempts=self.config_parser.getint(section, 'retry_attempts', fallback=3),
                enable_streaming=self.config_parser.getboolean(
                    section, 'enable_streaming', fallback=True)
            )
        except Exception as e:
            self.logger.warning(f"Error loading AI config: {e}, using defaults")
            self.ai_config = AIConfig()
    
    def _load_model_config(self, model_section: str) -> Optional[ModelConfig]:
        """Load model configuration from a specific section"""
        if not self.config_parser.has_section(model_section):
            return None
        
        try:
            provider_str = self.config_parser.get(model_section, 'provider', fallback='ollama')
            provider = ModelProvider(provider_str)
            
            model_id = self.config_parser.get(model_section, 'model_id', fallback='gemma2:2b')
            
            # Get API key securely
            api_key = None
            if provider == ModelProvider.OPENROUTER:
                api_key = self.get_secure_value('openrouter_api_key')
            
            return ModelConfig(
                provider=provider,
                model_id=model_id,
                api_key=api_key,
                base_url=self.config_parser.get(model_section, 'base_url', 
                                              fallback='http://localhost:11434'),
                max_tokens=self.config_parser.getint(model_section, 'max_tokens', fallback=4096),
                temperature=self.config_parser.getfloat(model_section, 'temperature', fallback=0.7),
                timeout=self.config_parser.getint(model_section, 'timeout', fallback=30)
            )
        except Exception as e:
            self.logger.warning(f"Error loading model config {model_section}: {e}")
            return None
    
    def _load_security_config(self) -> None:
        """Load security configuration section"""
        section = 'security'
        if not self.config_parser.has_section(section):
            self.security_config = SecurityConfig()
            return
        
        try:
            self.security_config = SecurityConfig(
                enable_keyring=self.config_parser.getboolean(section, 'enable_keyring', fallback=True),
                keyring_service=self.config_parser.get(section, 'keyring_service', 
                                                     fallback='wrapd-terminal'),
                encrypt_config=self.config_parser.getboolean(section, 'encrypt_config', fallback=False),
                api_key_storage=self.config_parser.get(section, 'api_key_storage', fallback='keyring'),
                session_timeout=self.config_parser.getint(section, 'session_timeout', fallback=3600),
                auto_lock=self.config_parser.getboolean(section, 'auto_lock', fallback=False),
                require_auth=self.config_parser.getboolean(section, 'require_auth', fallback=False)
            )
        except Exception as e:
            self.logger.warning(f"Error loading security config: {e}, using defaults")
            self.security_config = SecurityConfig()
    
    def _load_logging_config(self) -> None:
        """Load logging configuration section"""
        section = 'logging'
        if not self.config_parser.has_section(section):
            self.logging_config = LoggingConfig()
            return
        
        try:
            self.logging_config = LoggingConfig(
                level=self.config_parser.get(section, 'level', fallback='INFO'),
                enable_file_logging=self.config_parser.getboolean(
                    section, 'enable_file_logging', fallback=True),
                enable_console_logging=self.config_parser.getboolean(
                    section, 'enable_console_logging', fallback=True),
                enable_structured_logging=self.config_parser.getboolean(
                    section, 'enable_structured_logging', fallback=False),
                enable_performance_logging=self.config_parser.getboolean(
                    section, 'enable_performance_logging', fallback=True),
                log_file_max_size=self.config_parser.getint(
                    section, 'log_file_max_size', fallback=10*1024*1024),
                log_file_backup_count=self.config_parser.getint(
                    section, 'log_file_backup_count', fallback=10),
                log_retention_days=self.config_parser.getint(
                    section, 'log_retention_days', fallback=30)
            )
        except Exception as e:
            self.logger.warning(f"Error loading logging config: {e}, using defaults")
            self.logging_config = LoggingConfig()
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            self.logger.info(f"Saving configuration to {self.config_file}")
            
            # Clear existing configuration
            self.config_parser.clear()
            
            # Save general section
            self.config_parser.add_section('general')
            self.config_parser.set('general', 'version', self.config_version)
            self.config_parser.set('general', 'created_by', 'WRAPD Terminal v2.0')
            
            # Save each configuration section
            self._save_terminal_config()
            self._save_ui_config()
            self._save_ai_config()
            self._save_security_config()
            self._save_logging_config()
            
            # Write to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config_parser.write(f)
            
            # Notify callbacks
            self._notify_config_changed()
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def _save_terminal_config(self) -> None:
        """Save terminal configuration section"""
        section = 'terminal'
        self.config_parser.add_section(section)
        
        config = self.terminal_config
        self.config_parser.set(section, 'shell', config.shell)
        self.config_parser.set(section, 'working_directory', config.working_directory)
        self.config_parser.set(section, 'history_size', str(config.history_size))
        self.config_parser.set(section, 'enable_syntax_highlighting', 
                              str(config.enable_syntax_highlighting))
        self.config_parser.set(section, 'enable_auto_suggestions', 
                              str(config.enable_auto_suggestions))
        self.config_parser.set(section, 'confirm_dangerous_commands', 
                              str(config.confirm_dangerous_commands))
        self.config_parser.set(section, 'dangerous_command_patterns', 
                              json.dumps(config.dangerous_command_patterns))
    
    def _save_ui_config(self) -> None:
        """Save UI configuration section"""
        section = 'ui'
        self.config_parser.add_section(section)
        
        config = self.ui_config
        self.config_parser.set(section, 'theme', config.theme)
        self.config_parser.set(section, 'font_family', config.font_family)
        self.config_parser.set(section, 'font_size', str(config.font_size))
        self.config_parser.set(section, 'window_width', str(config.window_width))
        self.config_parser.set(section, 'window_height', str(config.window_height))
        self.config_parser.set(section, 'window_x', str(config.window_x))
        self.config_parser.set(section, 'window_y', str(config.window_y))
        self.config_parser.set(section, 'maximized', str(config.maximized))
        self.config_parser.set(section, 'opacity', str(config.opacity))
        self.config_parser.set(section, 'enable_transparency', str(config.enable_transparency))
        self.config_parser.set(section, 'show_line_numbers', str(config.show_line_numbers))
        self.config_parser.set(section, 'show_minimap', str(config.show_minimap))
        self.config_parser.set(section, 'auto_save_layout', str(config.auto_save_layout))
    
    def _save_ai_config(self) -> None:
        """Save AI configuration section"""
        section = 'ai'
        self.config_parser.add_section(section)
        
        config = self.ai_config
        self.config_parser.set(section, 'enable_command_suggestions', 
                              str(config.enable_command_suggestions))
        self.config_parser.set(section, 'enable_error_analysis', str(config.enable_error_analysis))
        self.config_parser.set(section, 'enable_auto_completion', str(config.enable_auto_completion))
        self.config_parser.set(section, 'context_length', str(config.context_length))
        self.config_parser.set(section, 'response_timeout', str(config.response_timeout))
        self.config_parser.set(section, 'retry_attempts', str(config.retry_attempts))
        self.config_parser.set(section, 'enable_streaming', str(config.enable_streaming))
        
        # Save primary model
        if config.primary_model:
            self._save_model_config('primary_model', config.primary_model)
        
        # Save fallback models
        self.config_parser.set(section, 'fallback_models_count', str(len(config.fallback_models)))
        for i, fallback_model in enumerate(config.fallback_models):
            self._save_model_config(f'fallback_model_{i}', fallback_model)
    
    def _save_model_config(self, section_name: str, model_config: ModelConfig) -> None:
        """Save model configuration to a specific section"""
        self.config_parser.add_section(section_name)
        
        self.config_parser.set(section_name, 'provider', model_config.provider.value)
        self.config_parser.set(section_name, 'model_id', model_config.model_id)
        if model_config.base_url:
            self.config_parser.set(section_name, 'base_url', model_config.base_url)
        self.config_parser.set(section_name, 'max_tokens', str(model_config.max_tokens))
        self.config_parser.set(section_name, 'temperature', str(model_config.temperature))
        self.config_parser.set(section_name, 'timeout', str(model_config.timeout))
        
        # Save API key securely
        if model_config.api_key and model_config.provider == ModelProvider.OPENROUTER:
            self.set_secure_value('openrouter_api_key', model_config.api_key)
    
    def _save_security_config(self) -> None:
        """Save security configuration section"""
        section = 'security'
        self.config_parser.add_section(section)
        
        config = self.security_config
        self.config_parser.set(section, 'enable_keyring', str(config.enable_keyring))
        self.config_parser.set(section, 'keyring_service', config.keyring_service)
        self.config_parser.set(section, 'encrypt_config', str(config.encrypt_config))
        self.config_parser.set(section, 'api_key_storage', config.api_key_storage)
        self.config_parser.set(section, 'session_timeout', str(config.session_timeout))
        self.config_parser.set(section, 'auto_lock', str(config.auto_lock))
        self.config_parser.set(section, 'require_auth', str(config.require_auth))
    
    def _save_logging_config(self) -> None:
        """Save logging configuration section"""
        section = 'logging'
        self.config_parser.add_section(section)
        
        config = self.logging_config
        self.config_parser.set(section, 'level', config.level)
        self.config_parser.set(section, 'enable_file_logging', str(config.enable_file_logging))
        self.config_parser.set(section, 'enable_console_logging', str(config.enable_console_logging))
        self.config_parser.set(section, 'enable_structured_logging', str(config.enable_structured_logging))
        self.config_parser.set(section, 'enable_performance_logging', str(config.enable_performance_logging))
        self.config_parser.set(section, 'log_file_max_size', str(config.log_file_max_size))
        self.config_parser.set(section, 'log_file_backup_count', str(config.log_file_backup_count))
        self.config_parser.set(section, 'log_retention_days', str(config.log_retention_days))
    
    def validate_config(self) -> None:
        """Validate current configuration"""
        try:
            # Validate terminal config
            if self.terminal_config.history_size < 10:
                raise ConfigurationError("Terminal history size must be at least 10")
            
            # Validate UI config
            if self.ui_config.font_size < 8 or self.ui_config.font_size > 72:
                raise ConfigurationError("Font size must be between 8 and 72")
            
            if self.ui_config.opacity < 0.1 or self.ui_config.opacity > 1.0:
                raise ConfigurationError("Opacity must be between 0.1 and 1.0")
            
            # Validate AI config
            if self.ai_config.context_length < 1 or self.ai_config.context_length > 100:
                raise ConfigurationError("Context length must be between 1 and 100")
            
            if self.ai_config.response_timeout < 5 or self.ai_config.response_timeout > 300:
                raise ConfigurationError("Response timeout must be between 5 and 300 seconds")
            
            # Validate model config
            if not self.ai_config.primary_model:
                raise ConfigurationError("Primary model configuration is required")
            
            self.logger.debug("Configuration validation passed")
            
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
    
    def _setup_keyring(self) -> None:
        """Setup keyring for secure storage"""
        try:
            # Test keyring functionality
            test_key = "wrapd_test_key"
            test_value = "test_value"
            
            keyring.set_password(self.security_config.keyring_service, test_key, test_value)
            stored_value = keyring.get_password(self.security_config.keyring_service, test_key)
            
            if stored_value != test_value:
                raise ConfigurationError("Keyring test failed")
            
            # Clean up test
            keyring.delete_password(self.security_config.keyring_service, test_key)
            
            self.logger.info("Keyring setup successful")
            
        except Exception as e:
            self.logger.warning(f"Keyring setup failed: {e}, falling back to environment variables")
            self.security_config.enable_keyring = False
    
    def _migrate_config(self, from_version: str) -> None:
        """Migrate configuration from older version"""
        self.logger.info(f"Migrating configuration from version {from_version} to {self.config_version}")
        
        # Create backup
        backup_file = self.config_file.with_suffix(f'.backup.{from_version}')
        if self.config_file.exists():
            self.config_file.rename(backup_file)
            self.logger.info(f"Configuration backup created: {backup_file}")
        
        # Perform migration (implementation depends on version differences)
        # For now, we'll just create new config with defaults
        self.create_default_config()
    
    def set_secure_value(self, key: str, value: str) -> None:
        """Store a value securely using keyring or environment variables"""
        try:
            if self.security_config.enable_keyring:
                keyring.set_password(self.security_config.keyring_service, key, value)
                self.logger.debug(f"Stored secure value for {key} in keyring")
            else:
                # Fall back to environment variable
                os.environ[f"WRAPD_{key.upper()}"] = value
                self.logger.debug(f"Stored secure value for {key} in environment")
        except Exception as e:
            raise ConfigurationError(f"Failed to store secure value {key}: {e}")
    
    def get_secure_value(self, key: str) -> Optional[str]:
        """Retrieve a value securely from keyring or environment variables"""
        try:
            if self.security_config.enable_keyring:
                value = keyring.get_password(self.security_config.keyring_service, key)
                if value:
                    return value
            
            # Fall back to environment variable
            return os.environ.get(f"WRAPD_{key.upper()}")
            
        except Exception as e:
            self.logger.warning(f"Failed to retrieve secure value {key}: {e}")
            return None
    
    def delete_secure_value(self, key: str) -> None:
        """Delete a secure value"""
        try:
            if self.security_config.enable_keyring:
                keyring.delete_password(self.security_config.keyring_service, key)
            
            # Also try environment variable
            env_key = f"WRAPD_{key.upper()}"
            if env_key in os.environ:
                del os.environ[env_key]
                
        except Exception as e:
            self.logger.warning(f"Failed to delete secure value {key}: {e}")
    
    def update_model_config(self, provider: ModelProvider, model_id: str, 
                           api_key: Optional[str] = None, **kwargs) -> None:
        """Update primary model configuration"""
        self.model_config = ModelConfig(
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            **kwargs
        )
        self.ai_config.primary_model = self.model_config
        
        # Save API key securely if provided
        if api_key and provider == ModelProvider.OPENROUTER:
            self.set_secure_value('openrouter_api_key', api_key)
        
        self.save_config()
        self.logger.info(f"Updated primary model to {provider.value}:{model_id}")
    
    def add_fallback_model(self, provider: ModelProvider, model_id: str, 
                          api_key: Optional[str] = None, **kwargs) -> None:
        """Add a fallback model"""
        fallback_model = ModelConfig(
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            **kwargs
        )
        
        self.ai_config.fallback_models.append(fallback_model)
        self.save_config()
        self.logger.info(f"Added fallback model {provider.value}:{model_id}")
    
    def get_all_models(self) -> List[ModelConfig]:
        """Get all configured models (primary + fallbacks)"""
        models = [self.ai_config.primary_model]
        models.extend(self.ai_config.fallback_models)
        return [model for model in models if model is not None]
    
    def register_callback(self, callback: callable) -> None:
        """Register callback for configuration changes"""
        self.callbacks.append(callback)
    
    def _notify_config_changed(self) -> None:
        """Notify all callbacks of configuration changes"""
        for callback in self.callbacks:
            try:
                callback(self)
            except Exception as e:
                self.logger.error(f"Error in config callback: {e}")
    
    def export_config(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            'terminal': asdict(self.terminal_config),
            'ui': asdict(self.ui_config),
            'ai': {
                **asdict(self.ai_config),
                'primary_model': asdict(self.ai_config.primary_model) if self.ai_config.primary_model else None,
                'fallback_models': [asdict(model) for model in self.ai_config.fallback_models]
            },
            'security': asdict(self.security_config),
            'logging': asdict(self.logging_config)
        }
    
    def import_config(self, config_data: Dict[str, Any]) -> None:
        """Import configuration from dictionary"""
        try:
            # Import each section
            if 'terminal' in config_data:
                self.terminal_config = TerminalConfig(**config_data['terminal'])
            
            if 'ui' in config_data:
                self.ui_config = UIConfig(**config_data['ui'])
            
            if 'ai' in config_data:
                ai_data = config_data['ai']
                
                # Import primary model
                primary_model = None
                if 'primary_model' in ai_data and ai_data['primary_model']:
                    primary_model_data = ai_data['primary_model']
                    primary_model_data['provider'] = ModelProvider(primary_model_data['provider'])
                    primary_model = ModelConfig(**primary_model_data)
                
                # Import fallback models
                fallback_models = []
                if 'fallback_models' in ai_data:
                    for fallback_data in ai_data['fallback_models']:
                        fallback_data['provider'] = ModelProvider(fallback_data['provider'])
                        fallback_models.append(ModelConfig(**fallback_data))
                
                # Create AI config
                ai_config_data = {k: v for k, v in ai_data.items() 
                                if k not in ['primary_model', 'fallback_models']}
                self.ai_config = AIConfig(
                    primary_model=primary_model,
                    fallback_models=fallback_models,
                    **ai_config_data
                )
            
            if 'security' in config_data:
                self.security_config = SecurityConfig(**config_data['security'])
            
            if 'logging' in config_data:
                self.logging_config = LoggingConfig(**config_data['logging'])
            
            # Update model config reference
            self.model_config = self.ai_config.primary_model
            
            # Validate and save
            self.validate_config()
            self.save_config()
            
            self.logger.info("Configuration imported successfully")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to import configuration: {e}")
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self.logger.info("Resetting configuration to defaults")
        
        # Create backup
        backup_file = self.config_file.with_suffix('.backup.reset')
        if self.config_file.exists():
            self.config_file.rename(backup_file)
        
        # Create default configuration
        self.create_default_config()
        self.save_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            'config_file': str(self.config_file),
            'config_version': self.config_version,
            'keyring_enabled': self.security_config.enable_keyring,
            'primary_model': f"{self.model_config.provider.value}:{self.model_config.model_id}" if self.model_config else None,
            'fallback_models_count': len(self.ai_config.fallback_models),
            'theme': self.ui_config.theme,
            'shell': self.terminal_config.shell
        }