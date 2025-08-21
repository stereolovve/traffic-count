# utils/logging_config.py
"""
Sistema de logging estruturado para debugging e monitoramento
"""
import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
import traceback
from typing import Optional, Dict, Any
import json

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
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
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_entry['extra'] = log_entry.get('extra', {})
                log_entry['extra'][key] = value
        
        return json.dumps(log_entry, default=str)

class ColoredConsoleFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)

class ApplicationLogger:
    """Centralized logging configuration for the application"""
    
    def __init__(self, app_name: str = "contador_perplan", log_dir: Optional[str] = None):
        self.app_name = app_name
        
        # Use application root directory for logs
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            # Default to application root directory (where executable is)
            self.log_dir = Path.cwd()
            
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Only error log file (performance optimized)
        self.error_log_file = self.log_dir / f"{app_name}_errors.log"
        
        # Setup loggers
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Setup minimal logging for performance"""
        
        # Root logger configuration - only WARNING and above
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.WARNING)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler - only ERROR and CRITICAL (minimal noise)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        console_formatter = ColoredConsoleFormatter(
            '%(levelname)s: %(message)s'  # Simplified format
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Error log file handler - only ERROR and CRITICAL
        error_file_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s:%(funcName)s:%(lineno)d\n'
            '%(message)s\n'
            'Thread: %(threadName)s (%(thread)d)\n'
            '%(pathname)s:%(lineno)d\n' + '-'*50
        )
        error_file_handler.setFormatter(error_file_formatter)
        root_logger.addHandler(error_file_handler)
        
        # Configure specific loggers
        self._configure_module_loggers()
        
        # Minimal startup log (only to file)
        error_logger = logging.getLogger('startup')
        error_logger.error(f"=== {self.app_name.upper()} STARTED ===")
        error_logger.error(f"Error log: {self.error_log_file}")
    
    def _configure_module_loggers(self):
        """Configure specific module loggers for minimal output"""
        
        # Application loggers - only ERROR and above
        app_loggers = [
            'main', 'contador', 'database', 'diagnostic', 'loading_screen',
            'session_manager', 'api_manager', 'ui_manager', 'excel_manager',
            'history_manager', 'startup'
        ]
        
        for logger_name in app_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.ERROR)  # Only errors
        
        # Third-party loggers - suppress completely unless critical
        noisy_loggers = [
            'httpx', 'urllib3', 'requests', 'asyncio', 'sqlalchemy',
            'flet', 'flet_desktop', 'utils.updater'
        ]
        
        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL)  # Almost silent
    
    def log_startup_info(self):
        """Minimal startup info logging"""
        # Skip startup info logging for performance
        pass
    
    def log_exception(self, exception: Exception, context: str = "", extra_data: Optional[Dict] = None):
        """Log exception with full context"""
        logger = logging.getLogger('exceptions')
        
        exc_info = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'context': context,
            'traceback': traceback.format_exc(),
        }
        
        if extra_data:
            exc_info['extra_data'] = extra_data
        
        logger.error(f"Exception in {context}: {exception}", extra=exc_info)
    
    def create_logger(self, name: str, level: int = logging.INFO) -> logging.Logger:
        """Create a logger with the standard configuration"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        return logger
    
    def get_log_files(self) -> Dict[str, Path]:
        """Get log file paths"""
        return {
            'errors': self.error_log_file,
        }
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    logging.info(f"Deleted old log file: {log_file}")
                    
        except Exception as e:
            logging.error(f"Error cleaning up old logs: {e}")

def setup_application_logging(app_name: str = "contador_perplan", 
                            log_dir: Optional[str] = None, 
                            debug_mode: bool = False) -> ApplicationLogger:
    """Setup application logging and return logger instance"""
    
    app_logger = ApplicationLogger(app_name, log_dir)
    
    if debug_mode:
        # In debug mode, show more verbose logging
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging.DEBUG)
    
    # Log startup information
    app_logger.log_startup_info()
    
    # Clean up old logs
    app_logger.cleanup_old_logs()
    
    return app_logger

# Global exception handler
def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Let KeyboardInterrupt be handled normally
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger = logging.getLogger('uncaught_exceptions')
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

# Install global exception handler
sys.excepthook = handle_exception