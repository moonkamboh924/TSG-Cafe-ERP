"""
System Analytics Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from ...models import Business, User, Sale, AuditLog
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_analytics', __name__, url_prefix='/system-admin/analytics')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """System Analytics Dashboard"""
    return render_template('system_admin/analytics.html')

@bp.route('/api/growth-trends')
@login_required
@system_admin_api_required
def growth_trends():
    """Get system growth trends"""
    
    try:
        # Business registration trends (last 12 months)
        business_trends = []
        user_trends = []
        
        # Generate months in chronological order (oldest to newest)
        for i in range(11, -1, -1):  # 11 down to 0 for correct order
            month_start = datetime.now(timezone.utc).replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            businesses_count = Business.query.filter(
                Business.created_at >= month_start,
                Business.created_at <= month_end
            ).count()
            
            users_count = User.query.filter(
                User.created_at >= month_start,
                User.created_at <= month_end
            ).count()
            
            business_trends.append({
                'month': month_start.strftime('%b %Y'),
                'count': businesses_count
            })
            
            user_trends.append({
                'month': month_start.strftime('%b %Y'),
                'count': users_count
            })
        
        return jsonify({
            'business_trends': business_trends,
            'user_trends': user_trends
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/subscription-analytics')
@login_required
@system_admin_api_required
def subscription_analytics():
    """Get subscription plan analytics"""
    
    try:
        # Current subscription distribution
        plan_distribution = db.session.query(
            Business.subscription_plan,
            func.count(Business.id).label('count')
        ).group_by(Business.subscription_plan).all()
        
        # Plan upgrade/downgrade trends (if you track plan changes)
        # This would require a plan_changes table to track history
        
        return jsonify({
            'plan_distribution': {plan: count for plan, count in plan_distribution},
            'total_businesses': sum(count for _, count in plan_distribution)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/stats')
@login_required
@system_admin_api_required
def system_stats():
    """Get overall system statistics"""
    
    try:
        # Total counts
        total_businesses = Business.query.count()
        total_users = User.query.count()
        
        # Active businesses (with subscription end date in future)
        active_businesses = Business.query.filter(
            Business.subscription_end_date >= datetime.now(timezone.utc)
        ).count()
        
        # Plan distribution
        plan_distribution = db.session.query(
            Business.subscription_plan,
            func.count(Business.id).label('count')
        ).group_by(Business.subscription_plan).all()
        
        return jsonify({
            'total_businesses': total_businesses,
            'total_users': total_users,
            'active_businesses': active_businesses,
            'plan_distribution': {plan: count for plan, count in plan_distribution}
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/top-businesses')
@login_required
@system_admin_api_required
def top_businesses():
    """Get top businesses by activity"""
    
    try:
        # Get businesses with most sales/activity
        top_businesses_data = db.session.query(
            Business.name,
            Business.subscription_plan,
            func.count(Sale.id).label('activity_count')
        ).outerjoin(
            User, Business.id == User.business_id
        ).outerjoin(
            Sale, User.id == Sale.user_id
        ).group_by(
            Business.id, Business.name, Business.subscription_plan
        ).order_by(
            func.count(Sale.id).desc()
        ).limit(5).all()
        
        # Calculate activity percentage (relative to most active)
        max_activity = top_businesses_data[0].activity_count if top_businesses_data else 1
        max_activity = max(max_activity, 1)  # Avoid division by zero
        
        result = []
        for business in top_businesses_data:
            activity_percentage = int((business.activity_count / max_activity) * 100)
            result.append({
                'name': business.name,
                'plan': business.subscription_plan or 'basic',
                'activity': activity_percentage
            })
        
        return jsonify({'businesses': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
