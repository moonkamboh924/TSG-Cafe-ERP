"""
System Settings Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone
from ...models import SystemSetting
from ...extensions import db

bp = Blueprint('system_admin_settings', __name__, url_prefix='/system-admin/settings')

def require_system_admin():
    """Decorator to ensure only system administrators can access"""
    if current_user.role != 'system_administrator':
        return redirect(url_for('dashboard.index'))
    return None

@bp.route('/')
@login_required
def index():
    """System Settings Dashboard"""
    redirect_response = require_system_admin()
    if redirect_response:
        return redirect_response
    
    # For now, redirect to main system admin dashboard
    return redirect(url_for('system_admin_dashboard.index'))

@bp.route('/api/global-settings')
@login_required
def get_global_settings():
    """Get global system settings"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get system-wide settings (business_id = None)
        settings = SystemSetting.query.filter_by(business_id=None).all()
        
        settings_data = {}
        for setting in settings:
            settings_data[setting.key] = {
                'value': setting.value,
                'description': setting.description
            }
        
        return jsonify({
            'settings': settings_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/global-settings', methods=['POST'])
@login_required
def update_global_settings():
    """Update global system settings"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        for key, value in data.items():
            setting = SystemSetting.query.filter_by(
                key=key, 
                business_id=None
            ).first()
            
            if setting:
                setting.value = str(value)
            else:
                # Create new global setting
                setting = SystemSetting(
                    key=key,
                    value=str(value),
                    business_id=None,
                    description=f'Global system setting: {key}'
                )
                db.session.add(setting)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Global settings updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
