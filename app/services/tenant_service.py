"""
Multi-tenant service for TSG Cafe ERP
Handles tenant creation, management, and data isolation
"""
import os
import secrets
import string
from datetime import datetime, timezone
from flask import current_app
from ..extensions import db
from ..models import Business, User, SystemSetting


class TenantService:
    """Service for managing multi-tenant operations"""
    
    @staticmethod
    def create_tenant(business_name, owner_email, owner_name=None, phone_number=None, password=None, subscription_plan='basic'):
        """
        Create a new tenant (business) with owner user
        
        Args:
            business_name (str): Name of the business
            owner_email (str): Email of the business owner
            owner_name (str): Full name of the owner (optional)
            phone_number (str): Phone number of the owner (optional)
            password (str): Password for the owner account (optional, generates temp password if not provided)
            subscription_plan (str): Subscription plan code from SubscriptionPlan table
            
        Returns:
            dict: Created business and user information
        """
        try:
            # Check if business name already exists (current or historical)
            from ..models import BusinessNameHistory
            existing_business = Business.query.filter_by(business_name=business_name).first()
            if existing_business:
                raise ValueError(f"Business name '{business_name}' is already registered")
            
            # Check if name was used before by any business
            historical_name = BusinessNameHistory.query.filter_by(business_name=business_name).first()
            if historical_name:
                raise ValueError(f"Business name '{business_name}' was previously used and cannot be reused")
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=owner_email).first()
            if existing_user:
                raise ValueError(f"Email '{owner_email}' already registered")
            
            # Get plan details from SubscriptionPlan table
            from ..models import SubscriptionPlan
            plan_config = SubscriptionPlan.query.filter_by(plan_code=subscription_plan, is_active=True).first()
            
            # Calculate trial end date if plan has trial
            trial_end_date = None
            subscription_status = 'active'
            if plan_config and plan_config.has_trial and plan_config.trial_days > 0:
                from datetime import timedelta
                trial_end_date = datetime.now(timezone.utc) + timedelta(days=plan_config.trial_days)
                subscription_status = 'trial'
            
            # Create business
            business = Business(
                business_name=business_name,
                owner_email=owner_email,
                subscription_plan=subscription_plan,
                subscription_status=subscription_status,
                trial_end_date=trial_end_date,
                is_active=True
            )
            db.session.add(business)
            db.session.flush()  # Get business ID
            
            # Generate and set business code based on business name
            business.business_code = TenantService._generate_business_code(business_name)
            
            # Record the initial business name in history
            from ..models import BusinessNameHistory
            name_history = BusinessNameHistory(
                business_id=business.id,
                business_name=business_name
            )
            db.session.add(name_history)
            
            # Generate secure credentials
            username = TenantService._generate_username(business_name)
            
            # Use provided password or generate temporary one
            if password:
                user_password = password
                requires_password_change = False
            else:
                user_password = TenantService._generate_password()
                requires_password_change = True
            
            # Parse owner name
            if owner_name:
                name_parts = owner_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
            else:
                first_name = 'Business'
                last_name = 'Owner'
            
            # Generate unique employee_id
            employee_id = TenantService._generate_employee_id(business.id)
            
            # Create owner user
            owner_user = User(
                business_id=business.id,
                employee_id=employee_id,
                username=username,
                email=owner_email,
                phone=phone_number,
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}".strip(),
                role='owner',  # Business owner role
                designation='CEO',  # Set designation as CEO
                department='Management',  # Set department as Management
                is_owner=True,
                is_active=True,
                requires_password_change=requires_password_change,
                email_verified=True  # Set to True since we verified with codes
            )
            owner_user.set_password(user_password)
            owner_user.set_navigation_permissions([
                'dashboard', 'pos', 'menu', 'inventory', 
                'finance', 'reports', 'admin'
            ])
            
            db.session.add(owner_user)
            db.session.flush()
            
            # Update business owner_id
            business.owner_id = owner_user.id
            
            # Create subscription for the business
            from .subscription_service import SubscriptionService
            subscription = SubscriptionService.create_subscription(
                business_id=business.id,
                plan=subscription_plan,
                subscription_months=1  # Default to 1 month
            )
            
            # Create default system settings for this tenant
            TenantService._create_default_settings(business.id, business_name)
            
            db.session.commit()
            
            return {
                'business': business.to_dict(),
                'owner': {
                    'id': owner_user.id,
                    'username': username,
                    'email': owner_email,
                    'phone': phone_number,
                    'temp_password': user_password if requires_password_change else None,
                    'full_name': owner_user.full_name
                },
                'subscription': subscription.to_dict(),
                'message': 'Tenant created successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def _generate_business_code(business_name):
        """Generate unique business code based on business name abbreviation + padded number"""
        import re
        
        # Extract letters only and convert to uppercase
        letters_only = re.sub(r'[^A-Za-z]', '', business_name).upper()
        
        if not letters_only:
            abbreviation = 'BIZ'
        else:
            # Create abbreviation from business name
            words = re.findall(r'[A-Z][a-z]*', business_name.title())
            
            if len(words) >= 2:
                # Use first letter of each word (e.g., "Art by Lishy" -> "ABL")
                abbreviation = ''.join(word[0] for word in words if word)
            elif len(letters_only) >= 3:
                # Use first 3-4 letters (e.g., "Restaurant" -> "REST")
                abbreviation = letters_only[:4]
            else:
                # Use all letters and pad if needed
                abbreviation = letters_only.ljust(3, 'X')
        
        # Limit abbreviation to 4 characters max
        abbreviation = abbreviation[:4]
        
        # Get total count of existing businesses + 1
        total_businesses = Business.query.count()
        business_number = total_businesses + 1
        
        # Generate code: ABBREVIATION + 3-digit padded number
        business_code = f"{abbreviation}{business_number:03d}"
        
        # Ensure uniqueness (in case of race conditions or deletions)
        while Business.query.filter_by(business_code=business_code).first():
            business_number += 1
            business_code = f"{abbreviation}{business_number:03d}"
        
        return business_code
    
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
    def _generate_employee_id(business_id):
        """Generate unique employee_id for the business"""
        # Start with OWNER001 and increment if needed
        base_id = "OWNER"
        counter = 1
        
        while True:
            employee_id = f"{base_id}{counter:03d}"
            # Check if this employee_id exists in any business (global uniqueness)
            existing = User.query.filter_by(employee_id=employee_id).first()
            if not existing:
                return employee_id
            counter += 1
            
            # Safety check to prevent infinite loop
            if counter > 999:
                # Use business_id as suffix for uniqueness
                return f"OWNER{business_id:03d}"
    
    @staticmethod
    def _generate_password():
        """Generate secure temporary password"""
        # Generate 12-character password with mixed case, numbers, and symbols
        chars = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(chars) for _ in range(12))
    
    @staticmethod
    @staticmethod
    def _create_default_settings(business_id, business_name):
        """Create default system settings for new tenant"""
        default_settings = [
            ('restaurant_name', business_name),
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
            # Check if setting already exists for this business
            existing = SystemSetting.query.filter_by(
                business_id=business_id,
                key=key
            ).first()
            
            if not existing:
                setting = SystemSetting(
                    business_id=business_id,
                    key=key,
                    value=value
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
