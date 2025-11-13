"""
System Admin User Management Blueprint
Handles all user management for system administrators
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from datetime import datetime, timezone
from sqlalchemy import func
from ...models import Business, User
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_users', __name__, url_prefix='/system-admin/users')

@bp.route('/')
@login_required
@require_system_admin
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
        
        # Base query for system administrator users only
        query = db.session.query(User, Business).outerjoin(
            Business, User.business_id == Business.id
        ).filter(User.role == 'system_administrator')
        
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
                'created_at': user.created_at.isoformat(),
                'business': {
                    'id': business.id if business else None,
                    'name': business.business_name if business else 'No Business',
                    'subscription_plan': business.subscription_plan if business else 'N/A'
                } if business else None
            }
            user_list.append(user_data)
        
        # Get summary statistics for system administrators only
        total_users = User.query.filter_by(role='system_administrator').count()
        active_users = User.query.filter_by(role='system_administrator', is_active=True).count()
        
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
