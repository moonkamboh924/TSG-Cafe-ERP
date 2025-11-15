"""
System Administrator Module
Separate module for system administration functionality
"""

from flask import Blueprint

def create_system_admin_blueprint():
    """Create and configure the system admin blueprint"""
    from .blueprints.dashboard import bp as dashboard_bp
    from .blueprints.businesses import bp as businesses_bp
    from .blueprints.analytics import bp as analytics_bp
    from .blueprints.monitoring import bp as monitoring_bp
    from .blueprints.settings import bp as settings_bp
    from .blueprints.subscription_management import bp as subscriptions_bp
    
    return {
        'dashboard': dashboard_bp,
        'businesses': businesses_bp,
        'analytics': analytics_bp,
        'monitoring': monitoring_bp,
        'settings': settings_bp,
        'subscriptions': subscriptions_bp
    }
