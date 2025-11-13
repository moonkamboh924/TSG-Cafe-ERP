"""
System Administrator Dashboard Blueprint
Separate dashboard for system administrators
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from ...models import Business, User
try:
    from ...models import Sale, Expense, AuditLog
except ImportError:
    Sale = None
    Expense = None
    AuditLog = None
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_dashboard', __name__, url_prefix='/system-admin')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """System Administrator Main Dashboard"""
    return render_template('system_admin/dashboard.html')

@bp.route('/api/stats')
@login_required
@system_admin_api_required
def system_stats():
    """Get system-wide statistics"""
    
    try:
        # Business Statistics
        total_businesses = Business.query.count()
        active_businesses = Business.query.filter_by(is_active=True).count()
        
        # User Statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        
        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_businesses = Business.query.filter(
            Business.created_at >= thirty_days_ago
        ).count()
        
        recent_users = User.query.filter(
            User.created_at >= thirty_days_ago
        ).count()
        
        # Subscription plan distribution
        plan_stats = db.session.query(
            Business.subscription_plan,
            func.count(Business.id).label('count')
        ).group_by(Business.subscription_plan).all()
        
        plan_distribution = {plan: count for plan, count in plan_stats}
        
        # System activity (audit logs from last 7 days)
        system_activity = 0
        if AuditLog is not None:
            try:
                seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
                system_activity = AuditLog.query.filter(
                    AuditLog.created_at >= seven_days_ago
                ).count()
            except Exception as audit_error:
                print(f"Warning: Could not load audit logs: {audit_error}")
                system_activity = 0
        
        # Business growth trend (last 6 months)
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        monthly_growth = []
        
        for i in range(6):
            month_start = datetime.now(timezone.utc) - timedelta(days=30*(i+1))
            month_end = datetime.now(timezone.utc) - timedelta(days=30*i)
            
            month_businesses = Business.query.filter(
                Business.created_at >= month_start,
                Business.created_at < month_end
            ).count()
            
            monthly_growth.insert(0, {
                'month': month_start.strftime('%b %Y'),
                'count': month_businesses
            })
        
        return jsonify({
            'total_businesses': total_businesses,
            'active_businesses': active_businesses,
            'total_users': total_users,
            'active_users': active_users,
            'recent_businesses': recent_businesses,
            'recent_users': recent_users,
            'plan_distribution': plan_distribution,
            'system_activity': system_activity,
            'monthly_growth': monthly_growth
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/system-health')
@login_required
@system_admin_api_required
def system_health():
    """Get system health metrics"""
    
    try:
        # Database health
        db_status = "healthy"  # You can add actual DB health checks here
        
        # Recent errors (if you have error logging)
        recent_errors = 0  # Implement based on your error logging
        
        # System uptime (placeholder)
        uptime = "99.9%"  # Implement based on your monitoring
        
        # Active sessions (approximate)
        active_sessions = User.query.filter_by(is_active=True).count()
        
        return jsonify({
            'database_status': db_status,
            'recent_errors': recent_errors,
            'uptime': uptime,
            'active_sessions': active_sessions,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
