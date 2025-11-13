"""
Multi-tenant service for TSG Cafe ERP
Handles tenant creation, management, and data isolation
"""
import os
import secrets
from datetime import datetime, timezone
from flask import current_app
from ..extensions import db
from ..models import Business, User, SystemSetting


class TenantService:
    """Service for managing multi-tenant operations"""
    
    @staticmethod
    def create_tenant(business_name, owner_email, owner_name=None, subscription_plan='free'):
        """
        Create a new tenant (business) with owner user
        
        Args:
            business_name (str): Name of the business
            owner_email (str): Email of the business owner
            owner_name (str): Full name of the owner (optional)
            subscription_plan (str): Subscription plan (free, basic, premium)
            
        Returns:
            dict: Created business and user information
        """
        try:
            # Check if business already exists
            existing_business = Business.query.filter_by(business_name=business_name).first()
            if existing_business:
                raise ValueError(f"Business '{business_name}' already exists")
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=owner_email).first()
            if existing_user:
                raise ValueError(f"Email '{owner_email}' already registered")
            
            # Create business
            business = Business(
                business_name=business_name,
                owner_email=owner_email,
                subscription_plan=subscription_plan,
                is_active=True
            )
            db.session.add(business)
            db.session.flush()  # Get business ID
            
            # Generate secure credentials
            username = TenantService._generate_username(business_name)
            temp_password = TenantService._generate_password()
            
            # Parse owner name
            if owner_name:
                name_parts = owner_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
            else:
                first_name = 'Business'
                last_name = 'Owner'
            
            # Create owner user
            owner_user = User(
                business_id=business.id,
                employee_id='OWNER001',
                username=username,
                email=owner_email,
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}".strip(),
                role='admin',
                is_owner=True,
                is_active=True,
                requires_password_change=True,  # Force password change on first login
                email_verified=False
            )
            owner_user.set_password(temp_password)
            owner_user.set_navigation_permissions([
                'dashboard', 'pos', 'menu', 'inventory', 
                'finance', 'reports', 'admin'
            ])
            
            db.session.add(owner_user)
            db.session.flush()
            
            # Update business owner_id
            business.owner_id = owner_user.id
            
            # Create default system settings for this tenant
            TenantService._create_default_settings(business.id)
            
            db.session.commit()
            
            return {
                'business': business.to_dict(),
                'owner': {
                    'id': owner_user.id,
                    'username': username,
                    'email': owner_email,
                    'temp_password': temp_password,
                    'full_name': owner_user.full_name
                },
                'message': 'Tenant created successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def _generate_username(business_name):
        """Generate unique username based on business name"""
        # Clean business name and create base username
        clean_name = ''.join(c for c in business_name if c.isalnum())[:8].upper()
        if not clean_name:
            clean_name = 'BIZ'
        
        # Add random suffix to ensure uniqueness
        suffix = secrets.randbelow(999) + 1
        username = f"{clean_name}{suffix:03d}"
        
        # Ensure uniqueness
        while User.query.filter_by(username=username).first():
            suffix = secrets.randbelow(999) + 1
            username = f"{clean_name}{suffix:03d}"
        
        return username
    
    @staticmethod
    def _generate_password():
        """Generate secure temporary password"""
        # Generate 12-character password with mixed case, numbers, and symbols
        import string
        chars = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(chars) for _ in range(12))
    
    @staticmethod
    def _create_default_settings(business_id):
        """Create default system settings for new tenant"""
        default_settings = [
            ('restaurant_name', 'My Restaurant'),
            ('currency', 'USD'),
            ('timezone', 'UTC'),
            ('date_format', 'DD/MM/YYYY'),
            ('time_format', '12'),
            ('tax_rate', '0.00'),
            ('service_charge', '0.00'),
            ('receipt_footer', 'Thank you for your business!'),
            ('max_users', '10'),
            ('backup_enabled', 'true'),
            ('backup_frequency', 'daily')
        ]
        
        for key, value in default_settings:
            setting = SystemSetting(
                business_id=business_id,
                key=key,
                value=value,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(setting)
    
    @staticmethod
    def get_tenant_info(business_id):
        """Get tenant information"""
        business = Business.query.get(business_id)
        if not business:
            return None
        
        return {
            'id': business.id,
            'name': business.business_name,
            'owner_email': business.owner_email,
            'subscription_plan': business.subscription_plan,
            'is_active': business.is_active,
            'created_at': business.created_at,
            'user_count': User.query.filter_by(business_id=business_id).count()
        }
    
    @staticmethod
    def deactivate_tenant(business_id, reason=None):
        """Deactivate a tenant"""
        business = Business.query.get(business_id)
        if business:
            business.is_active = False
            business.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def activate_tenant(business_id):
        """Activate a tenant"""
        business = Business.query.get(business_id)
        if business:
            business.is_active = True
            business.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False
