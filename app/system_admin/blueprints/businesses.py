"""
Business Management Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from datetime import datetime, timezone
from sqlalchemy import func, or_
from ...models import (
    Business,
    User,
    Sale,
    Expense,
    DailyClosing,
    PasswordResetRequest,
    AccountDeletionRequest,
    AuditLog,
    CreditSale,
    CreditPayment,
)
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_businesses', __name__, url_prefix='/system-admin/businesses')


def _cleanup_user_associations(user):
    """Detach related records before deleting a user to avoid FK errors"""
    Business.query.filter_by(owner_id=user.id).update({'owner_id': None})
    Sale.query.filter_by(user_id=user.id).update({'user_id': None})
    Expense.query.filter_by(user_id=user.id).update({'user_id': None})
    DailyClosing.query.filter_by(user_id=user.id).update({'user_id': None})
    AuditLog.query.filter_by(user_id=user.id).update({'user_id': None})
    CreditSale.query.filter_by(created_by=user.id).update({'created_by': None})
    CreditPayment.query.filter_by(received_by=user.id).update({'received_by': None})
    PasswordResetRequest.query.filter_by(user_id=user.id).delete()
    AccountDeletionRequest.query.filter_by(user_id=user.id).delete()
    PasswordResetRequest.query.filter_by(approved_by_id=user.id).update({'approved_by_id': None})
    AccountDeletionRequest.query.filter_by(approved_by_id=user.id).update({'approved_by_id': None})

@bp.route('/')
@login_required
@require_system_admin
def index():
    """Business Management Dashboard"""
    # Load key stats for header cards
    total_businesses = Business.query.count()
    active_businesses = Business.query.filter_by(is_active=True).count()
    recent_businesses = Business.query.order_by(Business.created_at.desc()).limit(5).all()

    return render_template(
        'system_admin/business_management.html',
        total_businesses=total_businesses,
        active_businesses=active_businesses,
        recent_businesses=recent_businesses,
    )

@bp.route('/employee-details')
@login_required
@require_system_admin
def employee_details():
    """Employee Details Dashboard"""
    # Redirect to main dashboard since employee details are integrated there
    from flask import redirect, url_for
    return redirect(url_for('system_admin_dashboard.index'))

@bp.route('/api/employee-details')
@login_required
@system_admin_api_required
def get_employee_details():
    """Get detailed employee information across all businesses"""
    
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


@bp.route('/api/<int:business_id>/users/<int:user_id>', methods=['DELETE'])
@login_required
@system_admin_api_required
def remove_user_from_business(business_id, user_id):
    """Detach a user from a specific business"""
    try:
        user = User.query.filter_by(id=user_id, business_id=business_id).first()
        if not user:
            return jsonify({'error': 'User not found for this business'}), 404

        _cleanup_user_associations(user)
        user.business_id = None
        user.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'User {user.full_name} removed from business',
            'business': {
                'id': business_id,
                'business_name': Business.query.get(business_id).business_name
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/<int:business_id>/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@system_admin_api_required
def toggle_business_user_status(business_id, user_id):
    try:
        user = User.query.filter_by(id=user_id, business_id=business_id).first()
        if not user:
            return jsonify({'error': 'User not found for this business'}), 404

        user.is_active = not user.is_active
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def _serialize_businesses():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip().lower()

    # Get businesses with user counts
    businesses_query = db.session.query(
        Business,
        func.count(User.id).label('user_count')
    ).outerjoin(User, Business.id == User.business_id)

    if search:
        like = f"%{search}%"
        businesses_query = businesses_query.filter(
            or_(
                Business.business_name.ilike(like),
                Business.owner_email.ilike(like),
                Business.subscription_plan.ilike(like)
            )
        )

    if status == 'active':
        businesses_query = businesses_query.filter(Business.is_active.is_(True))
    elif status == 'inactive':
        businesses_query = businesses_query.filter(Business.is_active.is_(False))

    businesses_query = businesses_query.group_by(Business.id).order_by(Business.created_at.desc())

    businesses = businesses_query.paginate(page=page, per_page=per_page, error_out=False)

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

    return {
        'businesses': business_list,
        'total': businesses.total,
        'pages': businesses.pages,
        'current_page': page,
        'per_page': per_page
    }


@bp.route('/api/businesses')
@login_required
@system_admin_api_required
def list_businesses():
    """Get all businesses with detailed information"""
    try:
        data = _serialize_businesses()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/list')
@login_required
@system_admin_api_required
def list_businesses_alias():
    return list_businesses()


@bp.route('/api/businesses/<int:business_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@system_admin_api_required
def manage_business(business_id):
    business = Business.query.get_or_404(business_id)

    if request.method == 'GET':
        user_count = User.query.filter_by(business_id=business_id).count()
        return jsonify({
            'business': {
                'id': business.id,
                'business_name': business.business_name,
                'owner_email': business.owner_email,
                'subscription_plan': business.subscription_plan,
                'is_active': business.is_active,
                'created_at': business.created_at.isoformat(),
                'updated_at': business.updated_at.isoformat() if business.updated_at else None,
                'user_count': user_count
            }
        })

    if request.method == 'PUT':
        data = request.get_json() or {}

        name = data.get('business_name')
        email = data.get('owner_email')
        plan = data.get('subscription_plan')
        is_active = data.get('is_active')

        if name:
            existing = Business.query.filter(
                Business.business_name == name,
                Business.id != business_id
            ).first()
            if existing:
                return jsonify({'error': 'Business name already exists'}), 400
            business.business_name = name.strip()

        if email:
            existing_email = Business.query.filter(
                Business.owner_email == email,
                Business.id != business_id
            ).first()
            if existing_email:
                return jsonify({'error': 'Owner email already in use'}), 400
            business.owner_email = email.strip()

        if plan:
            business.subscription_plan = plan.strip()

        if is_active is not None:
            if isinstance(is_active, str):
                is_active = is_active.lower() == 'true'
            business.is_active = bool(is_active)

        business.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Business updated successfully'})

    # DELETE flow
    try:
        users = User.query.filter_by(business_id=business_id).all()
        for user in users:
            _cleanup_user_associations(user)
            user.business_id = None

        db.session.delete(business)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Business deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/businesses/<int:business_id>/toggle-status', methods=['POST'])
@login_required
@system_admin_api_required
def toggle_business_status(business_id):
    """Toggle business active status"""
    
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

@bp.route('/api/businesses/<int:business_id>/users')
@login_required
@system_admin_api_required
def get_business_users(business_id):
    """Get users for a specific business"""
    
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
