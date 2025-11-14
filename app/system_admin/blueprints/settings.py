"""
System Settings Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import login_required
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_settings', __name__, url_prefix='/system-admin/settings')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """System Settings Dashboard"""
    # For now, redirect to main system admin dashboard
    return redirect(url_for('system_admin_dashboard.index'))

@bp.route('/api/global-settings')
@login_required
@system_admin_api_required
def get_global_settings():
    """Get global system settings"""
    
    try:
        # Placeholder for system settings - implement when SystemSetting model is created
        settings_data = {
            'maintenance_mode': {'value': False, 'description': 'System maintenance mode'},
            'max_businesses': {'value': 100, 'description': 'Maximum number of businesses'},
            'default_subscription': {'value': 'basic', 'description': 'Default subscription plan'}
        }
        
        return jsonify({
            'settings': settings_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/global-settings', methods=['POST'])
@login_required
@system_admin_api_required
def update_global_settings():
    """Update global system settings"""
    
    try:
        data = request.get_json()
        
        # Placeholder for updating system settings - implement when SystemSetting model is created
        # For now, just return success
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully (placeholder implementation)'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
