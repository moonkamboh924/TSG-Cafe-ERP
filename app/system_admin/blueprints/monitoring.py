"""
System Monitoring Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta, timezone
from ...models import User, AuditLog, Business
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_monitoring', __name__, url_prefix='/system-admin/monitoring')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """System Monitoring Dashboard"""
    # For now, redirect to main system admin dashboard
    return redirect(url_for('system_admin_dashboard.index'))

@bp.route('/api/system-health')
@login_required
@system_admin_api_required
def system_health():
    """Get real-time system health metrics"""
    
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
@system_admin_api_required
def activity_logs():
    """Get recent system activity logs"""
    
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
