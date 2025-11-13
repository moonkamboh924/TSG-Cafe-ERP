"""
System Analytics Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from ...models import Business, User, Sale, AuditLog
from ...extensions import db

bp = Blueprint('system_admin_analytics', __name__, url_prefix='/system-admin/analytics')

def require_system_admin():
    """Decorator to ensure only system administrators can access"""
    if current_user.role != 'system_administrator':
        return redirect(url_for('dashboard.index'))
    return None

@bp.route('/')
@login_required
def index():
    """System Analytics Dashboard"""
    redirect_response = require_system_admin()
    if redirect_response:
        return redirect_response
    
    # For now, redirect to main system admin dashboard
    return redirect(url_for('system_admin_dashboard.index'))

@bp.route('/api/growth-trends')
@login_required
def growth_trends():
    """Get system growth trends"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Business registration trends (last 12 months)
        business_trends = []
        user_trends = []
        
        for i in range(12):
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
            
            business_trends.insert(0, {
                'month': month_start.strftime('%b %Y'),
                'count': businesses_count
            })
            
            user_trends.insert(0, {
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
def subscription_analytics():
    """Get subscription plan analytics"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
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
