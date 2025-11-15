"""
System Admin User Management Blueprint
Handles all user management for system administrators
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_
from datetime import datetime, timezone

from ...models import Business, User
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required, require_navigation_permission

bp = Blueprint('system_admin_users', __name__, url_prefix='/system-admin/users')

@bp.route('/')
@login_required
@require_system_admin
@require_navigation_permission('user_management')
def index():
    """System Admin User Management Dashboard"""
    return render_template('system_admin/user_management.html')

@bp.route('/api/users')
@login_required
@system_admin_api_required
def get_all_users():
    """Get all users across all businesses for system admin"""
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        status_filter = request.args.get('status', '')
        
        # Base query for system administrator users only (including MM001 and new roles)
        system_admin_roles = ['system_administrator', 'Manager', 'Executive', 'Officer']
        query = db.session.query(User, Business).outerjoin(
            Business, User.business_id == Business.id
        ).filter(User.role.in_(system_admin_roles))
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    User.full_name.ilike(f'%{search}%'),
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.employee_id.ilike(f'%{search}%'),
                    Business.business_name.ilike(f'%{search}%')
                )
            )
        
        # Role filter is redundant since we already filter for system_administrator
        # if role_filter:
        #     query = query.filter(User.role == role_filter)
            
        # Apply status filter
        if status_filter == 'active':
            query = query.filter(User.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(User.is_active == False)
        
        # Order and paginate
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        print(f"DEBUG: Query returned {users.total} total users, {len(users.items)} on this page")
        
        user_list = []
        for user, business in users.items:
            user_data = {
                'id': user.id,
                'employee_id': user.employee_id,
                'username': user.username,
                'full_name': user.full_name,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'designation': user.designation,
                'department': user.department,
                'phone': user.phone,
                'address': user.address,
                'is_active': user.is_active,
                'is_owner': user.is_owner,
                'permissions': user.get_navigation_permissions(),
                'created_at': user.created_at.isoformat(),
                'business': {
                    'id': business.id if business else None,
                    'name': business.business_name if business else 'No Business',
                    'subscription_plan': business.subscription_plan if business else 'N/A'
                } if business else None
            }
            user_list.append(user_data)
        
        # Get all system administrators across all businesses (including new roles)
        system_admin_roles = ['system_administrator', 'Manager', 'Executive', 'Officer']
        all_users = User.query.filter(User.role.in_(system_admin_roles)).all()
        print(f"DEBUG: Found {len(all_users)} system admin users")
        total_users = len(all_users)
        active_users = User.query.filter(User.role.in_(system_admin_roles), User.is_active == True).count()
        
        # Get users by role (only system administrators)
        role_stats = db.session.query(
            User.role,
            func.count(User.id).label('count')
        ).filter(User.role == 'system_administrator').group_by(User.role).all()
        
        role_distribution = {role: count for role, count in role_stats}
        
        return jsonify({
            'users': user_list,
            'total': users.total,
            'pages': users.pages,
            'current_page': page,
            'per_page': per_page,
            'statistics': {
                'total_users': total_users,
                'active_users': active_users,
                'role_distribution': role_distribution
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/stats')
@login_required
@system_admin_api_required
def get_user_stats():
    """Get user statistics for system admin dashboard"""
    
    try:
        # Basic user statistics for system administrators only
        total_users = User.query.filter_by(role='system_administrator').count()
        active_sessions = User.query.filter_by(role='system_administrator', is_active=True).count()
        
        # System health (placeholder)
        system_health = "Good"
        database_size = "0 MB"  # You can implement actual database size calculation
        
        return jsonify({
            'total_users': total_users,
            'active_sessions': active_sessions,
            'system_health': system_health,
            'database_size': database_size
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/create', methods=['POST'])
@login_required
@system_admin_api_required
def create_system_administrator():
    """Create a new system administrator account"""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'full_name', 'email', 'password', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        # Validate role
        valid_roles = ['Manager', 'Executive', 'Officer']
        if data['role'] not in valid_roles:
            return jsonify({'error': f'Role must be one of: {", ".join(valid_roles)}'}), 400
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email address already exists'}), 400
        
        # Check if username already exists (if provided)
        username = data.get('username')
        if username:
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                return jsonify({'error': 'Username already exists'}), 400
        
        # Generate username if not provided
        if not username:
            first_name = data['first_name']
            last_name = data['last_name']
            # Generate username automatically (not editable by users)
            # Pattern: First letter of first name + First letter of last name + Series number
            first_char = data['first_name'][0].upper() if data['first_name'] else 'X'
            last_char = data['last_name'][0].upper() if data['last_name'] else 'X'
            
            # Find next available series number
            base_username = f"{first_char}{last_char}"
            counter = 1
            while True:
                test_username = f"{base_username}{counter}"
                if not User.query.filter_by(username=test_username).first():
                    username = test_username
                    break
                counter += 1
        
        # Generate employee ID for system administrators
        employee_id = None
        if not employee_id:
            # Count existing system administrators to generate next ID
            system_admin_roles = ['system_administrator', 'Manager', 'Executive', 'Officer']
            system_admin_count = User.query.filter(User.role.in_(system_admin_roles)).count()
            employee_id = f"SYS{system_admin_count + 2:03d}"
        
        # Set default password if not provided
        password = data.get('password', '1234@1234')
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Create new system administrator
        new_admin = User(
            username=username,
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            full_name=data['full_name'],  # Use manually entered full name
            phone=data.get('phone'),
            designation=data.get('designation'),
            department=data.get('department'),
            address=data.get('address'),
            role=data['role'],  # Use selected role: Manager, Executive, or Officer
            is_active=True,
            requires_password_change=False,  # Set to False for system admins
            email_verified=True  # System admins are pre-verified
        )
        
        # Set password
        new_admin.set_password(data['password'])
        
        # Set navigation permissions based on user selection
        permissions = data.get('permissions', [])
        if not permissions:
            # Default system administrator permissions if none specified
            permissions = ['user_management', 'business_management', 'subscription_management', 'system_settings', 'system_analytics', 'monitoring', 'reports']
        
        # Always add system_dashboard permission for all system administrators
        if 'system_dashboard' not in permissions:
            permissions.insert(0, 'system_dashboard')
        
        new_admin.set_navigation_permissions(permissions)
        
        db.session.add(new_admin)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'System administrator created successfully',
            'user': {
                'id': new_admin.id,
                'username': new_admin.username,
                'email': new_admin.email,
                'full_name': new_admin.full_name,
                'employee_id': new_admin.employee_id,
                'designation': new_admin.designation,
                'department': new_admin.department,
                'is_active': new_admin.is_active,
                'is_protected': new_admin.is_protected,
                'permissions': new_admin.get_navigation_permissions()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/delete/<int:user_id>', methods=['DELETE'])
@login_required
@system_admin_api_required
def delete_system_administrator(user_id):
    """Delete a system administrator account"""
    
    try:
        # Find the user to delete
        user_to_delete = User.query.filter_by(
            id=user_id, 
            role='system_administrator'
        ).first()
        
        if not user_to_delete:
            return jsonify({'error': 'System administrator not found'}), 404
        
        # Prevent deletion of the main system administrator (MM001)
        if user_to_delete.username == 'MM001':
            return jsonify({'error': 'Cannot delete the main system administrator account (MM001)'}), 403
        
        # Prevent users from deleting themselves
        if user_to_delete.id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 403
        
        # Store user info for logging
        deleted_username = user_to_delete.username
        deleted_email = user_to_delete.email
        
        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'System administrator "{deleted_username}" deleted successfully',
            'deleted_user': {
                'username': deleted_username,
                'email': deleted_email
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/user/<int:user_id>')
@login_required
@system_admin_api_required
def get_system_administrator(user_id):
    """Get a single system administrator by ID"""
    
    try:
        user = User.query.filter_by(
            id=user_id, 
            role='system_administrator'
        ).first()
        
        if not user:
            return jsonify({'error': 'System administrator not found'}), 404
        
        # Prevent editing MM001 account
        if user.username == 'MM001':
            return jsonify({'error': 'MM001 account cannot be edited - this is a protected system account'}), 403
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name,
            'employee_id': user.employee_id,
            'designation': user.designation,
            'department': user.department,
            'phone': user.phone,
            'address': user.address,
            'is_active': user.is_active,
            'is_protected': user.is_protected,
            'permissions': user.get_navigation_permissions(),
            'created_at': user.created_at.isoformat()
        }
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/update/<int:user_id>', methods=['PUT'])
@login_required
@system_admin_api_required
def update_system_administrator(user_id):
    """Update a system administrator account"""
    
    try:
        data = request.get_json()
        
        # Find the user to update
        user_to_update = User.query.filter_by(
            id=user_id, 
            role='system_administrator'
        ).first()
        
        if not user_to_update:
            return jsonify({'error': 'System administrator not found'}), 404
        
        # Prevent updating MM001 account
        if user_to_update.username == 'MM001':
            return jsonify({'error': 'MM001 account cannot be modified - this is a protected system account with fixed permissions'}), 403
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'full_name', 'email', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        # Validate role
        valid_roles = ['Manager', 'Executive', 'Officer']
        if data['role'] not in valid_roles:
            return jsonify({'error': f'Role must be one of: {", ".join(valid_roles)}'}), 400
        
        # Check if email already exists (excluding current user)
        existing_user = User.query.filter(
            User.email == data['email'],
            User.id != user_id
        ).first()
        if existing_user:
            return jsonify({'error': 'Email address already exists'}), 400
        
        # Update user fields (username is NOT editable)
        user_to_update.first_name = data['first_name']
        user_to_update.last_name = data['last_name']
        user_to_update.email = data['email']
        user_to_update.phone = data.get('phone')
        user_to_update.role = data['role']
        user_to_update.designation = data.get('designation')
        user_to_update.department = data.get('department')
        user_to_update.address = data.get('address')
        user_to_update.full_name = data['full_name']  # Use manually entered full name
        # Note: Username is never updated - it's permanent once created
        
        # Update account settings (only if user has permission)
        if current_user.username == 'MM001' or current_user.id == user_to_update.id:
            user_to_update.is_active = data.get('is_active', user_to_update.is_active)
            if current_user.username == 'MM001':  # Only MM001 can change protected status
                user_to_update.is_protected = data.get('is_protected', user_to_update.is_protected)
        
        # Update navigation permissions
        permissions = data.get('permissions', [])
        if permissions:
            # Always add system_dashboard permission for all system administrators
            if 'system_dashboard' not in permissions:
                permissions.insert(0, 'system_dashboard')
            user_to_update.set_navigation_permissions(permissions)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'System administrator updated successfully',
            'user': {
                'id': user_to_update.id,
                'username': user_to_update.username,
                'email': user_to_update.email,
                'full_name': user_to_update.full_name,
                'designation': user_to_update.designation,
                'department': user_to_update.department,
                'is_active': user_to_update.is_active,
                'is_protected': user_to_update.is_protected
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
