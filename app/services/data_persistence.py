import logging
from datetime import datetime, timezone
from functools import wraps
from flask import current_app
from app.extensions import db
from app.models import AuditLog
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DataPersistenceService:
    """Service to ensure all ERP data is automatically saved and persisted"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the data persistence service with Flask app"""
        self.app = app
        
        # Configure SQLite for better performance and reliability
        def configure_sqlite():
            if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
                try:
                    from sqlalchemy import text
                    with db.engine.connect() as conn:
                        # Enable WAL mode for better concurrency
                        conn.execute(text("PRAGMA journal_mode=WAL"))
                        # Enable foreign key constraints
                        conn.execute(text("PRAGMA foreign_keys=ON"))
                        # Set synchronous mode to NORMAL for better performance
                        conn.execute(text("PRAGMA synchronous=NORMAL"))
                        # Set cache size (negative value means KB)
                        conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB cache
                        # Set temp store to memory
                        conn.execute(text("PRAGMA temp_store=MEMORY"))
                        conn.commit()
                        logger.info("SQLite configured for optimal performance and reliability")
                except Exception as e:
                    logger.warning(f"Could not configure SQLite optimizations: {str(e)}")
        
        # Configure SQLite when app context is available
        try:
            with app.app_context():
                configure_sqlite()
        except Exception as e:
            logger.warning(f"Could not initialize SQLite configuration: {str(e)}")
        
        # Auto-commit after each request only if there are actual changes
        @app.after_request
        def auto_commit(response):
            try:
                # Only commit if there are actual pending changes
                if db.session.dirty or db.session.new or db.session.deleted:
                    # Check if response is successful (2xx status codes)
                    if 200 <= response.status_code < 300:
                        db.session.commit()
                        logger.debug("Auto-committed database changes")
                    else:
                        # Rollback on error responses
                        db.session.rollback()
                        logger.debug("Rolled back database changes due to error response")
            except Exception as e:
                logger.error(f"Error during auto-commit: {str(e)}")
                db.session.rollback()
            return response
        
        # Handle database errors gracefully
        @app.teardown_appcontext
        def handle_db_errors(error):
            if error:
                logger.error(f"Database error during request: {str(error)}")
                db.session.rollback()
            db.session.remove()
    
    def safe_save(self, obj, action='create', entity_name=None, user_id=None):
        """Safely save an object to the database with error handling and audit logging"""
        try:
            if action == 'create':
                db.session.add(obj)
            
            db.session.commit()
            
            # Log the action for audit trail
            self.log_data_action(action, entity_name or obj.__class__.__name__, 
                               getattr(obj, 'id', None), user_id)
            
            logger.info(f"Successfully {action}d {entity_name or obj.__class__.__name__} with ID: {getattr(obj, 'id', 'N/A')}")
            return True, "Data saved successfully"
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error saving {entity_name or obj.__class__.__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def safe_delete(self, obj, entity_name=None, user_id=None):
        """Safely delete an object from the database with error handling and audit logging"""
        try:
            entity_id = getattr(obj, 'id', None)
            entity_name = entity_name or obj.__class__.__name__
            
            db.session.delete(obj)
            db.session.commit()
            
            # Log the deletion for audit trail
            self.log_data_action('delete', entity_name, entity_id, user_id)
            
            logger.info(f"Successfully deleted {entity_name} with ID: {entity_id}")
            return True, "Data deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting {entity_name or obj.__class__.__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def log_data_action(self, action: str, entity: str, entity_id: Optional[int], user_id: Optional[int]):
        """Log data actions for audit trail"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                entity=entity.lower(),
                entity_id=entity_id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error logging audit action: {str(e)}")
            # Don't fail the main operation if audit logging fails
            db.session.rollback()
    
    def ensure_data_integrity(self):
        """Check and ensure database integrity"""
        try:
            if 'sqlite' in current_app.config.get('SQLALCHEMY_DATABASE_URI', ''):
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    # Check database integrity
                    result = conn.execute(text("PRAGMA integrity_check")).fetchone()
                    if result[0] != 'ok':
                        logger.error(f"Database integrity check failed: {result[0]}")
                        return False, f"Database integrity issue: {result[0]}"
                    
                    # Check foreign key constraints
                    result = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                    if result:
                        logger.error(f"Foreign key constraint violations found: {len(result)}")
                        return False, f"Foreign key violations found: {len(result)}"
                    
                    logger.info("Database integrity check passed")
                    return True, "Database integrity is good"
            
            return True, "Database integrity check completed"
            
        except Exception as e:
            error_msg = f"Error checking database integrity: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for monitoring"""
        try:
            stats = {}
            
            # Get table counts
            from app.models import (User, Sale, SaleLine, MenuItem, InventoryItem, 
                                  PurchaseOrder, Expense, DailyClosing, AuditLog)
            
            stats['table_counts'] = {
                'users': User.query.count(),
                'sales': Sale.query.count(),
                'sale_lines': SaleLine.query.count(),
                'menu_items': MenuItem.query.count(),
                'inventory_items': InventoryItem.query.count(),
                'purchase_orders': PurchaseOrder.query.count(),
                'expenses': Expense.query.count(),
                'daily_closings': DailyClosing.query.count(),
                'audit_logs': AuditLog.query.count()
            }
            
            # Get recent activity
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            recent_sales = Sale.query.filter(
                Sale.created_at >= today_start
            ).count()
            
            recent_audit_logs = AuditLog.query.filter(
                AuditLog.created_at >= today_start
            ).count()
            
            stats['daily_activity'] = {
                'sales_today': recent_sales,
                'audit_logs_today': recent_audit_logs
            }
            
            # Database file info
            if 'sqlite' in current_app.config.get('SQLALCHEMY_DATABASE_URI', ''):
                try:
                    from sqlalchemy import text
                    with db.engine.connect() as conn:
                        page_count = conn.execute(text("PRAGMA page_count")).fetchone()[0]
                        page_size = conn.execute(text("PRAGMA page_size")).fetchone()[0]
                        stats['database_info'] = {
                            'page_count': page_count,
                            'page_size': page_size,
                            'estimated_size_mb': round((page_count * page_size) / (1024 * 1024), 2)
                        }
                except Exception as e:
                    logger.warning(f"Could not get database file info: {str(e)}")
                    stats['database_info'] = {
                        'page_count': 0,
                        'page_size': 0,
                        'estimated_size_mb': 0
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {'error': str(e)}

def auto_save(entity_name=None):
    """Decorator to automatically save database changes with error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # Ensure changes are committed
                if db.session.dirty or db.session.new or db.session.deleted:
                    db.session.commit()
                    logger.debug(f"Auto-saved changes in {func.__name__}")
                
                return result
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error in {func.__name__}: {str(e)}")
                raise
        
        return wrapper
    return decorator

def transaction_safe(func):
    """Decorator to ensure database operations are transaction-safe"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            logger.error(f"Transaction failed in {func.__name__}: {str(e)}")
            raise
    
    return wrapper

# Global data persistence service instance
data_persistence = DataPersistenceService()
