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
from ...utils.system_monitor import SystemMonitor
from ...middleware import get_average_response_time

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
        
        # User Statistics (excluding system administrators)
        total_users = User.query.filter(User.role != 'system_administrator').count()
        active_users = User.query.filter(
            User.is_active == True,
            User.role != 'system_administrator'
        ).count()
        
        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_businesses = Business.query.filter(
            Business.created_at >= thirty_days_ago
        ).count()
        
        recent_users = User.query.filter(
            User.created_at >= thirty_days_ago,
            User.role != 'system_administrator'
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
        
        # Generate months in chronological order (oldest to newest)
        for i in range(5, -1, -1):  # 5 down to 0 for correct order
            month_start = datetime.now(timezone.utc) - timedelta(days=30*(i+1))
            month_end = datetime.now(timezone.utc) - timedelta(days=30*i)
            
            month_businesses = Business.query.filter(
                Business.created_at >= month_start,
                Business.created_at < month_end
            ).count()
            
            monthly_growth.append({
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
        # Get system resource stats
        system_stats = SystemMonitor.get_system_stats()
        
        # Database health
        db_status = "healthy"
        try:
            db.session.execute(db.text('SELECT 1'))
        except:
            db_status = "error"
        
        # Recent errors (if you have error logging)
        recent_errors = 0  # Implement based on your error logging
        
        # Active sessions (approximate)
        active_sessions = User.query.filter_by(is_active=True).count()
        
        # Average response time
        avg_response_time = get_average_response_time()
        
        return jsonify({
            'database_status': db_status,
            'recent_errors': recent_errors,
            'uptime': system_stats['uptime'],
            'cpu_usage': system_stats['cpu'],
            'memory_usage': system_stats['memory'],
            'disk_usage': system_stats['disk'],
            'avg_response_time': avg_response_time,
            'active_sessions': active_sessions,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

