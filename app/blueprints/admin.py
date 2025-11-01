from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app.models import User, SystemSetting, AuditLog, BillTemplate, Sale, db
from app.auth import require_permissions, log_audit
from app.services.backup_service import backup_service
from app.services.data_persistence import data_persistence
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
import logging
import json
import os
import uuid

bp = Blueprint('admin', __name__)

@bp.route('/')
@login_required
@require_permissions('admin.view')
def index():
    return render_template('admin/index.html')

@bp.route('/global-settings')
@login_required
@require_permissions('admin.view')
def global_settings():
    return render_template('admin/global_settings.html')

@bp.route('/api/global-settings')
@login_required
@require_permissions('admin.view')
def get_global_settings():
    """Get global settings as JSON for API consumption"""
    from app.models import SystemSetting
    settings = {
        'restaurant_name': SystemSetting.get_setting('restaurant_name', 'My Business'),
        'restaurant_subtitle': SystemSetting.get_setting('restaurant_subtitle', 'Powered by Trisync Global'),
        'copyright_company': SystemSetting.get_setting('copyright_company', 'Trysync global'),
        'restaurant_address': SystemSetting.get_setting('restaurant_address', '123 Main Street, Lahore'),
        'restaurant_phone': SystemSetting.get_setting('restaurant_phone', '+92 300 1234567'),
        'tax_rate': SystemSetting.get_setting('tax_rate', '16'),
        'currency': SystemSetting.get_setting('currency', 'PKR'),
        'date_format': SystemSetting.get_setting('date_format', 'DD/MM/YYYY'),
        'time_format': SystemSetting.get_setting('time_format', '12'),
        'timezone': SystemSetting.get_setting('timezone', 'Asia/Karachi'),
        'address': SystemSetting.get_setting('address', ''),
        'phone': SystemSetting.get_setting('phone', ''),
        'email': SystemSetting.get_setting('email', ''),
        'success': True
    }
    return jsonify(settings)

@bp.route('/bill-editor')
@login_required
@require_permissions('admin.view')
def bill_editor():
    from app.models import SystemSetting
    business_name = SystemSetting.get_setting('restaurant_name', 'My Business')
    return render_template('admin/bill_editor.html', business_name=business_name)

@bp.route('/api/users')
@login_required
@require_permissions('admin.view')
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # System administrators can see all users
    # Other users cannot see system administrators
    if current_user.role == 'system_administrator':
        users_query = User.query
    else:
        # Hide system administrators from regular users
        users_query = User.query.filter(User.role != 'system_administrator')
    
    users = users_query.order_by(User.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'users': [user.to_dict() for user in users.items],
        'total': users.total,
        'pages': users.pages,
        'current_page': page
    })

