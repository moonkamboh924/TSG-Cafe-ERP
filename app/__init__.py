from flask import Flask
from datetime import datetime
from .extensions import db, migrate, login_manager
from .blueprints import dashboard, admin, pos, menu, inventory, finance, reports, profile

def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Setup logging
    try:
        from logging_config import setup_logging
        setup_logging(app)
    except ImportError:
        pass

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Initialize backup and data persistence services
    from app.services.backup_service import backup_service
    from app.services.data_persistence import data_persistence
    from app.services.scheduler_service import scheduler_service
    backup_service.init_app(app)
    data_persistence.init_app(app)
    scheduler_service.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(dashboard.bp, url_prefix="/dashboard")
    app.register_blueprint(admin.bp, url_prefix="/admin")
    app.register_blueprint(pos.bp, url_prefix="/pos")
    app.register_blueprint(menu.bp, url_prefix="/menu")
    app.register_blueprint(inventory.bp, url_prefix="/inventory")
    app.register_blueprint(finance.bp, url_prefix="/finance")
    app.register_blueprint(reports.bp, url_prefix="/reports")
    app.register_blueprint(profile.bp, url_prefix="/profile")

    # Register auth blueprint
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Import models to ensure they are registered with SQLAlchemy
    from . import models
    
    # Initialize database tables (for multi-tenant ERP)
    with app.app_context():
        try:
            db.create_all()
            print("[OK] Database tables initialized")
        except Exception as e:
            print(f"Warning: Database initialization issue: {str(e)}")
    
    # Add template context processor for settings
    @app.context_processor
    def inject_settings():
        from .models import SystemSetting
        def get_setting(key, default=None):
            try:
                return SystemSetting.get_setting(key, default)
            except Exception as e:
                app.logger.warning(f"Error getting setting {key}: {str(e)}")
                return default
        return dict(get_setting=get_setting)
    
    # Add template filters for timezone handling
    @app.template_filter('format_datetime')
    def format_datetime_filter(dt):
        from .utils.timezone_utils import format_datetime
        return format_datetime(dt)
    
    @app.template_filter('format_date')
    def format_date_filter(dt):
        from .utils.timezone_utils import format_date_only
        return format_date_only(dt)
    
    @app.template_filter('format_time')
    def format_time_filter(dt):
        from .utils.timezone_utils import format_time_only
        return format_time_only(dt)
    
    @app.template_filter('to_local_time')
    def to_local_time_filter(dt):
        from .utils.timezone_utils import convert_utc_to_local
        return convert_utc_to_local(dt)
    
    # Add favicon route to prevent 404 errors
    @app.route('/favicon.ico')
    def favicon():
        from flask import send_from_directory
        import os
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    # Add health check endpoint for Railway
    @app.route('/health')
    def health_check():
        from flask import jsonify
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    
    # Add simple test route
    @app.route('/test')
    def test():
        return '<h1>TSG Cafe ERP - Application is running!</h1><p><a href="/auth/login">Go to Login</a></p>'
    
    # Add root route handler for unauthenticated users
    @app.route('/')
    def root():
        try:
            from flask import redirect, url_for
            from flask_login import current_user
            if current_user.is_authenticated:
                return redirect(url_for('dashboard.index'))
            else:
                return redirect(url_for('auth.login'))
        except Exception as e:
            app.logger.error(f"Error in root route: {str(e)}")
            return f'<h1>TSG Cafe ERP</h1><p>Error: {str(e)}</p><p><a href="/test">Test Page</a></p><p><a href="/auth/login">Login</a></p>'
    
    
    # Add before_request handler for password change requirement
    @app.before_request
    def check_password_change_required():
        from flask import request, redirect, url_for
        from flask_login import current_user
        
        # Skip check for static files, auth routes, and password change routes
        if (request.endpoint and 
            (request.endpoint.startswith('static') or 
             request.endpoint.startswith('auth.') or
             request.endpoint == 'admin.change_password_required' or
             request.endpoint == 'admin.change_password' or
             request.endpoint == 'admin.api.change_password')):
            return
        
        # Check if user is authenticated and requires password change
        if (current_user.is_authenticated and 
            hasattr(current_user, 'requires_password_change') and
            current_user.requires_password_change):
            return redirect(url_for('admin.change_password_required'))

    return app
