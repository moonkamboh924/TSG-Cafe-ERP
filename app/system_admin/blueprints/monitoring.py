"""
System Monitoring Blueprint for System Administrators
"""

from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta, timezone
from ...models import User, AuditLog, Business, SystemMetric
from ...extensions import db
from ..decorators import require_system_admin, system_admin_api_required
from ...utils.system_monitor import SystemMonitor
from ...middleware import get_average_response_time
from sqlalchemy import func

bp = Blueprint('system_admin_monitoring', __name__, url_prefix='/system-admin/monitoring')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """System Monitoring Dashboard"""
    return render_template('system_admin/monitoring.html')

@bp.route('/api/system-health')
@login_required
@system_admin_api_required
def system_health():
    """Get real-time system health metrics"""
    
    try:
        # Database connectivity
        db_healthy = True
        try:
            db.session.execute(db.text('SELECT 1'))
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
        
        # Get system resource stats
        system_stats = SystemMonitor.get_system_stats()
        
        # Average response time
        avg_response_time = get_average_response_time()
        
        return jsonify({
            'database_healthy': db_healthy,
            'active_users': active_users,
            'recent_activity': recent_activity,
            'cpu_usage': system_stats['cpu'],
            'memory_usage': system_stats['memory'],
            'disk_usage': system_stats['disk'],
            'uptime': system_stats['uptime'],
            'avg_response_time': avg_response_time,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/system-metrics')
@login_required
@system_admin_api_required
def system_metrics():
    """Get real-time system metrics"""
    
    try:
        # Daily logins (last 24 hours)
        daily_logins = SystemMetric.get_metric('daily_logins', days=1)
        
        # API requests (last 7 days)
        api_requests = SystemMetric.get_metric('api_requests', days=7)
        
        # Database queries (performance metrics)
        db_queries = SystemMetric.get_metric('db_queries', days=1)
        
        # Active sessions (users logged in within last hour)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        active_sessions = User.query.filter(
            User.last_login >= one_hour_ago
        ).count()
        
        # Get breakdown by metric type for last 7 days
        seven_days_ago = datetime.now(timezone.utc).date() - timedelta(days=6)
        metrics_breakdown = db.session.query(
            SystemMetric.metric_date,
            SystemMetric.metric_type,
            func.sum(SystemMetric.metric_value).label('total')
        ).filter(
            SystemMetric.metric_date >= seven_days_ago
        ).group_by(
            SystemMetric.metric_date,
            SystemMetric.metric_type
        ).all()
        
        # Format breakdown data
        breakdown = {}
        for metric in metrics_breakdown:
            date_str = metric.metric_date.isoformat()
            if date_str not in breakdown:
                breakdown[date_str] = {}
            breakdown[date_str][metric.metric_type] = metric.total
        
        return jsonify({
            'daily_logins': daily_logins,
            'api_requests': api_requests,
            'db_queries': db_queries,
            'active_sessions': active_sessions,
            'breakdown': breakdown,
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

