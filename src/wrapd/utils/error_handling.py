#!/usr/bin/env python3
"""
WRAPD: Comprehensive error handling system with structured error management,
recovery strategies, and user-friendly error reporting
"""

import sys
import logging
import traceback
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from PyQt5.QtWidgets import QMessageBox, QWidget

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error category types"""
    SYSTEM = "system"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    USER_INPUT = "user_input"
    MODEL_SELECTION = "model_selection"
    TERMINAL = "terminal"
    GUI = "gui"
    THEME = "theme"
    API = "api"

@dataclass
class ErrorContext:
    """Context information for errors"""
    function_name: str
    module_name: str
    line_number: int
    timestamp: float
    thread_name: str
    user_action: Optional[str] = None
    system_state: Optional[Dict[str, Any]] = None

class WRAPDError(Exception):
    """Base exception class for all WRAPD errors"""
    
    def __init__(self, 
                 message: str, 
                 error_code: str = None, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 details: Dict[str, Any] = None,
                 recoverable: bool = True,
                 context: ErrorContext = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "WRAPD_ERROR"
        self.severity = severity
        self.category = category
        self.details = details or {}
        self.recoverable = recoverable
        self.context = context
        self.timestamp = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
            "context": asdict(self.context) if self.context else None
        }

class ConfigurationError(WRAPDError):
    """Configuration-related errors"""
    
    def __init__(self, message: str, config_key: str = None, config_file: str = None):
        super().__init__(
            message, 
            "CONFIG_ERROR", 
            ErrorSeverity.HIGH,
            ErrorCategory.CONFIGURATION
        )
        if config_key:
            self.details["config_key"] = config_key
        if config_file:
            self.details["config_file"] = config_file

class NetworkError(WRAPDError):
    """Network-related errors"""
    
    def __init__(self, message: str, url: str = None, status_code: int = None):
        super().__init__(
            message, 
            "NETWORK_ERROR", 
            ErrorSeverity.MEDIUM,
            ErrorCategory.NETWORK
        )
        if url:
            self.details["url"] = url
        if status_code:
            self.details["status_code"] = status_code

class TerminalError(WRAPDError):
    """Terminal operation errors"""
    
    def __init__(self, message: str, command: str = None, exit_code: int = None):
        super().__init__(
            message, 
            "TERMINAL_ERROR", 
            ErrorSeverity.MEDIUM,
            ErrorCategory.TERMINAL
        )
        if command:
            self.details["command"] = command
        if exit_code:
            self.details["exit_code"] = exit_code

class GUIError(WRAPDError):
    """GUI-related errors"""
    
    def __init__(self, message: str, widget_name: str = None, action: str = None):
        super().__init__(
            message, 
            "GUI_ERROR", 
            ErrorSeverity.LOW,
            ErrorCategory.GUI
        )
        if widget_name:
            self.details["widget_name"] = widget_name
        if action:
            self.details["action"] = action

class ThemeError(WRAPDError):
    """Theme-related errors"""
    
    def __init__(self, message: str, theme_name: str = None, theme_file: str = None):
        super().__init__(
            message, 
            "THEME_ERROR", 
            ErrorSeverity.LOW,
            ErrorCategory.THEME
        )
        if theme_name:
            self.details["theme_name"] = theme_name
        if theme_file:
            self.details["theme_file"] = theme_file

class ModelSelectionError(WRAPDError):
    """Base exception for model selection errors"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message, 
            error_code or "MODEL_SELECTION_ERROR", 
            ErrorSeverity.MEDIUM,
            ErrorCategory.MODEL_SELECTION,
            details
        )

class APIConnectionError(ModelSelectionError):
    """API connection failed"""
    
    def __init__(self, message: str, provider: str = None, status_code: int = None):
        details = {}
        if provider:
            details["provider"] = provider
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, "API_CONNECTION_ERROR", details)

class ModelNotAvailableError(ModelSelectionError):
    """Requested model is not available"""
    
    def __init__(self, message: str, model_id: str = None, provider: str = None):
        details = {}
        if model_id:
            details["model_id"] = model_id
        if provider:
            details["provider"] = provider
        super().__init__(message, "MODEL_NOT_AVAILABLE", details)

class RateLimitError(ModelSelectionError):
    """API rate limit exceeded"""
    
    def __init__(self, message: str, retry_after: int = None, provider: str = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        if provider:
            details["provider"] = provider
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)

