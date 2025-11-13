"""
System Administrator Dashboard Blueprint
Separate dashboard for system administrators
"""

from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user
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

bp = Blueprint('system_admin_dashboard', __name__, url_prefix='/system-admin')

def require_system_admin():
    """Decorator to ensure only system administrators can access"""
    if current_user.role != 'system_administrator':
        return redirect(url_for('dashboard.index'))
    return None

@bp.route('/')
@login_required
def index():
    """System Administrator Main Dashboard"""
    redirect_response = require_system_admin()
    if redirect_response:
        return redirect_response
    
    return render_template('system_admin/dashboard.html')

@bp.route('/api/stats')
@login_required
def system_stats():
    """Get system-wide statistics"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
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

@bp.route('/api/business-analytics')
@login_required
def business_analytics():
    """Get business analytics data"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get businesses with user counts and activity
        businesses_data = db.session.query(
            Business,
            func.count(User.id).label('user_count')
        ).outerjoin(User, Business.id == User.business_id)\
         .group_by(Business.id)\
         .order_by(Business.created_at.desc()).all()
        
        businesses_list = []
        for business, user_count in businesses_data:
            # Get recent activity for this business (if AuditLog has business_id)
            recent_activity = 0
            if AuditLog is not None:
                try:
                    if hasattr(AuditLog, 'business_id'):
                        recent_activity = AuditLog.query.filter(
                            AuditLog.business_id == business.id,
                            AuditLog.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
                        ).count()
                except:
                    recent_activity = 0
            
            businesses_list.append({
                'id': business.id,
                'name': business.business_name,
                'owner_email': business.owner_email,
                'subscription_plan': business.subscription_plan,
                'is_active': business.is_active,
                'created_at': business.created_at.isoformat(),
                'user_count': user_count,
                'recent_activity': recent_activity
            })
        
        return jsonify({
            'businesses': businesses_list,
            'total': len(businesses_list)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/system-health')
@login_required
def system_health():
    """Get system health metrics"""
    redirect_response = require_system_admin()
    if redirect_response:
        return jsonify({'error': 'Access denied'}), 403
    
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
