"""
Middleware for tracking system metrics
"""
from flask import request, g
from datetime import datetime, timezone
from .models import SystemMetric
from .extensions import db

# Store response times for averaging
_response_times = []
_max_response_times = 100  # Keep last 100 response times

def track_request_metrics(app):
    """Add before/after request handlers to track metrics"""
    
    @app.before_request
    def before_request():
        """Track request start time"""
        g.request_start_time = datetime.now(timezone.utc)
    
    @app.after_request
    def after_request(response):
        """Track API requests and database queries"""
        try:
            # Track API requests (count all requests)
            if request.endpoint and not request.path.startswith('/static'):
                SystemMetric.increment_metric('api_requests')
            
            # Track response time
            if hasattr(g, 'request_start_time'):
                duration = (datetime.now(timezone.utc) - g.request_start_time).total_seconds() * 1000
                # Store average response time
                if duration > 0:
                    response.headers['X-Response-Time'] = f'{duration:.2f}ms'
                    
                    # Store for averaging (keep last 100)
                    global _response_times
                    _response_times.append(duration)
                    if len(_response_times) > _max_response_times:
                        _response_times.pop(0)
        
        except Exception as e:
            # Don't fail the request if metric tracking fails
            app.logger.error(f"Metric tracking error: {str(e)}")
        
        return response
    
    # Track database queries
    @app.before_request
    def track_db_queries():
        """Track database query count"""
        g.query_count = 0
    
    # Hook into SQLAlchemy to count queries
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Increment query counter"""
        if hasattr(g, 'query_count'):
            g.query_count += 1
    
    @app.after_request
    def track_db_metrics(response):
        """Save database query metrics"""
        try:
            if hasattr(g, 'query_count') and g.query_count > 0:
                # Track total queries (batch update to avoid too many DB writes)
                if g.query_count > 1:  # Ignore the metric increment itself
                    SystemMetric.increment_metric('db_queries', g.query_count - 1)
        except Exception as e:
            app.logger.error(f"DB metric tracking error: {str(e)}")
        
        return response

def get_average_response_time():
    """Get average response time from stored values"""
    global _response_times
    if not _response_times:
        return 0
    return round(sum(_response_times) / len(_response_times), 2)

