"""
System Settings Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, current_app
from flask_login import login_required
from ...extensions import db
from ...models import SystemSetting
from ..decorators import require_system_admin, system_admin_api_required
from werkzeug.utils import secure_filename
import os
import uuid

bp = Blueprint('system_admin_settings', __name__, url_prefix='/system-admin/settings')

# Favicon upload configuration
ALLOWED_FAVICON_EXTENSIONS = {'png', 'jpg', 'jpeg', 'ico', 'svg'}

def get_favicon_folder():
    """Get absolute path to static folder"""
    return os.path.join(current_app.root_path, 'static')

def allowed_favicon_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FAVICON_EXTENSIONS

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

# Favicon Management API

@bp.route('/api/favicon')
@login_required
@system_admin_api_required
def get_favicon():
    """Get current favicon setting"""
    try:
        favicon = SystemSetting.get_setting('system_favicon', None, business_id=None)
        return jsonify({
            'success': True,
            'favicon': favicon
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/favicon/upload', methods=['POST'])
@login_required
@system_admin_api_required
def upload_favicon():
    """Upload a new favicon"""
    try:
        if 'favicon' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['favicon']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_favicon_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed types: PNG, JPG, JPEG, ICO, SVG'}), 400
        
        # Delete old favicon if exists
        old_favicon = SystemSetting.get_setting('system_favicon', None, business_id=None)
        if old_favicon and old_favicon != 'favicon.ico':
            old_path = os.path.join(get_favicon_folder(), old_favicon)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception as e:
                    current_app.logger.warning(f"Could not delete old favicon: {e}")
        
        # Generate unique filename with secure name
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"favicon_{uuid.uuid4().hex[:8]}.{original_ext}"
        
        # Save file with absolute path
        filepath = os.path.join(get_favicon_folder(), filename)
        file.save(filepath)
        
        # Update setting with explicit business_id=None for global setting
        SystemSetting.set_setting('system_favicon', filename, description='System favicon file', business_id=None)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Favicon uploaded successfully',
            'favicon': filename
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/favicon', methods=['DELETE'])
@login_required
@system_admin_api_required
def delete_favicon():
    """Delete custom favicon and restore default"""
    try:
        # Get current favicon
        favicon = SystemSetting.get_setting('system_favicon', None, business_id=None)
        
        if favicon and favicon != 'favicon.ico':
            # Delete file
            filepath = os.path.join(get_favicon_folder(), favicon)
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Remove setting
            setting = SystemSetting.query.filter_by(
                key='system_favicon',
                business_id=None
            ).first()
            if setting:
                db.session.delete(setting)
                db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Favicon deleted successfully. Default favicon restored.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
