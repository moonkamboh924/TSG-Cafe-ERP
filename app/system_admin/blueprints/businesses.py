"""
Business Management Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import func
from ...models import Business, User
from ...extensions import db

bp = Blueprint('system_admin_businesses', __name__, url_prefix='/system-admin/businesses')

def require_system_admin():
    """Decorator to ensure only system administrators can access"""
    if current_user.role != 'system_administrator':
        return redirect(url_for('dashboard.index'))
    return None

@bp.route('/')
@login_required
def index():
    """Business Management Dashboard"""
    redirect_response = require_system_admin()
    if redirect_response:
        return redirect_response
    
    # For now, redirect to main system admin dashboard
    return redirect(url_for('system_admin_dashboard.index'))

@bp.route('/employee-details')
@login_required
def employee_details():
    """Employee Details Dashboard"""
    redirect_response = require_system_admin()
    if redirect_response:
        return redirect_response
    
    return render_template('system_admin/employee_details.html')

@bp.route('/api/employee-details')
@login_required
def get_employee_details():
    """Get detailed employee information across all businesses"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        search = request.args.get('search', '')
        business_filter = request.args.get('business_id', '')
        
        # Base query for all users with business information
        query = db.session.query(User, Business).join(
            Business, User.business_id == Business.id, isouter=True
        )
        
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
        
        # Apply business filter
        if business_filter:
            query = query.filter(User.business_id == business_filter)
        
        # Order and paginate
        employees = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        employee_list = []
        for user, business in employees.items:
            employee_data = {
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
                'last_login': user.last_login.isoformat() if hasattr(user, 'last_login') and user.last_login else None,
                'business': {
                    'id': business.id if business else None,
                    'name': business.business_name if business else 'No Business',
                    'subscription_plan': business.subscription_plan if business else 'N/A'
                } if business else None
            }
            employee_list.append(employee_data)
        
        # Get summary statistics
        total_employees = User.query.count()
        active_employees = User.query.filter_by(is_active=True).count()
        
        # Get employees by role
        role_stats = db.session.query(
            User.role,
            func.count(User.id).label('count')
        ).group_by(User.role).all()
        
        role_distribution = {role: count for role, count in role_stats}
        
        return jsonify({
            'employees': employee_list,
            'total': employees.total,
            'pages': employees.pages,
            'current_page': page,
            'per_page': per_page,
            'statistics': {
                'total_employees': total_employees,
                'active_employees': active_employees,
                'role_distribution': role_distribution
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/list')
@login_required
def list_businesses():
    """Get all businesses with detailed information"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        
        # Get businesses with user counts
        businesses_query = db.session.query(
            Business,
            func.count(User.id).label('user_count')
        ).outerjoin(User, Business.id == User.business_id)\
         .group_by(Business.id)\
         .order_by(Business.created_at.desc())
        
        businesses = businesses_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        business_list = []
        for business, user_count in businesses.items:
            business_list.append({
                'id': business.id,
                'business_name': business.business_name,
                'owner_email': business.owner_email,
                'subscription_plan': business.subscription_plan,
                'is_active': business.is_active,
                'created_at': business.created_at.isoformat(),
                'updated_at': business.updated_at.isoformat() if business.updated_at else None,
                'user_count': user_count
            })
        
        return jsonify({
            'businesses': business_list,
            'total': businesses.total,
            'pages': businesses.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/<int:business_id>/toggle-status', methods=['POST'])
@login_required
def toggle_business_status(business_id):
    """Toggle business active status"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        business = Business.query.get_or_404(business_id)
        business.is_active = not business.is_active
        business.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Business {"activated" if business.is_active else "deactivated"} successfully',
            'is_active': business.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/<int:business_id>/users')
@login_required
def get_business_users(business_id):
    """Get users for a specific business"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        business = Business.query.get_or_404(business_id)
        users = User.query.filter_by(business_id=business_id).all()
        
        users_list = []
        for user in users:
            users_list.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat()
            })
        
        return jsonify({
            'business': {
                'id': business.id,
                'name': business.business_name,
                'owner_email': business.owner_email
            },
            'users': users_list,
            'total_users': len(users_list)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
