"""
Enhanced Security Utilities for TSG ERP System
Provides additional security features for system administrator accounts
"""
import hashlib
import hmac
import secrets
import string
from datetime import datetime, timezone, timedelta
from flask import request, current_app
from flask_login import current_user
import logging

class SecurityManager:
    """Enhanced security manager for system administrator operations"""
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate a cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_verification_code(length=6):
        """Generate a numeric verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def hash_sensitive_data(data, salt=None):
        """Hash sensitive data with salt"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # Use PBKDF2 for key derivation
        from werkzeug.security import generate_password_hash
        return generate_password_hash(data + salt.hex())
    
    @staticmethod
    def verify_password_strength(password):
        """Verify password meets security requirements"""
        requirements = {
            'length': len(password) >= 8,
            'uppercase': any(c.isupper() for c in password),
            'lowercase': any(c.islower() for c in password),
            'digit': any(c.isdigit() for c in password),
            'special': any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        }
        
        score = sum(requirements.values())
        strength = 'weak' if score < 3 else 'medium' if score < 5 else 'strong'
        
        return {
            'score': score,
            'strength': strength,
            'requirements': requirements,
            'is_valid': score >= 4  # Require at least 4 out of 5 criteria
        }
    
    @staticmethod
    def log_security_event(event_type, details=None, user=None):
        """Log security-related events"""
        if user is None and current_user.is_authenticated:
            user = current_user
        
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'user_id': user.id if user else None,
            'username': user.username if user else 'anonymous',
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'details': details or {}
        }
        
        # Log to application logger
        logging.warning(f"SECURITY EVENT: {event_type} - User: {log_entry['username']} - IP: {log_entry['ip_address']}")
        
        return log_entry
    
    @staticmethod
    def check_suspicious_activity(user):
        """Check for suspicious activity patterns"""
        suspicious_indicators = []
        
        # Check failed login attempts
        if user.failed_login_attempts >= 3:
            suspicious_indicators.append('multiple_failed_logins')
        
        # Check if account was recently unlocked
        if user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc) - timedelta(hours=1):
            suspicious_indicators.append('recent_account_unlock')
        
        # Check login time patterns (if implemented)
        current_hour = datetime.now(timezone.utc).hour
        if current_hour < 6 or current_hour > 22:  # Outside normal business hours
            suspicious_indicators.append('unusual_login_time')
        
        return suspicious_indicators
    
    @staticmethod
    def generate_session_token():
        """Generate a secure session token"""
        return secrets.token_urlsafe(64)
    
    @staticmethod
    def validate_ip_whitelist(ip_address, whitelist=None):
        """Validate IP address against whitelist (if configured)"""
        if not whitelist:
            return True  # No whitelist configured, allow all
        
        # Simple IP validation - can be enhanced with CIDR support
        return ip_address in whitelist
    
    @staticmethod
    def encrypt_sensitive_field(data, key=None):
        """Encrypt sensitive field data"""
        if key is None:
            key = current_app.config.get('SECRET_KEY', 'default-key')
        
        # Simple encryption using Fernet (requires cryptography package)
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Generate key from secret
            key_bytes = hashlib.sha256(key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            fernet = Fernet(fernet_key)
            
            return fernet.encrypt(data.encode()).decode()
        except ImportError:
            # Fallback to base64 encoding if cryptography not available
            import base64
            return base64.b64encode(data.encode()).decode()
    
    @staticmethod
    def decrypt_sensitive_field(encrypted_data, key=None):
        """Decrypt sensitive field data"""
        if key is None:
            key = current_app.config.get('SECRET_KEY', 'default-key')
        
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Generate key from secret
            key_bytes = hashlib.sha256(key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            fernet = Fernet(fernet_key)
            
            return fernet.decrypt(encrypted_data.encode()).decode()
        except ImportError:
            # Fallback to base64 decoding
            import base64
            return base64.b64decode(encrypted_data.encode()).decode()

class SystemAdminSecurity:
    """Specialized security features for system administrator accounts"""
    
    @staticmethod
    def require_verification_code(user):
        """Generate and require verification code for sensitive operations"""
        if not user.is_system_administrator():
            return False
        
        verification_code = user.generate_verification_code()
        
        # In a real implementation, send this via SMS/Email
        SecurityManager.log_security_event(
            'verification_code_generated',
            {'code_length': len(verification_code)},
            user
        )
        
        return verification_code
    
    @staticmethod
    def validate_system_admin_session(user):
        """Validate system admin session security"""
        if not user.is_system_administrator():
            return False
        
        # Check for suspicious activity
        suspicious_indicators = SecurityManager.check_suspicious_activity(user)
        
        if suspicious_indicators:
            SecurityManager.log_security_event(
                'suspicious_activity_detected',
                {'indicators': suspicious_indicators},
                user
            )
            return False
        
        return True
    
    @staticmethod
    def enforce_session_timeout(user, timeout_minutes=60):
        """Enforce session timeout for system administrators"""
        if not user.is_system_administrator():
            return True
        
        if user.last_login:
            session_duration = datetime.now(timezone.utc) - user.last_login
            if session_duration > timedelta(minutes=timeout_minutes):
                SecurityManager.log_security_event(
                    'session_timeout_enforced',
                    {'duration_minutes': session_duration.total_seconds() / 60},
                    user
                )
                return False
        
        return True

# Security event types
SECURITY_EVENTS = {
    'LOGIN_SUCCESS': 'login_success',
    'LOGIN_FAILURE': 'login_failure',
    'ACCOUNT_LOCKED': 'account_locked',
    'PASSWORD_CHANGED': 'password_changed',
    'PRIVILEGE_ESCALATION': 'privilege_escalation',
    'SUSPICIOUS_ACTIVITY': 'suspicious_activity_detected',
    'VERIFICATION_CODE_GENERATED': 'verification_code_generated',
    'SESSION_TIMEOUT': 'session_timeout_enforced',
    'UNAUTHORIZED_ACCESS_ATTEMPT': 'unauthorized_access_attempt'
}
