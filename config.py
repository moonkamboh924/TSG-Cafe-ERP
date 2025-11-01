import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Use Railway's PostgreSQL database
    # Railway provides DATABASE_URL environment variable
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Railway/Heroku compatibility: convert postgres:// to postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Fallback to SQLite for local development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/erp.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ERP Configuration
    ERP_NAME = os.environ.get('ERP_NAME') or 'TSG Cafe ERP'
    ERP_SUBTITLE = os.environ.get('ERP_SUBTITLE') or 'Powered by Trisyns Global'
    TIMEZONE = os.environ.get('TIMEZONE') or 'Asia/Karachi'
    CURRENCY = os.environ.get('CURRENCY') or 'PKR'
    LANG = os.environ.get('LANG') or 'en'
    
    # Security
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
