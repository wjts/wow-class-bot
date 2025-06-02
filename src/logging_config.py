import logging
import sys
from datetime import datetime
import os

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

def setup_logging():
    """Set up logging configuration for the Discord bot"""
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatters
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    audit_formatter = logging.Formatter(
        fmt='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Main log file handler (DEBUG and above)
    main_file_handler = logging.FileHandler(
        filename=f'{log_dir}/discord_bot.log',
        encoding='utf-8',
        mode='a'
    )
    main_file_handler.setLevel(logging.DEBUG)
    main_file_handler.setFormatter(file_formatter)
    
    # Error log file handler (ERROR and above)
    error_file_handler = logging.FileHandler(
        filename=f'{log_dir}/errors.log',
        encoding='utf-8',
        mode='a'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)
    
    # Audit log file handler (for user actions and security events)
    audit_file_handler = logging.FileHandler(
        filename=f'{log_dir}/audit.log',
        encoding='utf-8',
        mode='a'
    )
    audit_file_handler.setLevel(logging.INFO)
    audit_file_handler.setFormatter(audit_formatter)
    
    # Create audit logger filter
    class AuditFilter(logging.Filter):
        def filter(self, record):
            # Only log records that contain audit keywords
            audit_keywords = [
                'USER ACTION', 'ADMIN ACTION', 'SECURITY EVENT',
                'SELECTION_CREATED', 'SELECTION_UPDATED', 'SELECTION_DELETED',
                'USER_REMOVED', 'UNAUTHORIZED'
            ]
            return any(keyword in record.getMessage() for keyword in audit_keywords)
    
    audit_file_handler.addFilter(AuditFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove default handlers
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(main_file_handler)
    root_logger.addHandler(error_file_handler)
    root_logger.addHandler(audit_file_handler)
    
    # Configure discord.py logging (reduce verbosity)
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    # Configure Google API logging (reduce verbosity)
    google_logger = logging.getLogger('googleapiclient')
    google_logger.setLevel(logging.WARNING)
    
    oauth_logger = logging.getLogger('oauth2client')
    oauth_logger.setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log files location: {os.path.abspath(log_dir)}")
    
    return logger

def get_audit_logger():
    """Get a logger specifically for audit events"""
    return logging.getLogger('audit')

def log_startup_info():
    """Log important startup information"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Discord WoW Class Management Bot Starting")
    logger.info(f"Startup time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

def log_shutdown_info():
    """Log shutdown information"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Discord WoW Class Management Bot Shutting Down")
    logger.info(f"Shutdown time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)