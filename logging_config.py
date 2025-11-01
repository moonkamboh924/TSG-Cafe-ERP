import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging(app):
    """Setup logging configuration for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging level based on environment
    log_level = logging.DEBUG if app.config.get('FLASK_DEBUG') else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler for general application logs
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # File handler for error logs
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Configure Flask app logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    
    if app.config.get('FLASK_DEBUG'):
        app.logger.addHandler(console_handler)
    
    # Configure SQLAlchemy logging (only in debug mode)
    if app.config.get('FLASK_DEBUG'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    return app.logger

def log_audit_error(error_msg):
    """Log audit errors to a dedicated logger"""
    logger = logging.getLogger('audit_errors')
    logger.error(error_msg)

def log_dashboard_error(error_msg):
    """Log dashboard errors to a dedicated logger"""
    logger = logging.getLogger('dashboard_errors')
    logger.error(error_msg)
