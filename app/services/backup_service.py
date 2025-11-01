import os
import shutil
import json
import zipfile
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple

# Conditional import for sqlite3 (only needed for SQLite databases)
try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

logger = logging.getLogger(__name__)

class BackupService:
    """Service for handling local database backups and data persistence"""
    
    def __init__(self, app=None):
        self.app = app
        self.backup_dir = None
        self.db_path = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the backup service with Flask app"""
        self.app = app
        
        # Get database path from config
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///erp.db')
        if db_uri.startswith('sqlite:///'):
            self.db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(self.db_path):
                self.db_path = os.path.join(app.instance_path, self.db_path)
        
        # Set backup directory
        self.backup_dir = os.path.join(app.instance_path, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Ensure instance directory exists
        os.makedirs(app.instance_path, exist_ok=True)
    
    def get_database_size(self) -> int:
        """Get the size of the database file in bytes"""
        try:
            if self.db_path and os.path.exists(self.db_path):
                return os.path.getsize(self.db_path)
            return 0
        except Exception as e:
            logger.error(f"Error getting database size: {str(e)}")
            return 0
    
    def get_backup_info(self) -> Dict:
        """Get comprehensive backup information"""
        try:
            backup_files = []
            total_backup_size = 0
            
            if os.path.exists(self.backup_dir):
                for filename in os.listdir(self.backup_dir):
                    if filename.endswith('.zip'):
                        filepath = os.path.join(self.backup_dir, filename)
                        if os.path.isfile(filepath):
                            size = os.path.getsize(filepath)
                            total_backup_size += size
                            backup_files.append({
                                'filename': filename,
                                'size': size,
                                'size_mb': round(size / (1024 * 1024), 2),
                                'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                            })
            
            # Sort by creation time (newest first)
            backup_files.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Get database size
            db_size = 0
            if os.path.exists(self.db_path):
                db_size = os.path.getsize(self.db_path)
            
            return {
                'database_size': db_size,
                'database_size_mb': round(db_size / (1024 * 1024), 2),
                'backup_count': len(backup_files),
                'total_backup_size': total_backup_size,
                'total_backup_size_mb': round(total_backup_size / (1024 * 1024), 2),
                'backup_files': backup_files
            }
            
        except Exception as e:
            logger.error(f"Error getting backup info: {str(e)}")
            return {
                'error': str(e),
                'database_size': 0,
                'database_size_mb': 0,
                'backup_count': 0,
                'total_backup_size': 0,
                'total_backup_size_mb': 0,
                'backup_files': []
            }
    
    def list_backups(self) -> List[Dict]:
        """Get list of available backup files"""
        backup_info = self.get_backup_info()
        return backup_info.get('backup_files', [])
    
    def create_backup(self, backup_name: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """Create a backup of the database and return success status, message, and backup info"""
        try:
            if not self.db_path or not os.path.exists(self.db_path):
                return False, "Database file not found", {}
            
            # Generate backup filename if not provided
            if not backup_name:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_name = f"erp_backup_{timestamp}.zip"
            elif not backup_name.endswith('.zip'):
                backup_name += '.zip'
            
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Create backup zip file
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database file
                zipf.write(self.db_path, 'erp.db')
                
                # Add metadata
                metadata = {
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'database_size': self.get_database_size(),
                    'app_version': '1.0.0',  # You can get this from your app config
                    'backup_type': 'full'
                }
                zipf.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
                
                # Add any additional files (logs, uploads, etc.)
                self._add_additional_files_to_backup(zipf)
            
            backup_size = os.path.getsize(backup_path)
            
            logger.info(f"Backup created successfully: {backup_name}")
            
            return True, f"Backup created successfully: {backup_name}", {
                'filename': backup_name,
                'size': backup_size,
                'size_mb': round(backup_size / (1024 * 1024), 2),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error creating backup: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}
    
    def _add_additional_files_to_backup(self, zipf: zipfile.ZipFile):
        """Add additional files to backup (logs, uploads, etc.)"""
        try:
            # Add log files if they exist
            log_dir = os.path.join(os.path.dirname(self.app.instance_path), 'logs')
            if os.path.exists(log_dir):
                for log_file in os.listdir(log_dir):
                    if log_file.endswith('.log'):
                        log_path = os.path.join(log_dir, log_file)
                        zipf.write(log_path, f'logs/{log_file}')
            
            # Add uploaded files if they exist
            uploads_dir = os.path.join(self.app.root_path, 'static', 'uploads')
            if os.path.exists(uploads_dir):
                for root, dirs, files in os.walk(uploads_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, self.app.root_path)
                        zipf.write(file_path, arc_path)
                        
        except Exception as e:
            logger.warning(f"Error adding additional files to backup: {str(e)}")
    
    def restore_backup(self, backup_filename: str) -> Tuple[bool, str]:
        """Restore database from backup file"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return False, "Backup file not found"
            
            # Create a backup of current database before restoring
            current_backup_name = f"pre_restore_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
            success, msg, _ = self.create_backup(current_backup_name)
            if not success:
                logger.warning(f"Could not create pre-restore backup: {msg}")
            
            # Extract and restore from backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Check if backup contains database
                if 'erp.db' not in zipf.namelist():
                    return False, "Invalid backup file: database not found"
                
                # Extract database to temporary location first
                temp_db_path = self.db_path + '.temp'
                with zipf.open('erp.db') as source, open(temp_db_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                
                # Validate the extracted database
                if not self._validate_database(temp_db_path):
                    os.remove(temp_db_path)
                    return False, "Invalid database in backup file"
                
                # Replace current database
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
                os.rename(temp_db_path, self.db_path)
                
                # Restore additional files
                self._restore_additional_files(zipf)
            
            logger.info(f"Database restored successfully from: {backup_filename}")
            return True, f"Database restored successfully from: {backup_filename}"
            
        except Exception as e:
            error_msg = f"Error restoring backup: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _validate_database(self, db_path: str) -> bool:
        """Validate that the database file is valid SQLite database"""
        if not SQLITE_AVAILABLE:
            logger.warning("SQLite not available, skipping database validation")
            return True  # Assume valid if we can't validate
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Try to execute a simple query
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            conn.close()
            
            # Check if essential tables exist
            table_names = [table[0] for table in tables]
            essential_tables = ['users', 'sales', 'menu_items', 'system_settings']
            
            return any(table in table_names for table in essential_tables)
            
        except Exception as e:
            logger.error(f"Database validation failed: {str(e)}")
            return False
    
    def _restore_additional_files(self, zipf: zipfile.ZipFile):
        """Restore additional files from backup"""
        try:
            # Restore uploaded files
            for file_info in zipf.filelist:
                if file_info.filename.startswith('static/uploads/'):
                    target_path = os.path.join(self.app.root_path, file_info.filename)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    with zipf.open(file_info) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                        
        except Exception as e:
            logger.warning(f"Error restoring additional files: {str(e)}")
    
    def delete_backup(self, backup_filename: str) -> Tuple[bool, str]:
        """Delete a backup file"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return False, "Backup file not found"
            
            os.remove(backup_path)
            logger.info(f"Backup deleted: {backup_filename}")
            return True, f"Backup deleted successfully: {backup_filename}"
            
        except Exception as e:
            error_msg = f"Error deleting backup: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def cleanup_old_backups(self, keep_count: int = 10) -> Tuple[bool, str, int]:
        """Clean up old backup files, keeping only the specified number of recent backups"""
        try:
            if not os.path.exists(self.backup_dir):
                return True, "No backups to clean up", 0
            
            # Get all backup files with their modification times
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.endswith('.zip'):
                    backup_path = os.path.join(self.backup_dir, file)
                    mtime = os.path.getmtime(backup_path)
                    backups.append((file, mtime, backup_path))
            
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Delete old backups
            deleted_count = 0
            for i, (filename, mtime, path) in enumerate(backups):
                if i >= keep_count:  # Keep only the specified number of recent backups
                    try:
                        os.remove(path)
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {filename}")
                    except Exception as e:
                        logger.error(f"Error deleting old backup {filename}: {str(e)}")
            
            return True, f"Cleaned up {deleted_count} old backups", deleted_count
            
        except Exception as e:
            error_msg = f"Error during backup cleanup: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, 0
    
    def auto_backup(self) -> Tuple[bool, str]:
        """Perform automatic backup based on system settings"""
        try:
            from app.models import SystemSetting
            
            # Check if auto backup is enabled
            backup_frequency = SystemSetting.get_setting('backup_frequency', 'daily')
            
            if backup_frequency == 'disabled':
                return True, "Auto backup is disabled"
            
            # Check if backup is needed based on frequency
            last_backup_time = SystemSetting.get_setting('last_auto_backup_time')
            
            if last_backup_time:
                last_backup = datetime.fromisoformat(last_backup_time)
                now = datetime.now(timezone.utc)
                
                if backup_frequency == 'daily' and (now - last_backup).days < 1:
                    return True, "Daily backup already completed"
                elif backup_frequency == 'weekly' and (now - last_backup).days < 7:
                    return True, "Weekly backup already completed"
                elif backup_frequency == 'monthly' and (now - last_backup).days < 30:
                    return True, "Monthly backup already completed"
            
            # Create auto backup
            backup_name = f"auto_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
            success, message, backup_info = self.create_backup(backup_name)
            
            if success:
                # Update last backup time
                SystemSetting.set_setting('last_auto_backup_time', datetime.now(timezone.utc).isoformat())
                
                # Clean up old backups (keep last 20 auto backups)
                self.cleanup_old_backups(20)
                
                return True, f"Auto backup completed: {backup_name}"
            else:
                return False, f"Auto backup failed: {message}"
                
        except Exception as e:
            error_msg = f"Error during auto backup: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# Global backup service instance
backup_service = BackupService()
