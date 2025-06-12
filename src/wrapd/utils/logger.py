#!/usr/bin/env python3
"""
WRAPD: Comprehensive logging system with multiple handlers and performance monitoring
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import threading
import time
import json

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors"""
        # Add color to levelname
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

class PerformanceHandler(logging.Handler):
    """Custom handler to track performance metrics"""
    
    def __init__(self):
        super().__init__()
        self.metrics = {
            'total_logs': 0,
            'logs_by_level': {},
            'errors_by_module': {},
            'start_time': time.time()
        }
        self.lock = threading.Lock()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Track performance metrics for each log record"""
        with self.lock:
            self.metrics['total_logs'] += 1
            
            # Track by level
            level = record.levelname
            self.metrics['logs_by_level'][level] = self.metrics['logs_by_level'].get(level, 0) + 1
            
            # Track errors by module
            if record.levelno >= logging.ERROR:
                module = record.module or 'unknown'
                self.metrics['errors_by_module'][module] = self.metrics['errors_by_module'].get(module, 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self.lock:
            uptime = time.time() - self.metrics['start_time']
            return {
                **self.metrics,
                'uptime_seconds': uptime,
                'logs_per_minute': (self.metrics['total_logs'] / uptime) * 60 if uptime > 0 else 0
            }

class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'thread': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                          'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'exc_info', 'exc_text',
                          'stack_info', 'getMessage'):
                log_entry['extra'] = log_entry.get('extra', {})
                log_entry['extra'][key] = value
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)

class Logger:
    """
    Comprehensive logging system for WRAPD with multiple handlers,
    performance monitoring, and structured logging capabilities
    """
    
    def __init__(self, log_file: Union[str, Path], 
                 level: int = logging.INFO,
                 enable_console: bool = True,
                 enable_structured: bool = False,
                 enable_performance: bool = True):
        """
        Initialize the WRAPD logging system
        
        Args:
            log_file: Path to the main log file
            level: Logging level (default: INFO)
            enable_console: Whether to enable console output
            enable_structured: Whether to enable structured JSON logging
            enable_performance: Whether to enable performance monitoring
        """
        self.log_file = Path(log_file)
        self.level = level
        self.enable_console = enable_console
        self.enable_structured = enable_structured
        self.enable_performance = enable_performance
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create main logger
        self.logger = logging.getLogger("wrapd")
        self.logger.setLevel(level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Performance tracking
        self.performance_handler: Optional[PerformanceHandler] = None
        
        # Setup handlers
        self._setup_handlers()
        
        # Log initialization
        self.info("Logger initialized successfully")
        self.info(f"Log file: {self.log_file}")
        self.info(f"Log level: {logging.getLevelName(level)}")
    
    def _setup_handlers(self) -> None:
        """Setup all logging handlers"""
        # 1. Main rotating file handler
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(self.level)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s.%(module)s.%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 2. Console handler (optional)
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            console_formatter = ColoredFormatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # 3. Error file handler (errors and above only)
        error_file = self.log_file.parent / f"{self.log_file.stem}_errors.log"
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s.%(module)s.%(funcName)s:%(lineno)d | %(message)s\n'
            'Thread: %(threadName)s (%(thread)d) | Process: %(processName)s (%(process)d)\n'
            '%(pathname)s:%(lineno)d\n' + '-' * 80,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        self.logger.addHandler(error_handler)
        
        # 4. Structured JSON handler (optional)
        if self.enable_structured:
            json_file = self.log_file.parent / f"{self.log_file.stem}_structured.jsonl"
            json_handler = TimedRotatingFileHandler(
                json_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            json_handler.setLevel(self.level)
            json_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(json_handler)
        
        # 5. Performance monitoring handler (optional)
        if self.enable_performance:
            self.performance_handler = PerformanceHandler()
            self.performance_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(self.performance_handler)
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, exc_info: bool = False, **kwargs) -> None:
        """Log error message"""
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message"""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs) -> None:
        """Log exception with traceback"""
        self.logger.exception(message, *args, **kwargs)
    
    def log_function_call(self, func_name: str, args: tuple = (), kwargs: dict = None) -> None:
        """Log function call with parameters"""
        kwargs = kwargs or {}
        self.debug(f"Function call: {func_name}(args={args}, kwargs={kwargs})")
    
    def log_performance(self, operation: str, duration: float, **extra) -> None:
        """Log performance metrics"""
        message = f"Performance: {operation} took {duration:.3f}s"
        self.info(message, extra={'operation': operation, 'duration': duration, **extra})
    
    def log_user_action(self, action: str, details: dict = None) -> None:
        """Log user actions for analytics"""
        details = details or {}
        self.info(f"User action: {action}", extra={'user_action': action, 'details': details})
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, 
                    duration: float, **extra) -> None:
        """Log API calls"""
        message = f"API call: {method} {endpoint} -> {status_code} ({duration:.3f}s)"
        self.info(message, extra={
            'api_endpoint': endpoint,
            'api_method': method,
            'api_status': status_code,
            'api_duration': duration,
            **extra
        })
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if self.performance_handler:
            return self.performance_handler.get_metrics()
        return {}
    
    def set_level(self, level: int) -> None:
        """Change logging level"""
        self.level = level
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            if not isinstance(handler, PerformanceHandler):
                handler.setLevel(level)
    
    def add_context(self, **context) -> 'LoggerContext':
        """Add context to subsequent log messages"""
        return LoggerContext(self, context)
    
    def close(self) -> None:
        """Close all handlers and cleanup"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

class LoggerContext:
    """Context manager for adding context to log messages"""
    
    def __init__(self, logger: Logger, context: dict):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self) -> 'LoggerContext':
        # Store old factory
        self.old_factory = logging.getLogRecordFactory()
        
        # Create new factory that adds context
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old factory
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)

# Utility functions for backward compatibility
def setup_logger(log_file: Union[str, Path], level: int = logging.INFO) -> Logger:
    """Setup and return a Logger instance (backward compatibility)"""
    return Logger(log_file, level)

def log_exception(logger: Logger, exception: Exception, context: str = "") -> None:
    """Log an exception with context (backward compatibility)"""
    if context:
        logger.exception(f"{context}: {type(exception).__name__}: {exception}")
    else:
        logger.exception(f"{type(exception).__name__}: {exception}")

def create_null_logger() -> logging.Logger:
    """Create a null logger that doesn't output anything"""
    null_logger = logging.getLogger("null_logger")
    null_logger.addHandler(logging.NullHandler())
    return null_logger
