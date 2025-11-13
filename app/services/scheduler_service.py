import threading
import time
import logging
from datetime import datetime, timezone, timedelta
# Lazy imports to avoid circular dependencies
# from app.services.backup_service import backup_service
# from app.models import SystemSetting

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for handling scheduled tasks like automatic backups"""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler_thread = None
        self.running = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the scheduler service with Flask app"""
        self.app = app
        
        # Only start scheduler in development mode or when explicitly enabled
        import os
        flask_env = os.environ.get('FLASK_ENV', 'production')
        enable_scheduler = os.environ.get('ENABLE_SCHEDULER', 'false').lower() == 'true'
        
        # Disable scheduler in production by default to avoid threading issues
        if flask_env == 'development' or enable_scheduler:
            if not self.running and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
                def start_scheduler():
                    self.start()
                
                # Use a timer to start scheduler after app initialization
                import threading
                timer = threading.Timer(2.0, start_scheduler)
                timer.daemon = True
                timer.start()
        else:
            logger.info("Scheduler service disabled in production environment")
    
    def start(self):
        """Start the scheduler thread"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Scheduler service started")
    
    def stop(self):
        """Stop the scheduler thread"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Scheduler service stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                with self.app.app_context():
                    # Check for automatic backup
                    self._check_auto_backup()
                    
                    # Check database integrity (daily)
                    self._check_database_integrity()
                
                # Sleep for 1 hour before next check
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in scheduler: {str(e)}")
                time.sleep(300)  # Sleep 5 minutes on error
    
    def _check_auto_backup(self):
        """Check if automatic backup is needed"""
        try:
            # Lazy import to avoid circular dependencies
            from app.models import SystemSetting
            from app.services.backup_service import backup_service
            
            backup_frequency = SystemSetting.get_setting('backup_frequency', 'daily')
            
            if backup_frequency == 'disabled':
                return
            
            last_backup_time = SystemSetting.get_setting('last_auto_backup_time')
            now = datetime.now(timezone.utc)
            
            should_backup = False
            
            if not last_backup_time:
                should_backup = True
            else:
                last_backup = datetime.fromisoformat(last_backup_time)
                # Ensure both datetimes are timezone-aware for comparison
                if last_backup.tzinfo is None:
                    last_backup = last_backup.replace(tzinfo=timezone.utc)
                
                if backup_frequency == 'daily' and (now - last_backup).days >= 1:
                    should_backup = True
                elif backup_frequency == 'weekly' and (now - last_backup).days >= 7:
                    should_backup = True
                elif backup_frequency == 'monthly' and (now - last_backup).days >= 30:
                    should_backup = True
            
            if should_backup:
                success, message = backup_service.auto_backup()
                if success:
                    logger.info(f"Automatic backup completed: {message}")
                else:
                    logger.error(f"Automatic backup failed: {message}")
                    
        except Exception as e:
            logger.error(f"Error checking auto backup: {str(e)}")
    
    def _check_database_integrity(self):
        """Check database integrity daily"""
        try:
            # Lazy import to avoid circular dependencies
            from app.models import SystemSetting
            
            last_integrity_check = SystemSetting.get_setting('last_integrity_check')
            now = datetime.now(timezone.utc)
            
            should_check = False
            
            if not last_integrity_check:
                should_check = True
            else:
                last_check = datetime.fromisoformat(last_integrity_check)
                # Ensure both datetimes are timezone-aware for comparison
                if last_check.tzinfo is None:
                    last_check = last_check.replace(tzinfo=timezone.utc)
                if (now - last_check).days >= 1:
                    should_check = True
            
            if should_check:
                from app.services.data_persistence import data_persistence
                success, message = data_persistence.ensure_data_integrity()
                
                if success:
                    logger.info(f"Database integrity check passed: {message}")
                else:
                    logger.error(f"Database integrity check failed: {message}")
                
                # Update last check time
                SystemSetting.set_setting('last_integrity_check', now.isoformat())
                
        except Exception as e:
            logger.error(f"Error checking database integrity: {str(e)}")

# Global scheduler service instance
scheduler_service = SchedulerService()