class ModelInstallationError(ModelSelectionError):
    """Model installation failed"""
    
    def __init__(self, message: str, model_id: str = None, install_stage: str = None):
        details = {}
        if model_id:
            details["model_id"] = model_id
        if install_stage:
            details["install_stage"] = install_stage
        super().__init__(message, "MODEL_INSTALLATION_ERROR", details)

class CacheError(ModelSelectionError):
    """Cache operation failed"""
    
    def __init__(self, message: str, operation: str = None):
        details = {}
        if operation:
            details["operation"] = operation
        super().__init__(message, "CACHE_ERROR", details)

class ValidationError(ModelSelectionError):
    """Data validation failed"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(message, "VALIDATION_ERROR", details)

class ErrorHandler:
    """
    Comprehensive error handling system for WRAPD with GUI integration,
    recovery strategies, and detailed error tracking
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.lock = threading.Lock()
        
        # Error tracking
        self.error_counts: Dict[str, int] = {}
        self.recent_errors: List[Dict[str, Any]] = []
        self.error_trends: Dict[str, List[float]] = {}
        self.max_recent_errors = 100
        
        # Recovery handlers
        self.recovery_handlers: Dict[str, Callable] = {}
        self.error_callbacks: List[Callable] = []
        
        # GUI integration
        self.parent_widget: Optional[QWidget] = None
        self.show_gui_errors = True
        
        # Performance tracking
        self.start_time = time.time()
        
        self.logger.info("ErrorHandler initialized")
    
    def setup_global_exception_handler(self, parent_widget: QWidget = None) -> None:
        """Setup global exception handler for unhandled exceptions"""
        self.parent_widget = parent_widget
        
        # Store original handler
        self.original_excepthook = sys.excepthook
        
        # Set custom handler
        sys.excepthook = self._global_exception_handler
        
        self.logger.info("Global exception handler setup complete")
    
    def _global_exception_handler(self, exc_type, exc_value, exc_traceback) -> None:
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't handle keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Create error context
        tb = exc_traceback
        context = None
        if tb:
            context = ErrorContext(
                function_name=tb.tb_frame.f_code.co_name,
                module_name=tb.tb_frame.f_globals.get('__name__', 'unknown'),
                line_number=tb.tb_lineno,
                timestamp=time.time(),
                thread_name=threading.current_thread().name
            )
        
        # Create WRAPDError
        error = WRAPDError(
            message=f"Unhandled exception: {exc_value}",
            error_code="UNHANDLED_EXCEPTION",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM,
            recoverable=False,
            context=context
        )
        
        # Handle the error
        self.handle_error(error, show_user_dialog=True)
        
        # Log full traceback
        self.logger.critical(
            "Unhandled exception occurred",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    def handle_error(self, 
                    error: Exception, 
                    context: str = None,
                    show_user_dialog: bool = None,
                    attempt_recovery: bool = True) -> Dict[str, Any]:
        """
        Handle an error with comprehensive processing
        
        Args:
            error: The exception to handle
            context: Additional context information
            show_user_dialog: Whether to show user dialog (None = auto-decide)
            attempt_recovery: Whether to attempt automatic recovery
        
        Returns:
            Dictionary containing error information and recovery status
        """
        with self.lock:
            try:
                # Extract error information
                error_info = self._extract_error_info(error)
                
                # Add context
                if context:
                    error_info["context"] = context
                
                # Add current state
                error_info["system_state"] = self._get_system_state()
                
                # Log the error
                self._log_error(error, error_info)
                
                # Update statistics and trends
                self._update_statistics(error_info)
                self._update_trends(error_info)
                
                # Store recent error
                self._store_recent_error(error_info)
                
                # Attempt recovery if requested
                recovery_result = None
                if attempt_recovery and isinstance(error, WRAPDError) and error.recoverable:
                    recovery_result = self._attempt_recovery(error)
                    error_info["recovery_attempted"] = True
                    error_info["recovery_successful"] = recovery_result is not None
                    error_info["recovery_result"] = recovery_result
                
                # Show user dialog if appropriate
                if self._should_show_user_dialog(error, show_user_dialog):
                    self._show_user_error_dialog(error, error_info, recovery_result)
                
                # Notify callbacks
                self._notify_error_callbacks(error, error_info)
                
                return error_info
                
            except Exception as handler_error:
                # Error in error handler - log and return basic info
                self.logger.critical(f"Error in error handler: {handler_error}", exc_info=True)
                return {
                    "error_type": error.__class__.__name__,
                    "message": str(error),
                    "handler_error": str(handler_error)
                }
    
    def _extract_error_info(self, error: Exception) -> Dict[str, Any]:
        """Extract comprehensive information from an error"""
        if isinstance(error, WRAPDError):
            error_info = error.to_dict()
        else:
            # Extract context from traceback
            tb = traceback.extract_tb(error.__traceback__)
            context = None
            if tb:
                frame = tb[-1]  # Get the last frame
                context = ErrorContext(
                    function_name=frame.name,
                    module_name=frame.filename,
                    line_number=frame.lineno,
                    timestamp=time.time(),
                    thread_name=threading.current_thread().name
                )
            
            error_info = {
                "error_type": error.__class__.__name__,
                "message": str(error),
                "error_code": "UNKNOWN_ERROR",
                "severity": ErrorSeverity.MEDIUM.value,
                "category": ErrorCategory.SYSTEM.value,
                "details": {},
                "recoverable": True,
                "timestamp": time.time(),
                "context": asdict(context) if context else None
            }
        
        # Add traceback information
        error_info["traceback"] = traceback.format_exception(
            type(error), error, error.__traceback__
        )
        
        return error_info
    
    def _get_system_state(self) -> Dict[str, Any]:
        """Get current system state information"""
        try:
            import psutil
            return {
                "memory_usage": psutil.virtual_memory().percent,
                "cpu_usage": psutil.cpu_percent(),
                "thread_count": threading.active_count(),
                "uptime": time.time() - self.start_time
            }
        except Exception:
            return {"error": "Could not collect system state"}
    
    def _log_error(self, error: Exception, error_info: Dict[str, Any]) -> None:
        """Log error with appropriate level and formatting"""
        error_type = error_info.get("error_type", "Unknown")
        message = error_info.get("message", "Unknown error")
        severity = error_info.get("severity", "medium")
        context = error_info.get("context", "")
        
        log_message = f"{error_type}: {message}"
        if context:
            log_message += f" (Context: {context})"
        
        # Choose log level based on severity
        if severity == ErrorSeverity.LOW.value:
            self.logger.warning(log_message)
        elif severity == ErrorSeverity.MEDIUM.value:
            self.logger.error(log_message)
        elif severity == ErrorSeverity.HIGH.value:
            self.logger.error(log_message, exc_info=True)
        elif severity == ErrorSeverity.CRITICAL.value:
            self.logger.critical(log_message, exc_info=True)
        else:
            self.logger.error(log_message, exc_info=True)
    
    def _update_statistics(self, error_info: Dict[str, Any]) -> None:
        """Update error statistics"""
        error_code = error_info.get("error_code", "UNKNOWN_ERROR")
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1
    
    def _update_trends(self, error_info: Dict[str, Any]) -> None:
        """Update error trends for analysis"""
        error_code = error_info.get("error_code", "UNKNOWN_ERROR")
        timestamp = error_info.get("timestamp", time.time())
        
        if error_code not in self.error_trends:
            self.error_trends[error_code] = []
        
        self.error_trends[error_code].append(timestamp)
        
        # Keep only last 24 hours of trends
        cutoff = timestamp - (24 * 60 * 60)
        self.error_trends[error_code] = [
            t for t in self.error_trends[error_code] if t > cutoff
        ]
    
    def _store_recent_error(self, error_info: Dict[str, Any]) -> None:
        """Store error in recent errors list"""
        self.recent_errors.insert(0, error_info.copy())
        
        # Keep only recent errors
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[:self.max_recent_errors]
    
    def _should_show_user_dialog(self, error: Exception, show_user_dialog: bool = None) -> bool:
        """Determine if user dialog should be shown"""
        if show_user_dialog is not None:
            return show_user_dialog
        
        if not self.show_gui_errors or not self.parent_widget:
            return False
        
        # Show dialog for high/critical errors or non-recoverable errors
        if isinstance(error, WRAPDError):
            return (error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] or 
                   not error.recoverable)
        
        return True
    
    def _show_user_error_dialog(self, error: Exception, error_info: Dict[str, Any], 
                               recovery_result: Any = None) -> None:
        """Show user-friendly error dialog"""
        try:
            if not self.parent_widget:
                return
            
            title = "WRAPD Error"
            message = self._get_user_friendly_message(error)
            
            # Add recovery information
            if recovery_result:
                message += f"\n\nRecovery action taken: {recovery_result}"
            
            # Add suggested actions
            actions = self._get_recovery_suggestions(error)
            if actions:
                message += f"\n\nSuggested actions:\n" + "\n".join(f"• {action}" for action in actions)
            
            # Show appropriate dialog based on severity
            severity = error_info.get("severity", "medium")
            if severity == ErrorSeverity.CRITICAL.value:
                QMessageBox.critical(self.parent_widget, title, message)
            elif severity == ErrorSeverity.HIGH.value:
                QMessageBox.warning(self.parent_widget, title, message)
            else:
                QMessageBox.information(self.parent_widget, title, message)
                
        except Exception as dialog_error:
            self.logger.error(f"Error showing user dialog: {dialog_error}")
    
    def _get_user_friendly_message(self, error: Exception) -> str:
        """Get user-friendly error message"""
        if isinstance(error, ConfigurationError):
            return f"Configuration problem: {error.message}\n\nPlease check your settings."
        elif isinstance(error, NetworkError):
            return f"Network problem: {error.message}\n\nPlease check your internet connection."
        elif isinstance(error, APIConnectionError):
            return f"Cannot connect to AI service: {error.message}\n\nPlease check your API keys and internet connection."
        elif isinstance(error, ModelNotAvailableError):
            return f"Model not available: {error.message}\n\nPlease select a different model."
        elif isinstance(error, TerminalError):
            return f"Terminal error: {error.message}\n\nThe command could not be executed properly."
        elif isinstance(error, ThemeError):
            return f"Theme error: {error.message}\n\nThe theme could not be applied."
        else:
            return f"An error occurred: {error}"
    
    def _get_recovery_suggestions(self, error: Exception) -> List[str]:
        """Get recovery suggestions for an error"""
        if isinstance(error, NetworkError):
            return [
                "Check your internet connection",
                "Try again in a few moments",
                "Check if the service is available"
            ]
        elif isinstance(error, ConfigurationError):
            return [
                "Check your configuration settings",
                "Reset to default settings",
                "Restart the application"
            ]
        elif isinstance(error, APIConnectionError):
            return [
                "Verify your API keys",
                "Check your internet connection",
                "Try a different AI provider"
            ]
        elif isinstance(error, ModelNotAvailableError):
            return [
                "Select a different model",
                "Refresh the model list",
                "Check if the model is installed"
            ]
        else:
            return [
                "Try the operation again",
                "Restart the application",
                "Check the logs for details"
            ]
    
    def _attempt_recovery(self, error: WRAPDError) -> Any:
        """Attempt automatic recovery for an error"""
        recovery_key = f"{error.category.value}_{error.error_code}"
        
        if recovery_key in self.recovery_handlers:
            try:
                handler = self.recovery_handlers[recovery_key]
                result = handler(error)
                self.logger.info(f"Recovery successful for {recovery_key}: {result}")
                return result
            except Exception as recovery_error:
                self.logger.error(f"Recovery failed for {recovery_key}: {recovery_error}")
        
        return None
    
    def _notify_error_callbacks(self, error: Exception, error_info: Dict[str, Any]) -> None:
        """Notify registered error callbacks"""
        for callback in self.error_callbacks:
            try:
                callback(error, error_info)
            except Exception as callback_error:
                self.logger.error(f"Error in error callback: {callback_error}")
    
    def register_recovery_handler(self, error_category: str, error_code: str, 
                                 handler: Callable) -> None:
        """Register a recovery handler for specific error types"""
        key = f"{error_category}_{error_code}"
        self.recovery_handlers[key] = handler
        self.logger.info(f"Recovery handler registered for {key}")
    
    def add_error_callback(self, callback: Callable) -> None:
        """Add callback to be notified of errors"""
        self.error_callbacks.append(callback)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        with self.lock:
            total_errors = sum(self.error_counts.values())
            uptime = time.time() - self.start_time
            
            return {
                "error_counts": self.error_counts.copy(),
                "total_errors": total_errors,
                "recent_errors_count": len(self.recent_errors),
                "uptime_hours": uptime / 3600,
                "errors_per_hour": (total_errors / uptime) * 3600 if uptime > 0 else 0,
                "most_common_errors": sorted(
                    self.error_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10],
                "error_trends": {
                    category: len(timestamps) 
                    for category, timestamps in self.error_trends.items()
                }
            }
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent errors"""
        with self.lock:
            return self.recent_errors[:limit]
    
    def clear_statistics(self) -> None:
        """Clear error statistics"""
        with self.lock:
            self.error_counts.clear()
            self.recent_errors.clear()
            self.error_trends.clear()
            self.logger.info("Error statistics cleared")
    
    def export_error_report(self) -> Dict[str, Any]:
        """Export comprehensive error report"""
        with self.lock:
            return {
                "statistics": self.get_error_statistics(),
                "recent_errors": self.get_recent_errors(50),
                "trends": self.error_trends.copy(),
                "export_timestamp": time.time(),
                "uptime": time.time() - self.start_time
            }
    
    def close(self) -> None:
        """Cleanup error handler"""
        # Restore original exception handler
        if hasattr(self, 'original_excepthook'):
            sys.excepthook = self.original_excepthook
        
        self.logger.info("ErrorHandler closed")

def handle_api_error(func):
    """Decorator for handling API errors"""
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except APIConnectionError:
            # Re-raise API errors as-is
            raise
        except RateLimitError:
            # Re-raise rate limit errors as-is
            raise
        except Exception as e:
            # Convert other exceptions to API errors
            raise APIConnectionError(f"Unexpected error in {func.__name__}: {str(e)}")
    
    return wrapper

def handle_model_operation(func):
    """Decorator for handling model operation errors"""
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ModelSelectionError:
            # Re-raise model selection errors as-is
            raise
        except FileNotFoundError as e:
            raise ModelNotAvailableError(f"Model file not found: {str(e)}")
        except PermissionError as e:
            raise ModelInstallationError(f"Permission denied: {str(e)}")
        except Exception as e:
            raise ModelSelectionError(f"Unexpected error in {func.__name__}: {str(e)}")
    
    return wrapper

class ErrorRecovery:
    """Error recovery strategies"""
    
    @staticmethod
    def get_fallback_models() -> list:
        """Get fallback models when primary sources fail"""
        return [
            {
                "id": "fallback/basic-chat",
                "name": "Basic Chat Model",
                "provider": "fallback",
                "description": "Fallback model for basic functionality",
                "capabilities": {
                    "context_length": 2048,
                    "supports_streaming": True
                }
            }
        ]
    
    @staticmethod
    def get_error_message_for_user(error: Exception) -> str:
        """Get user-friendly error message"""
        if isinstance(error, APIConnectionError):
            if "openrouter" in str(error).lower():
                return "Unable to connect to OpenRouter. Please check your internet connection and API key."
            elif "ollama" in str(error).lower():
                return "Unable to connect to Ollama. Please make sure Ollama is installed and running."
            else:
                return "Unable to connect to the model service. Please check your internet connection."
        
        elif isinstance(error, RateLimitError):
            return "API rate limit exceeded. Please wait a moment before trying again."
        
        elif isinstance(error, ModelNotAvailableError):
            return "The selected model is not available. Please choose a different model."
        
        elif isinstance(error, ModelInstallationError):
            return "Failed to install the model. Please check your disk space and try again."
        
        elif isinstance(error, ValidationError):
            return f"Invalid input: {error.message}"
        
        else:
            return "An unexpected error occurred. Please try again or contact support."
    
    @staticmethod
    def suggest_recovery_actions(error: Exception) -> list:
        """Suggest recovery actions for an error"""
        actions = []
        
        if isinstance(error, APIConnectionError):
            actions.extend([
                "Check your internet connection",
                "Verify your API keys are correct",
                "Try switching to a different provider"
            ])
        
        elif isinstance(error, RateLimitError):
            actions.extend([
                "Wait before making another request",
                "Consider upgrading your API plan",
                "Switch to a local model"
            ])
        
        elif isinstance(error, ModelNotAvailableError):
            actions.extend([
                "Choose a different model",
                "Check if the model name is correct",
                "Try refreshing the model list"
            ])
        
        elif isinstance(error, ModelInstallationError):
            actions.extend([
                "Check available disk space",
                "Ensure Ollama is running",
                "Try installing a smaller model"
            ])
        
        else:
            actions.extend([
                "Try again in a few moments",
                "Restart the application",
                "Check the application logs"
            ])
        
        return actions