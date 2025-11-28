"""
System resource monitoring utilities using psutil
"""
import psutil
from datetime import datetime, timezone

class SystemMonitor:
    """Monitor system resources (CPU, Memory, Disk)"""
    
    _app_start_time = None
    
    @classmethod
    def initialize(cls):
        """Initialize system monitor with app start time"""
        if cls._app_start_time is None:
            cls._app_start_time = datetime.now(timezone.utc)
    
    @classmethod
    def get_cpu_usage(cls):
        """Get current CPU usage percentage"""
        try:
            # Get CPU usage over 0.1 second interval
            return round(psutil.cpu_percent(interval=0.1), 1)
        except Exception as e:
            print(f"Error getting CPU usage: {e}")
            return 0
    
    @classmethod
    def get_memory_usage(cls):
        """Get memory usage information"""
        try:
            memory = psutil.virtual_memory()
            return {
                'percent': round(memory.percent, 1),
                'used_gb': round(memory.used / (1024 ** 3), 2),
                'total_gb': round(memory.total / (1024 ** 3), 2),
                'available_gb': round(memory.available / (1024 ** 3), 2)
            }
        except Exception as e:
            print(f"Error getting memory usage: {e}")
            return {'percent': 0, 'used_gb': 0, 'total_gb': 0, 'available_gb': 0}
    
    @classmethod
    def get_disk_usage(cls, path='/'):
        """Get disk usage information"""
        try:
            disk = psutil.disk_usage(path)
            return {
                'percent': round(disk.percent, 1),
                'used_gb': round(disk.used / (1024 ** 3), 2),
                'total_gb': round(disk.total / (1024 ** 3), 2),
                'free_gb': round(disk.free / (1024 ** 3), 2)
            }
        except Exception as e:
            print(f"Error getting disk usage: {e}")
            return {'percent': 0, 'used_gb': 0, 'total_gb': 0, 'free_gb': 0}
    
    @classmethod
    def get_uptime(cls):
        """Get application uptime"""
        try:
            if cls._app_start_time is None:
                cls.initialize()
            
            uptime_delta = datetime.now(timezone.utc) - cls._app_start_time
            total_seconds = int(uptime_delta.total_seconds())
            
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            # Calculate uptime percentage (assuming 99.9% as target)
            # For a real implementation, you'd track downtime
            uptime_percent = 99.9
            
            return {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
                'total_seconds': total_seconds,
                'uptime_percent': uptime_percent,
                'uptime_string': f"{days}d {hours}h {minutes}m"
            }
        except Exception as e:
            print(f"Error getting uptime: {e}")
            return {
                'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0,
                'total_seconds': 0, 'uptime_percent': 0, 'uptime_string': '0d 0h 0m'
            }
    
    @classmethod
    def get_system_stats(cls):
        """Get all system statistics in one call"""
        return {
            'cpu': cls.get_cpu_usage(),
            'memory': cls.get_memory_usage(),
            'disk': cls.get_disk_usage(),
            'uptime': cls.get_uptime()
        }
    
    @classmethod
    def get_process_info(cls):
        """Get current process information"""
        try:
            process = psutil.Process()
            with process.oneshot():
                return {
                    'memory_mb': round(process.memory_info().rss / (1024 ** 2), 2),
                    'cpu_percent': round(process.cpu_percent(), 1),
                    'threads': process.num_threads(),
                    'connections': len(process.connections())
                }
        except Exception as e:
            print(f"Error getting process info: {e}")
            return {'memory_mb': 0, 'cpu_percent': 0, 'threads': 0, 'connections': 0}
