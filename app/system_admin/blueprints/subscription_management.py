"""
System Admin Subscription Management Blueprint
Handles subscription management for all businesses
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models import Business, User
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_subscriptions', __name__, url_prefix='/system-admin/subscriptions')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """Subscription Management Dashboard"""
    return render_template('system_admin/subscription_management.html')

@bp.route('/api/subscriptions')
@login_required
@system_admin_api_required
def get_subscriptions():
    """Get subscription data for all businesses"""
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        search = request.args.get('search', '', type=str)
        plan_filter = request.args.get('plan', '', type=str)
        status_filter = request.args.get('status', '', type=str)
        
        # Base query for all businesses
        query = Business.query
        
        # Apply search filter
        if search:
            query = query.filter(
                Business.business_name.ilike(f'%{search}%')
            )
        
        # Apply plan filter
        if plan_filter:
            query = query.filter(Business.subscription_plan == plan_filter)
        
        # Apply status filter
        if status_filter:
            if status_filter == 'active':
                query = query.filter(Business.is_active == True)
            elif status_filter == 'inactive':
                query = query.filter(Business.is_active == False)
        
        # Order by creation date
        query = query.order_by(desc(Business.created_at))
        
        # Paginate results
        businesses = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        business_list = []
        for business in businesses.items:
            # Get business owner
            owner = User.query.filter_by(business_id=business.id, is_owner=True).first()
            
            business_data = {
                'id': business.id,
                'business_name': business.business_name,
                'subscription_plan': business.subscription_plan,
                'is_active': business.is_active,
                'created_at': business.created_at.isoformat(),
                'owner': {
                    'name': owner.full_name if owner else 'No Owner',
                    'email': owner.email if owner else 'N/A',
                    'username': owner.username if owner else 'N/A'
                } if owner else None
            }
            business_list.append(business_data)
        
        # Get summary statistics
        total_businesses = Business.query.count()
        active_businesses = Business.query.filter_by(is_active=True).count()
        
        # Get subscription plan distribution
        plan_stats = db.session.query(
            Business.subscription_plan,
            func.count(Business.id).label('count')
        ).group_by(Business.subscription_plan).all()
        
        plan_distribution = {plan: count for plan, count in plan_stats}
        
        return jsonify({
            'businesses': business_list,
            'total': businesses.total,
            'pages': businesses.pages,
            'current_page': page,
            'per_page': per_page,
            'statistics': {
                'total_businesses': total_businesses,
                'active_businesses': active_businesses,
                'plan_distribution': plan_distribution
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/stats')
@login_required
@system_admin_api_required
def subscription_stats():
    """Get subscription statistics"""
    
    try:
        # Basic subscription statistics
        total_subscriptions = Business.query.count()
        active_subscriptions = Business.query.filter_by(is_active=True).count()
        
        # Plan distribution
        plan_stats = db.session.query(
            Business.subscription_plan,
            func.count(Business.id).label('count')
        ).group_by(Business.subscription_plan).all()
        
        plan_distribution = {plan: count for plan, count in plan_stats}
        
        # Recent subscriptions (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_subscriptions = Business.query.filter(
            Business.created_at >= thirty_days_ago
        ).count()
        
        return jsonify({
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'plan_distribution': plan_distribution,
            'recent_subscriptions': recent_subscriptions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