@bp.route('/api/users', methods=['POST'])
@login_required
@require_permissions('admin.create')
def create_user():
    data = request.get_json()
    
    # Prevent non-system administrators from creating system administrator accounts
    if data.get('role') == 'system_administrator' and current_user.role != 'system_administrator':
        return jsonify({
            'error': 'Access denied. Only System Administrators can create system administrator accounts.'
        }), 403
    
    try:
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Generate next employee ID (ensure uniqueness)
        employee_id = User.generate_next_employee_id()
        while User.query.filter_by(employee_id=employee_id).first():
            # If duplicate, increment and try again
            num = int(employee_id[3:]) + 1
            employee_id = f"EMP{num:03d}"
        
        # Extract first and last names
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        # Generate full name if not provided
        full_name = data.get('full_name')
        if not full_name and (first_name or last_name):
            full_name = f"{first_name} {last_name}".strip()
        
        # Generate username if not provided
        username = data.get('username')
        if not username and first_name and last_name:
            username = User.generate_username(first_name, last_name, employee_id)
        
        # Ensure username is unique
        if User.query.filter_by(username=username).first():
            # Add a number suffix if duplicate
            counter = 1
            while User.query.filter_by(username=f"{username}{counter}").first():
                counter += 1
            username = f"{username}{counter}"
        
        # Set default password if not provided
        password = data.get('password', '1234@1234')
        
        user = User(
            employee_id=employee_id,
            username=username,
            email=data['email'],
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            role=data['role'],
            designation=data.get('designation'),
            phone=data.get('phone'),
            address=data.get('address'),
            department=data.get('department'),
            navigation_permissions=data.get('navigation_permissions'),
            requires_password_change=data.get('requires_password_change', True),
            is_active=data.get('is_active', True)
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        log_audit('create', 'user', user.id, {
            'username': user.username,
            'employee_id': user.employee_id,
            'role': user.role,
            'full_name': user.full_name
        })
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'generated_username': username,
            'default_password': password if data.get('password') is None else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@require_permissions('admin.edit')
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Non-system administrators cannot view/edit/delete system administrators
    if user.role == 'system_administrator' and current_user.role != 'system_administrator':
        return jsonify({
            'error': 'Access denied. You do not have permission to access this user account.'
        }), 403
    
    # Handle GET request - return user details
    if request.method == 'GET':
        return jsonify(user.to_dict())
    
    # Handle DELETE request - create deletion request (not direct delete)
    if request.method == 'DELETE':
        from app.models import AccountDeletionRequest
        
        # Users cannot delete their own account directly
        if user.id == current_user.id:
            return jsonify({
                'error': 'You cannot delete your own account. Please submit a deletion request instead.',
                'show_request_form': True
            }), 403
        
        # Only system administrator can delete other users
        if current_user.role != 'system_administrator':
            return jsonify({
                'error': 'Only System Administrators can delete user accounts.'
            }), 403
        
        # Check if the user can be deleted
        if not user.can_be_edited_by(current_user):
            return jsonify({
                'error': 'You do not have permission to delete this protected user'
            }), 403
        
        try:
            # Delete any pending account deletion requests for this user first
            from app.models import AccountDeletionRequest, PasswordResetRequest
            AccountDeletionRequest.query.filter_by(user_id=user.id).delete()
            PasswordResetRequest.query.filter_by(user_id=user.id).delete()
            
            # Log the deletion before removing
            log_audit('delete', 'user', user.id, {
                'username': user.username,
                'full_name': user.full_name,
                'deleted_by': current_user.full_name
            })
            
            # Delete the user
            db.session.delete(user)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'User {user.full_name} has been permanently deleted from the system.'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Error deleting user: {str(e)}'}), 500
    
    # Handle PUT request - update user
    data = request.get_json()
    
    # Check if the user can be edited by the current user
    if not user.can_be_edited_by(current_user):
        return jsonify({
            'error': 'You do not have permission to edit this protected user'
        }), 403
    
    # Prevent non-system administrators from changing role to system_administrator
    if data.get('role') == 'system_administrator' and current_user.role != 'system_administrator':
        return jsonify({
            'error': 'Access denied. Only System Administrators can assign the system administrator role.'
        }), 403
    
    try:
        # Update basic fields
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.full_name = data.get('full_name', user.full_name)
        user.designation = data.get('designation', user.designation)
        user.phone = data.get('phone', user.phone)
        user.address = data.get('address', user.address)
        user.department = data.get('department', user.department)
        
        # Update full name if first/last names changed
        if data.get('first_name') or data.get('last_name'):
            first_name = data.get('first_name', user.first_name) or ''
            last_name = data.get('last_name', user.last_name) or ''
            user.full_name = f"{first_name} {last_name}".strip()
        
        # Only allow role and permission changes if user is not protected or is editing themselves
        # OR if current user is Muhammad Mamoon (MM001) who can edit protected users
        if not user.is_protected or user.id == current_user.id or current_user.username == 'MM001':
            user.role = data.get('role', user.role)
            user.is_active = data.get('is_active', user.is_active)
            user.navigation_permissions = data.get('navigation_permissions', user.navigation_permissions)
            
            # Only Muhammad Mamoon can change protected status
            if current_user.username == 'MM001' and 'is_protected' in data:
                user.is_protected = data.get('is_protected', user.is_protected)
        
        # Handle password changes
        if data.get('password'):
            # For protected users, verify identity first (unless it's Muhammad Mamoon editing others)
            if user.is_protected and user.id == current_user.id:
                verification_code = data.get('verification_code')
                if not verification_code or verification_code != user.verification_code:
                    return jsonify({
                        'error': 'Invalid verification code for protected user'
                    }), 403
            # Muhammad Mamoon can change passwords for any user without verification
            elif user.is_protected and current_user.username != 'MM001':
                return jsonify({
                    'error': 'Only the user themselves or Muhammad Mamoon can change protected user passwords'
                }), 403
            user.set_password(data['password'])
            user.requires_password_change = False
        
        db.session.commit()
        
        log_audit('update', 'user', user.id, {
            'username': user.username,
            'role': user.role
        })
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Change password for current user"""
    data = request.get_json()
    
    try:
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        verification_code = data.get('verification_code')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # For protected users, verify identity
        if current_user.is_protected:
            if not verification_code or verification_code != current_user.verification_code:
                return jsonify({'error': 'Invalid verification code for protected user'}), 403
        
        # Update password
        current_user.set_password(new_password)
        current_user.requires_password_change = False
        db.session.commit()
        
        log_audit('update', 'user_password', current_user.id, {
            'username': current_user.username
        })
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/change-password-required')
@login_required
def change_password_required():
    """Show password change required page"""
    if not current_user.requires_password_change:
        return redirect(url_for('dashboard.index'))
    return render_template('auth/change_password_required.html')

@bp.route('/api/navigation-permissions')
@login_required
@require_permissions('admin.view')
def get_navigation_permissions():
    """Get available navigation permissions"""
    permissions = [
        {'value': 'dashboard', 'label': 'Dashboard'},
        {'value': 'pos', 'label': 'POS'},
        {'value': 'menu', 'label': 'Menu'},
        {'value': 'inventory', 'label': 'Inventory'},
        {'value': 'finance', 'label': 'Finance'},
        {'value': 'reports', 'label': 'Reports'},
        {'value': 'admin', 'label': 'Admin'}
    ]
    return jsonify({'permissions': permissions})

@bp.route('/api/timezones')
@login_required
@require_permissions('admin.view')
def get_timezones():
    """Get available timezones for system configuration"""
    import pytz
    
    # Common timezones for Pakistan and surrounding regions
    common_timezones = [
        {'value': 'Asia/Karachi', 'label': 'Asia/Karachi (Pakistan Standard Time)'},
        {'value': 'Asia/Dubai', 'label': 'Asia/Dubai (Gulf Standard Time)'},
        {'value': 'Asia/Kolkata', 'label': 'Asia/Kolkata (India Standard Time)'},
        {'value': 'Asia/Dhaka', 'label': 'Asia/Dhaka (Bangladesh Standard Time)'},
        {'value': 'UTC', 'label': 'UTC (Coordinated Universal Time)'},
    ]
    
    # Get all available timezones
    all_timezones = []
    for tz in pytz.all_timezones:
        try:
            timezone = pytz.timezone(tz)
            all_timezones.append({
                'value': tz,
                'label': f"{tz} ({timezone.zone})"
            })
        except (AttributeError, TypeError):
            continue
    
    # Sort all timezones alphabetically
    all_timezones.sort(key=lambda x: x['value'])
    
    return jsonify({
        'common_timezones': common_timezones,
        'all_timezones': all_timezones,
        'current_timezone': SystemSetting.get_setting('timezone', 'Asia/Karachi')
    })

@bp.route('/api/timezone-info')
@login_required
@require_permissions('admin.view')
def get_timezone_info():
    """Get current timezone information"""
    try:
        from app.utils.timezone_utils import get_timezone_info
        info = get_timezone_info()
        return jsonify({
            'success': True,
            'timezone_info': {
                'timezone': info['timezone'],
                'current_time': info['current_time'].isoformat(),
                'utc_offset': info['utc_offset'],
                'timezone_name': info['timezone_name']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/next-employee-id')
@login_required
@require_permissions('admin.view')
def get_next_employee_id():
    """Get the next employee ID for username generation"""
    next_id = User.generate_next_employee_id()
    return jsonify({'employee_id': next_id})

@bp.route('/api/stats')
@login_required
@require_permissions('admin.view')
def get_system_stats():
    """Get system statistics for admin dashboard"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        from app.models import MenuItem, InventoryItem, Expense, Sale
        
        # Total users
        total_users = User.query.count()
        
        # Active users (logged in within last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        active_users = User.query.filter(
            User.last_login >= thirty_days_ago
        ).count() if hasattr(User, 'last_login') else 0
        
        # Total menu items
        total_menu_items = MenuItem.query.count()
        
        # Total inventory items
        total_inventory_items = InventoryItem.query.count()
        
        # Low stock items (assuming stock < 10 is low)
        low_stock_items = InventoryItem.query.filter(
            InventoryItem.current_stock < 10
        ).count()
        
        # Today's sales
        today = datetime.now(timezone.utc).date()
        today_sales = db.session.query(func.sum(Sale.total)).filter(
            func.date(Sale.created_at) == today
        ).scalar() or 0
        
        # This month's expenses
        current_month = datetime.now(timezone.utc).replace(day=1)
        month_expenses = db.session.query(func.sum(Expense.amount)).filter(
            Expense.incurred_at >= current_month
        ).scalar() or 0
        
        # Recent audit logs count
        recent_logs = AuditLog.query.filter(
            AuditLog.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
        ).count()
        
        return jsonify({
            'success': True,
            'total_users': total_users,
            'active_users': active_users,
            'total_menu_items': total_menu_items,
            'total_inventory_items': total_inventory_items,
            'low_stock_items': low_stock_items,
            'today_sales': float(today_sales),
            'month_expenses': float(month_expenses),
            'recent_audit_logs': recent_logs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/employee-sync', methods=['POST'])
@login_required
def sync_employee_profile():
    """Sync employee profile data on login"""
    try:
        from datetime import datetime
        # This would typically sync with external HR system
        # For now, just update last login and sync basic profile data
        current_user.last_login = datetime.now(timezone.utc)
        
        # If user requires password change, flag it
        if current_user.requires_password_change:
            db.session.commit()
            return jsonify({
                'success': True,
                'requires_password_change': True,
                'message': 'Password change required'
            })
        
        db.session.commit()
        return jsonify({
            'success': True,
            'user': current_user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/settings')
@login_required
@require_permissions('admin.view')
def list_settings():
    settings = SystemSetting.query.all()
    return jsonify([{
        'id': setting.id,
        'key': setting.key,
        'value': setting.value,
        'description': setting.description,
        'updated_at': setting.updated_at.isoformat() if setting.updated_at else None
    } for setting in settings])

@bp.route('/api/settings/<setting_key>', methods=['PUT'])
@login_required
@require_permissions('admin.edit')
def update_setting(setting_key):
    data = request.get_json()
    
    try:
        SystemSetting.set_setting(
            setting_key, 
            data['value'], 
            data.get('description')
        )
        
        log_audit('update', 'system_setting', None, {
            'key': setting_key,
            'value': data['value']
        })
        
        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/upload-profile-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Upload profile picture for user"""
    try:
        if 'profile_picture' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['profile_picture']
        user_id = request.form.get('user_id')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'error': 'Invalid file type. Only PNG, JPG, JPEG, GIF allowed'}), 400
        
        # Create uploads directory if it doesn't exist
        import os
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        import uuid
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        file.save(file_path)
        
        # Update user profile picture
        if user_id:
            user = User.query.get(user_id)
            if user:
                # Remove old profile picture if exists
                if user.profile_picture:
                    old_file_path = os.path.join(upload_dir, user.profile_picture)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                user.profile_picture = filename
                db.session.commit()
        
        return jsonify({
            'success': True, 
            'filename': filename,
            'message': 'Profile picture uploaded successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/save-settings', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def save_settings():
    data = request.get_json()
    
    try:
        # Define the settings mapping
        settings_mapping = {
            'restaurantName': 'restaurant_name',
            'restaurantSubtitle': 'restaurant_subtitle',
            'copyrightCompany': 'copyright_company',
            'restaurantAddress': 'restaurant_address',
            'restaurantPhone': 'restaurant_phone',
            'restaurantEmail': 'restaurant_email',
            'currency': 'currency',
            'taxRate': 'tax_rate',
            'serviceCharge': 'service_charge',
            'autoTax': 'auto_tax',
            'dateFormat': 'date_format',
            'timeFormat': 'time_format',
            'timezone': 'timezone',
            'language': 'language',
            'notifications': 'notifications',
            'backupFrequency': 'backup_frequency',
            'sessionTimeout': 'session_timeout'
        }
        
        # Save each setting
        for frontend_key, backend_key in settings_mapping.items():
            if frontend_key in data:
                value = data[frontend_key]
                # Handle boolean values properly
                if isinstance(value, bool):
                    value = 'True' if value else 'False'
                SystemSetting.set_setting(backend_key, str(value))
        
        # Check if timezone was updated and trigger sync
        if 'timezone' in data:
            try:
                from app.utils.timezone_utils import sync_existing_records
                sync_existing_records()
            except Exception as e:
                # Log the error but don't fail the settings update
                import logging
                logging.error(f"Failed to sync existing records after timezone update: {str(e)}")
        
        # Log the settings update
        log_audit('update', 'global_settings', None, {
            'updated_settings': list(data.keys())
        })
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@bp.route('/api/audit-logs')
@login_required
@require_permissions('admin.view')
def list_audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    action = request.args.get('action')
    entity = request.args.get('entity')
    
    query = AuditLog.query
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if entity:
        query = query.filter(AuditLog.entity == entity)
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'logs': [log.to_dict() for log in logs.items],
        'total': logs.total,
        'pages': logs.pages,
        'current_page': page
    })

# Configuration for file uploads
UPLOAD_FOLDER = 'app/static/uploads/logos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    """Ensure the upload folder exists"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@bp.route('/api/bill-template/<template_type>')
@login_required
@require_permissions('admin.view')
def get_bill_template(template_type):
    """Get bill template settings"""
    template = BillTemplate.get_template(template_type)
    return jsonify({
        'success': True,
        'template': template.to_dict()
    })

@bp.route('/api/bill-template', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def save_bill_template():
    """Save bill template settings"""
    try:
        data = request.get_json()
        template_type = data.get('template_type', 'receipt')
        
        template = BillTemplate.get_template(template_type)
        
        # Update template fields
        template.header_name = data.get('header_name', template.header_name)
        template.header_tagline = data.get('header_tagline', template.header_tagline)
        template.show_logo = data.get('show_logo', template.show_logo)
        template.show_order_number = data.get('show_order_number', template.show_order_number)
        template.show_date_time = data.get('show_date_time', template.show_date_time)
        template.show_cashier = data.get('show_cashier', template.show_cashier)
        template.show_table = data.get('show_table', template.show_table)
        template.show_tax = data.get('show_tax', template.show_tax)
        template.footer_message = data.get('footer_message', template.footer_message)
        template.show_qr_code = data.get('show_qr_code', template.show_qr_code)
        template.paper_size = data.get('paper_size', template.paper_size)
        template.font_size = data.get('font_size', template.font_size)
        template.auto_cut = data.get('auto_cut', template.auto_cut)
        
        db.session.commit()
        
        log_audit('update', 'bill_template', template.id, {
            'template_type': template_type
        })
        
        return jsonify({
            'success': True,
            'message': 'Bill template saved successfully',
            'template': template.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@bp.route('/api/upload-logo', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def upload_logo():
    """Upload logo for bill template"""
    try:
        if 'logo' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No logo file provided'
            }), 400
        
        file = request.files['logo']
        template_type = request.form.get('template_type', 'receipt')
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400
        
        if file and allowed_file(file.filename):
            ensure_upload_folder()
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
            
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            
            # Update template with logo filename
            template = BillTemplate.get_template(template_type)
            
            # Remove old logo file if exists
            if template.logo_filename:
                old_filepath = os.path.join(UPLOAD_FOLDER, template.logo_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            template.logo_filename = unique_filename
            db.session.commit()
            
            log_audit('update', 'bill_template_logo', template.id, {
                'template_type': template_type,
                'logo_filename': unique_filename
            })
            
            return jsonify({
                'success': True,
                'message': 'Logo uploaded successfully',
                'logo_filename': unique_filename,
                'logo_url': f'/static/uploads/logos/{unique_filename}'
            })
        
        return jsonify({
            'success': False,
            'message': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, or SVG files.'
        }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@bp.route('/api/remove-logo', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def remove_logo():
    """Remove logo from bill template"""
    try:
        data = request.get_json()
        template_type = data.get('template_type', 'receipt')
        
        template = BillTemplate.get_template(template_type)
        
        # Remove logo file if exists
        if template.logo_filename:
            filepath = os.path.join(UPLOAD_FOLDER, template.logo_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        template.logo_filename = None
        db.session.commit()
        
        log_audit('update', 'bill_template', template.id, {
            'action': 'remove_logo',
            'template_type': template_type
        })
        
        return jsonify({
            'success': True,
            'message': 'Logo removed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@bp.route('/bill-preview')
@login_required
@require_permissions('admin.view')
def bill_preview():
    """Generate bill preview page"""
    # Get settings from global settings - ALWAYS use current settings, not saved template
    from app.models import SystemSetting
    business_name = SystemSetting.get_setting('restaurant_name', 'My Business')
    tax_rate = float(SystemSetting.get_setting('tax_rate', '0'))
    
    # Get template data from query parameters
    template_type = request.args.get('template_type', 'receipt')
    # ALWAYS use current business name from global settings, ignore URL parameter
    header_name = business_name
    header_tagline = request.args.get('header_tagline', 'Authentic Pakistani Cuisine')
    show_logo = request.args.get('show_logo', 'false') == 'true'
    show_order_number = request.args.get('show_order_number', 'true') == 'true'
    show_date_time = request.args.get('show_date_time', 'true') == 'true'
    show_cashier = request.args.get('show_cashier', 'true') == 'true'
    show_table = request.args.get('show_table', 'true') == 'true'
    show_tax = request.args.get('show_tax', 'true') == 'true'
    footer_message = request.args.get('footer_message', 'Thank you for visiting!\nPlease come again!')
    show_qr_code = request.args.get('show_qr_code', 'false') == 'true'
    paper_size = request.args.get('paper_size', '80mm')
    font_size = request.args.get('font_size', 'medium')
    logo_filename = request.args.get('logo_filename', '')
    
    # Get current template for logo
    template = BillTemplate.get_template(template_type)
    if not logo_filename and template.logo_filename:
        logo_filename = template.logo_filename
    
    template_data = {
        'template_type': template_type,
        'header_name': header_name,
        'header_tagline': header_tagline,
        'show_logo': show_logo,
        'show_order_number': show_order_number,
        'show_date_time': show_date_time,
        'show_cashier': show_cashier,
        'show_table': show_table,
        'show_tax': show_tax,
        'footer_message': footer_message,
        'show_qr_code': show_qr_code,
        'paper_size': paper_size,
        'font_size': font_size,
        'logo_filename': logo_filename,
        'tax_rate': tax_rate
    }
    
    return render_template('admin/bill_preview.html', **template_data)

@bp.route('/print-bill/<int:sale_id>')
@login_required
@require_permissions('admin.view')
def print_bill(sale_id):
    """Print bill with logo using template settings"""
    try:
        # Get the sale data
        sale = Sale.query.get_or_404(sale_id)
        
        # Get the template (default to receipt)
        template = BillTemplate.get_template('receipt')
        
        return render_template('print/bill_template.html', 
                             bill_data=sale, 
                             template=template)
        
    except Exception as e:
        flash(f'Error generating bill: {str(e)}', 'error')
        return redirect(url_for('admin.index'))

@bp.route('/api/backup-info-test')
def get_backup_info_test():
    """Test endpoint for backup info without authentication"""
    try:
        # Ensure services are initialized
        if not hasattr(backup_service, 'backup_dir') or not backup_service.backup_dir:
            backup_service.init_app(current_app)
        if not hasattr(data_persistence, 'app') or not data_persistence.app:
            data_persistence.init_app(current_app)
            
        backup_info = backup_service.get_backup_info()
        db_stats = data_persistence.get_database_stats()
        
        return jsonify({
            'success': True,
            'backup_info': backup_info,
            'database_stats': db_stats
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in get_backup_info_test: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_details': error_details if current_app.debug else None
        }), 500

@bp.route('/api/backup-info')
@login_required
@require_permissions('admin.view')
def get_backup_info():
    """Get backup information including database size and backup history"""
    try:
        # Ensure services are initialized
        if not hasattr(backup_service, 'backup_dir') or not backup_service.backup_dir:
            backup_service.init_app(current_app)
        if not hasattr(data_persistence, 'app') or not data_persistence.app:
            data_persistence.init_app(current_app)
            
        backup_info = backup_service.get_backup_info()
        db_stats = data_persistence.get_database_stats()
        
        return jsonify({
            'success': True,
            'backup_info': backup_info,
            'database_stats': db_stats
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in get_backup_info: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_details': error_details if current_app.debug else None
        }), 500

@bp.route('/api/create-backup', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def create_backup():
    """Create a new backup of the database"""
    try:
        data = request.get_json() or {}
        backup_name = data.get('backup_name')
        
        # Ensure backup service is initialized
        if not hasattr(backup_service, 'backup_dir') or not backup_service.backup_dir:
            backup_service.init_app(current_app)
        
        success, message, backup_info = backup_service.create_backup(backup_name)
        
        if success:
            log_audit('create', 'backup', None, {
                'backup_filename': backup_info.get('filename'),
                'backup_size': backup_info.get('size')
            })
        
        return jsonify({
            'success': success,
            'message': message,
            'backup_info': backup_info
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in create_backup: {error_details}")
        return jsonify({
            'success': False,
            'message': str(e),
            'error_details': error_details if current_app.debug else None
        }), 500

@bp.route('/api/restore-backup', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def restore_backup():
    """Restore database from uploaded backup file"""
    try:
        if 'backup_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No backup file provided'
            }), 400
        
        file = request.files['backup_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400
        
        if not file.filename.endswith('.zip'):
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Please upload a .zip backup file'
            }), 400
        
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            file.save(temp_file.name)
            temp_filename = os.path.basename(temp_file.name)
        
        # Move to backup directory
        backup_path = os.path.join(backup_service.backup_dir, temp_filename)
        os.rename(temp_file.name, backup_path)
        
        # Restore from backup
        success, message = backup_service.restore_backup(temp_filename)
        
        if success:
            log_audit('restore', 'backup', None, {
                'backup_filename': temp_filename
            })
        
        # Clean up temporary file
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/download-backup/<backup_filename>')
@login_required
@require_permissions('admin.view')
def download_backup(backup_filename):
    """Download a backup file"""
    try:
        backup_path = os.path.join(backup_service.backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            return jsonify({
                'success': False,
                'message': 'Backup file not found'
            }), 404
        
        return send_file(backup_path, as_attachment=True, download_name=backup_filename)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/delete-backup/<backup_filename>', methods=['DELETE'])
@login_required
@require_permissions('admin.edit')
def delete_backup(backup_filename):
    """Delete a backup file"""
    try:
        success, message = backup_service.delete_backup(backup_filename)
        
        if success:
            log_audit('delete', 'backup', None, {
                'backup_filename': backup_filename
            })
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/cleanup-backups', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def cleanup_backups():
    """Clean up old backup files"""
    try:
        data = request.get_json() or {}
        keep_count = data.get('keep_count', 10)
        
        success, message, deleted_count = backup_service.cleanup_old_backups(keep_count)
        
        if success and deleted_count > 0:
            log_audit('cleanup', 'backup', None, {
                'deleted_count': deleted_count,
                'keep_count': keep_count
            })
        
        return jsonify({
            'success': success,
            'message': message,
            'deleted_count': deleted_count
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error cleaning up backups: {str(e)}'
        }), 500

@bp.route('/password-reset-requests')
@login_required
@require_permissions('admin.view')
def password_reset_requests():
    """View all password reset requests - System Administrator only"""
    # Only system administrators can access password reset requests
    if current_user.role != 'system_administrator':
        flash('Access denied. Only System Administrators can manage password reset requests.', 'error')
        return redirect(url_for('dashboard.index'))
    
    from app.models import PasswordResetRequest
    requests = PasswordResetRequest.query.order_by(PasswordResetRequest.requested_at.desc()).all()
    return render_template('admin/password_reset_requests.html', requests=requests)

@bp.route('/api/approve-password-reset', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def approve_password_reset():
    """Approve password reset request and set new password - System Administrator only"""
    # Only system administrators can approve password resets
    if current_user.role != 'system_administrator':
        flash('Access denied. Only System Administrators can approve password resets.', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        from app.models import PasswordResetRequest, User
        
        request_id = request.form.get('request_id')
        new_password = request.form.get('new_password')
        admin_notes = request.form.get('admin_notes', '')
        
        if not request_id or not new_password:
            flash('Request ID and new password are required.', 'error')
            return redirect(url_for('admin.password_reset_requests'))
        
        # Get the reset request
        reset_request = PasswordResetRequest.query.get_or_404(request_id)
        
        if reset_request.status != 'pending':
            flash('This request has already been processed.', 'error')
            return redirect(url_for('admin.password_reset_requests'))
        
        # Get the user
        user = User.query.get(reset_request.user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('admin.password_reset_requests'))
        
        # Set new password
        user.set_password(new_password)
        user.requires_password_change = True  # Force password change on first login
        
        # Update reset request
        reset_request.status = 'approved'
        reset_request.new_password_set = True
        reset_request.approved_at = datetime.now(timezone.utc)
        reset_request.approved_by_id = current_user.id
        reset_request.admin_notes = admin_notes
        reset_request.user_notified = True  # Mark as notified (user will see on login)
        
        db.session.commit()
        
        log_audit('approve_password_reset', 'password_reset_request', reset_request.id, {
            'user_id': user.id,
            'user_email': user.email,
            'approved_by': current_user.full_name
        })
        
        flash(f'Password reset approved for {user.full_name}. New temporary password has been set.', 'success')
        return redirect(url_for('admin.password_reset_requests'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving password reset: {str(e)}', 'error')
        return redirect(url_for('admin.password_reset_requests'))

@bp.route('/account-deletion-requests')
@login_required
@require_permissions('admin.view')
def account_deletion_requests():
    """View all account deletion requests - System Administrator only"""
    # Only system administrators can access account deletion requests
    if current_user.role != 'system_administrator':
        flash('Access denied. Only System Administrators can manage account deletion requests.', 'error')
        return redirect(url_for('dashboard.index'))
    
    from app.models import AccountDeletionRequest
    requests = AccountDeletionRequest.query.order_by(AccountDeletionRequest.requested_at.desc()).all()
    return render_template('admin/account_deletion_requests.html', requests=requests)

@bp.route('/api/request-account-deletion', methods=['POST'])
@login_required
def request_account_deletion():
    """User requests to delete their own account"""
    try:
        from app.models import AccountDeletionRequest
        
        reason = request.form.get('reason', '').strip()
        
        # Check if there's already a pending request
        existing_request = AccountDeletionRequest.query.filter_by(
            user_id=current_user.id,
            status='pending'
        ).first()
        
        if existing_request:
            return jsonify({
                'success': False,
                'message': 'You already have a pending account deletion request.'
            }), 400
        
        # Create deletion request
        deletion_request = AccountDeletionRequest(
            user_id=current_user.id,
            reason=reason,
            status='pending'
        )
        db.session.add(deletion_request)
        db.session.commit()
        
        log_audit('account_deletion_request', 'user', current_user.id, {
            'reason': reason,
            'request_id': deletion_request.id
        })
        
        return jsonify({
            'success': True,
            'message': 'Your account deletion request has been submitted. A System Administrator will review it within 24-48 hours.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error submitting request: {str(e)}'
        }), 500

@bp.route('/api/approve-account-deletion', methods=['POST'])
@login_required
@require_permissions('admin.edit')
def approve_account_deletion():
    """Approve account deletion request and delete user - System Administrator only"""
    # Only system administrators can approve account deletions
    if current_user.role != 'system_administrator':
        flash('Access denied. Only System Administrators can approve account deletions.', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        from app.models import AccountDeletionRequest
        
        request_id = request.form.get('request_id')
        admin_notes = request.form.get('admin_notes', '')
        action = request.form.get('action')  # 'approve' or 'reject'
        
        if not request_id or not action:
            flash('Request ID and action are required.', 'error')
            return redirect(url_for('admin.account_deletion_requests'))
        
        # Get the deletion request
        deletion_request = AccountDeletionRequest.query.get_or_404(request_id)
        
        if deletion_request.status != 'pending':
            flash('This request has already been processed.', 'error')
            return redirect(url_for('admin.account_deletion_requests'))
        
        # Get the user
        user = User.query.get(deletion_request.user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('admin.account_deletion_requests'))
        
        if action == 'reject':
            # Reject the request
            deletion_request.status = 'rejected'
            deletion_request.approved_at = datetime.now(timezone.utc)
            deletion_request.approved_by_id = current_user.id
            deletion_request.admin_notes = admin_notes
            db.session.commit()
            
            flash(f'Account deletion request for {user.full_name} has been rejected.', 'success')
            return redirect(url_for('admin.account_deletion_requests'))
        
        elif action == 'approve':
            # Approve and delete the account
            user_name = user.full_name
            user_email = user.email
            user_id = user.id
            
            # Log the deletion before removing
            log_audit('approve_account_deletion', 'user', user_id, {
                'user_name': user_name,
                'user_email': user_email,
                'approved_by': current_user.full_name,
                'reason': deletion_request.reason
            })
            
            # Delete all related requests first to avoid foreign key constraints
            PasswordResetRequest.query.filter_by(user_id=user_id).delete()
            AccountDeletionRequest.query.filter_by(user_id=user_id).delete()
            
            # Delete the user (this will cascade delete other related data)
            db.session.delete(user)
            db.session.commit()
            
            flash(f'Account for {user_name} ({user_email}) has been permanently deleted from the system.', 'success')
            return redirect(url_for('admin.account_deletion_requests'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing account deletion: {str(e)}', 'error')
        return redirect(url_for('admin.account_deletion_requests'))
