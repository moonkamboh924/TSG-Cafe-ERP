"""
System Monitoring Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from ...models import Business, User, AuditLog
from ...extensions import db

bp = Blueprint('system_admin_monitoring', __name__, url_prefix='/system-admin/monitoring')

def require_system_admin():
    """Decorator to ensure only system administrators can access"""
    if current_user.role != 'system_administrator':
        return redirect(url_for('dashboard.index'))
    return None

@bp.route('/')
@login_required
def index():
    """System Monitoring Dashboard"""
    redirect_response = require_system_admin()
    if redirect_response:
        return redirect_response
    
    # For now, redirect to main system admin dashboard
    return redirect(url_for('system_admin_dashboard.index'))

@bp.route('/api/system-health')
@login_required
def system_health():
    """Get real-time system health metrics"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Database connectivity
        db_healthy = True
        try:
            db.session.execute('SELECT 1')
        except:
            db_healthy = False
        
        # Active users in last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        active_users = User.query.filter(
            User.last_login >= one_hour_ago
        ).count() if hasattr(User, 'last_login') else 0
        
        # System activity in last 24 hours
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_activity = AuditLog.query.filter(
            AuditLog.created_at >= twenty_four_hours_ago
        ).count()
        
        # Error rate (placeholder - implement based on your error logging)
        error_rate = 0.1  # 0.1% error rate
        
        return jsonify({
            'database_healthy': db_healthy,
            'active_users': active_users,
            'recent_activity': recent_activity,
            'error_rate': error_rate,
            'uptime': 99.9,  # Placeholder
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/activity-logs')
@login_required
def activity_logs():
    """Get recent system activity logs"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get recent audit logs
        logs = AuditLog.query.order_by(
            AuditLog.created_at.desc()
        ).limit(100).all()
        
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'action': log.action,
                'entity': log.entity,
                'entity_id': log.entity_id,
                'user_id': log.user_id,
                'business_id': log.business_id,
                'details': log.details,
                'created_at': log.created_at.isoformat()
            })
        
        return jsonify({
            'logs': logs_data,
            'total': len(logs_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
