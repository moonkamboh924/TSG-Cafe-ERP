from flask import Flask
from datetime import datetime, timezone
import os
from .extensions import db, migrate, login_manager, mail, cache
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
    mail.init_app(app)
    cache.init_app(app)
    
    # Initialize backup and data persistence services
    from app.services.backup_service import backup_service
    from app.services.data_persistence import data_persistence
    from app.services.scheduler_service import scheduler_service
    backup_service.init_app(app)
    data_persistence.init_app(app)
    scheduler_service.init_app(app)
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Disable detailed error messages in production
        if not app.debug:
            response.headers['Server'] = 'TSG-ERP'
        return response
    
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
    
    # Register subscription management blueprint
    from .blueprints import subscriptions as subscriptions_bp
    app.register_blueprint(subscriptions_bp.bp)

    # Register auth blueprint
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    
    # Register tenant registration blueprint
    from .blueprints import tenant_registration
    app.register_blueprint(tenant_registration.bp, url_prefix="/tenant")
    
    # Register system admin blueprints
    try:
        from .system_admin.blueprints.dashboard import bp as system_admin_dashboard_bp
        from .system_admin.blueprints.user_management import bp as system_admin_users_bp
        from .system_admin.blueprints.profile import bp as system_admin_profile_bp
        from .system_admin.blueprints.businesses import bp as system_admin_businesses_bp
        from .system_admin.blueprints.settings import bp as system_admin_settings_bp
        from .system_admin.blueprints.analytics import bp as system_admin_analytics_bp
        from .system_admin.blueprints.monitoring import bp as system_admin_monitoring_bp
        from .system_admin.blueprints.subscription_management import bp as system_admin_subscriptions_bp
        
        app.register_blueprint(system_admin_dashboard_bp)
        app.register_blueprint(system_admin_users_bp)
        app.register_blueprint(system_admin_profile_bp)
        app.register_blueprint(system_admin_businesses_bp)
        app.register_blueprint(system_admin_settings_bp)
        app.register_blueprint(system_admin_analytics_bp)
        app.register_blueprint(system_admin_monitoring_bp)
        app.register_blueprint(system_admin_subscriptions_bp)
        
        print("[OK] System admin blueprints registered successfully")
    except Exception as e:
        print(f"[ERROR] Failed to register system admin blueprints: {e}")
        # Continue without system admin blueprints if there are issues

    # Import models to ensure they are registered with SQLAlchemy
    from . import models
    
    # Multi-tenant database initialization
    def init_database():
        """Initialize database tables for multi-tenant ERP"""
        try:
            db.create_all()
            print("[OK] Multi-tenant database tables initialized")
            
            # Check if any tenants exist
            from .models import Business
            from sqlalchemy import text
            tenant_count = db.session.execute(text('SELECT COUNT(*) FROM businesses')).scalar()
            
            if tenant_count == 0:
                print("[INFO] No tenants found - system ready for tenant registration")
                # Create a system admin tenant only if DEMO_MODE is enabled
                demo_mode = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
                
                if demo_mode:
                    from .services.tenant_service import TenantService
                    try:
                        demo_tenant = TenantService.create_tenant(
                            business_name='Demo Restaurant',
                            owner_email='demo@example.com',
                            owner_name='Demo Admin',
                            subscription_plan='free'
                        )
                        print(f"[DEMO] Demo tenant created:")
                        print(f"  Username: {demo_tenant['owner']['username']}")
                        print(f"  Password: {demo_tenant['owner']['temp_password']}")
                    except Exception as e:
                        print(f"[DEMO] Failed to create demo tenant: {str(e)}")
            else:
                print(f"[OK] Multi-tenant system ready - {tenant_count} tenant(s) active")
                
        except Exception as e:
            print(f"Warning: Database initialization issue: {str(e)}")
    
    # Initialize database in app context
    with app.app_context():
        init_database()
    
    # Initialize system monitor
    from .utils.system_monitor import SystemMonitor
    SystemMonitor.initialize()
    
    # Initialize request tracking middleware
    from .middleware import track_request_metrics
    track_request_metrics(app)
    
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
        import os
        
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database_url_set': bool(os.environ.get('DATABASE_URL')),
            'database_connection': 'unknown'
        }
        
        # Test database connection
        try:
            db.session.execute('SELECT 1')
            health_data['database_connection'] = 'connected'
        except Exception as e:
            health_data['database_connection'] = f'failed: {str(e)}'
            health_data['status'] = 'unhealthy'
        
        return jsonify(health_data)
    
    # Add simple test route
    @app.route('/test')
    def test():
        return '<h1>TSG Cafe ERP - Application is running!</h1><p><a href="/auth/login">Go to Login</a></p>'
    
    # Add database diagnostic route
    @app.route('/db-status')
    def db_status():
        from flask import jsonify
        import os
        
        try:
            # Get database info
            db_url = os.environ.get('DATABASE_URL', 'Not set')
            
            # Test connection and get info
            result = db.session.execute('SELECT version()')
            version = result.fetchone()[0] if result else 'Unknown'
            
            # Count tables
            tables_result = db.session.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = tables_result.fetchone()[0]
            
            # Count users if table exists
            try:
                users_result = db.session.execute('SELECT COUNT(*) FROM users')
                user_count = users_result.fetchone()[0]
            except:
                user_count = 'Table not found'
            
            return jsonify({
                'database_url_set': bool(db_url != 'Not set'),
                'database_url_preview': db_url[:30] + '...' if len(db_url) > 30 else db_url,
                'connection_status': 'connected',
                'postgresql_version': version,
                'table_count': table_count,
                'user_count': user_count
            })
            
        except Exception as e:
            return jsonify({
                'database_url_set': bool(os.environ.get('DATABASE_URL')),
                'connection_status': 'failed',
                'error': str(e)
            })
    
    # Add root route handler for multi-tenant system
    @app.route('/')
    def root():
        try:
            from flask import redirect, url_for, render_template
            from flask_login import current_user
            from app.models import SystemSetting
            
            # If user is authenticated, redirect to dashboard
            if current_user.is_authenticated:
                return redirect(url_for('dashboard.index'))
            
            # Get welcome page settings from database
            settings = {
                'hero_title': SystemSetting.get_setting('hero_title', 'Transform Your Restaurant Operations', business_id=None),
                'hero_subtitle': SystemSetting.get_setting('hero_subtitle', 'Comprehensive Multi-Tenant ERP Solution for Modern Restaurants', business_id=None),
                'hero_description': SystemSetting.get_setting('hero_description', 'Streamline your restaurant management with our powerful, cloud-based ERP system.', business_id=None),
                'social_facebook': SystemSetting.get_setting('social_facebook', '#', business_id=None),
                'social_twitter': SystemSetting.get_setting('social_twitter', '#', business_id=None),
                'social_linkedin': SystemSetting.get_setting('social_linkedin', '#', business_id=None),
                'social_instagram': SystemSetting.get_setting('social_instagram', '#', business_id=None),
                'social_youtube': SystemSetting.get_setting('social_youtube', '#', business_id=None),
                'contact_address': SystemSetting.get_setting('contact_address', '123 Restaurant Ave, Food City, FC 12345', business_id=None),
                'contact_phone': SystemSetting.get_setting('contact_phone', '+1 (555) 123-4567', business_id=None),
                'contact_email': SystemSetting.get_setting('contact_email', 'support@tsgcafeerp.com', business_id=None),
                'contact_hours': SystemSetting.get_setting('contact_hours', 'Mon - Fri: 9:00 AM - 6:00 PM', business_id=None),
                'tutorial_getting_started': SystemSetting.get_setting('tutorial_getting_started', '', business_id=None),
                'tutorial_pos_system': SystemSetting.get_setting('tutorial_pos_system', '', business_id=None),
                'tutorial_inventory': SystemSetting.get_setting('tutorial_inventory', '', business_id=None),
                'tutorial_reports': SystemSetting.get_setting('tutorial_reports', '', business_id=None),
                'company_name': SystemSetting.get_setting('company_name', 'TSG Cafe ERP', business_id=None),
                'company_description': SystemSetting.get_setting('company_description', 'The leading multi-tenant restaurant management solution.', business_id=None),
                'company_tagline': SystemSetting.get_setting('company_tagline', 'Powered by Trisync Global', business_id=None),
                'copyright_text': SystemSetting.get_setting('copyright_text', '© 2025 Trisync Global. All rights reserved.', business_id=None),
            }
            
            # Show welcome page for non-authenticated users
            return render_template('welcome.html', settings=settings)
                
        except Exception as e:
            app.logger.error(f"Error in root route: {str(e)}")
            # Fallback to welcome page if there's an error
            return render_template('welcome.html', settings={})
    
    
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
