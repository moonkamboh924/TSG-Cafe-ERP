import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    DEBUG = False  # Disable debug mode to prevent code exposure
    
    # Use Railway's PostgreSQL database
    # Railway provides DATABASE_URL environment variable
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Handle PostgreSQL URL format for Railway/Heroku
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback to SQLite for local development
        # Ensure instance directory exists
        instance_dir = os.path.join(basedir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(instance_dir, "erp.db")}'
    
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
    
    # Email Configuration (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@tsgcafe.com'
    
    # SMS Configuration
    SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'TWILIO')  # TWILIO, MSG91, or FAST2SMS
    
    # Twilio Configuration (Works globally including Pakistan - $15 free trial)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # MSG91 Configuration (Paid - works in Pakistan)
    MSG91_AUTH_KEY = os.environ.get('MSG91_AUTH_KEY')
    MSG91_SENDER_ID = os.environ.get('MSG91_SENDER_ID', 'TSGCAF')
    MSG91_ROUTE = os.environ.get('MSG91_ROUTE', '4')
    MSG91_TEMPLATE_ID = os.environ.get('MSG91_TEMPLATE_ID')
    
    # Fast2SMS Configuration (Free: 50 SMS/day, India only)
    FAST2SMS_API_KEY = os.environ.get('FAST2SMS_API_KEY')
    
    # Cache Configuration (for verification codes)
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or 'SimpleCache'  # Use 'RedisCache' for production
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes default
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')  # For Redis cache
    
    # Stripe Configuration (Payment Processing)
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
