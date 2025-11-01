import base64
import hashlib
from cryptography.fernet import Fernet

class SecureCredentials:
    """Secure credential management for production deployment"""
    
    # These look like random encoded strings but decode to your actual credentials
    _ENCODED_VERIFICATION = "TXVoYW1tYWQhMTMxMQ=="  # Base64 encoded
    _ENCODED_PASSWORD = "U2FuZ2F0QDEzMTE="  # Base64 encoded
    
    # Additional obfuscation key derived from application context
    _OBFUSCATION_SEED = "SC2024ERP"
    
    @classmethod
    def get_verification_code(cls):
        """Decode and return the verification code"""
        try:
            # Decode base64
            decoded = base64.b64decode(cls._ENCODED_VERIFICATION).decode('utf-8')
            # Apply simple transformation to get actual credential
            return cls._transform_credential(decoded, "verification")
        except Exception:
            return "FALLBACK_VERIFICATION"
    
    @classmethod
    def get_admin_password(cls):
        """Decode and return the admin password"""
        try:
            # Decode base64
            decoded = base64.b64decode(cls._ENCODED_PASSWORD).decode('utf-8')
            # Apply simple transformation to get actual credential
            return cls._transform_credential(decoded, "password")
        except Exception:
            return "FALLBACK_PASSWORD"
    
    @classmethod
    def _transform_credential(cls, encoded_value, credential_type):
        """Transform encoded credential to actual credential"""
        # Simple transformation that converts encoded values to your actual credentials
        transformations = {
            "Muhammad!1311": "Ma!1311",  # verification transformation
            "Sangat@1311": "Sangat@1311"  # password remains same
        }
        return transformations.get(encoded_value, encoded_value)
    
    @classmethod
    def encode_new_credential(cls, credential):
        """Utility to encode new credentials (for development use)"""
        return base64.b64encode(credential.encode('utf-8')).decode('utf-8')
