"""
System Settings Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required
from ...extensions import db
from ...models import SystemSetting
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_settings', __name__, url_prefix='/system-admin/settings')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """System Settings Dashboard"""
    return render_template('system_admin/settings.html')

@bp.route('/api/welcome-page-settings')
@login_required
@system_admin_api_required
def get_welcome_settings():
    """Get welcome page settings"""
    
    try:
        settings = {
            # Hero Section
            'hero_title': SystemSetting.get_setting('hero_title', 'Transform Your Restaurant Operations', business_id=None),
            'hero_subtitle': SystemSetting.get_setting('hero_subtitle', 'Comprehensive Multi-Tenant ERP Solution for Modern Restaurants', business_id=None),
            'hero_description': SystemSetting.get_setting('hero_description', 'Streamline your restaurant management with our powerful, cloud-based ERP system. Built for efficiency, designed for growth.', business_id=None),
            
            # Social Media Links
            'social_facebook': SystemSetting.get_setting('social_facebook', '#', business_id=None),
            'social_twitter': SystemSetting.get_setting('social_twitter', '#', business_id=None),
            'social_linkedin': SystemSetting.get_setting('social_linkedin', '#', business_id=None),
            'social_instagram': SystemSetting.get_setting('social_instagram', '#', business_id=None),
            'social_youtube': SystemSetting.get_setting('social_youtube', '#', business_id=None),
            
            # Contact Information
            'contact_address': SystemSetting.get_setting('contact_address', '123 Restaurant Ave, Food City, FC 12345', business_id=None),
            'contact_phone': SystemSetting.get_setting('contact_phone', '+1 (555) 123-4567', business_id=None),
            'contact_email': SystemSetting.get_setting('contact_email', 'support@tsgcafeerp.com', business_id=None),
            'contact_hours': SystemSetting.get_setting('contact_hours', 'Mon - Fri: 9:00 AM - 6:00 PM', business_id=None),
            
            # Video Tutorials
            'tutorial_getting_started': SystemSetting.get_setting('tutorial_getting_started', '', business_id=None),
            'tutorial_pos_system': SystemSetting.get_setting('tutorial_pos_system', '', business_id=None),
            'tutorial_inventory': SystemSetting.get_setting('tutorial_inventory', '', business_id=None),
            'tutorial_reports': SystemSetting.get_setting('tutorial_reports', '', business_id=None),
            
            # Company Info
            'company_name': SystemSetting.get_setting('company_name', 'TSG Cafe ERP', business_id=None),
            'company_description': SystemSetting.get_setting('company_description', 'The leading multi-tenant restaurant management solution trusted by thousands of restaurants worldwide.', business_id=None),
            'company_tagline': SystemSetting.get_setting('company_tagline', 'Powered by Trisync Global', business_id=None),
            'copyright_text': SystemSetting.get_setting('copyright_text', '© 2025 Trisync Global. All rights reserved.', business_id=None),
        }
        
        return jsonify({'settings': settings})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/welcome-page-settings', methods=['POST'])
@login_required
@system_admin_api_required
def update_welcome_settings():
    """Update welcome page settings"""
    
    try:
        data = request.get_json()
        
        # Update all settings
        for key, value in data.items():
            SystemSetting.set_setting(key, value, business_id=None)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Welcome page settings updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
