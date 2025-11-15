from flask import Flask
from datetime import datetime
import os
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
            'timestamp': datetime.now().isoformat(),
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
            from .models import Business
            
            # If user is authenticated, redirect to dashboard
            if current_user.is_authenticated:
                return redirect(url_for('dashboard.index'))
            
            # Check if any tenants exist
            from sqlalchemy import text
            tenant_count = db.session.execute(text('SELECT COUNT(*) FROM businesses')).scalar()
            
            if tenant_count == 0:
                # No tenants exist - show welcome page with registration
                return render_template('welcome.html')
            else:
                # Tenants exist - redirect to login
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            app.logger.error(f"Error in root route: {str(e)}")
            # Fallback to tenant registration if there's an error
            return redirect(url_for('tenant.register'))
    
    
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
