"""
System Administrator Permissions and Rights
Complete list of all system administrator privileges separated from business module
"""

# System Administrator Rights and Permissions
SYSTEM_ADMIN_RIGHTS = {
    # User Management Rights
    'user_management': {
        'view_all_users': 'Can view users from all businesses (not just own business)',
        'create_system_admin': 'Can create other system administrator accounts',
        'edit_system_admin': 'Can edit other system administrator accounts',
        'delete_any_user': 'Can delete any user account (including protected users)',
        'view_system_admin': 'Can view system administrator accounts',
        'assign_system_admin_role': 'Can assign system administrator role to users',
        'edit_protected_users': 'Can edit protected user accounts',
        'change_protected_passwords': 'Can change passwords for protected users',
        'manage_user_permissions': 'Can manage navigation permissions for all users',
        'access_user_management_panel': 'Can access the user management interface'
    },
    
    # Business Management Rights  
    'business_management': {
        'view_all_businesses': 'Can view all registered businesses in the system',
        'access_business_analytics': 'Can view business analytics and statistics',
        'toggle_business_status': 'Can activate/deactivate business accounts',
        'view_business_users': 'Can view users belonging to any business',
        'access_multi_tenant_data': 'Can access data from all businesses',
        'manage_subscription_plans': 'Can view and manage subscription plans',
        'view_business_registration_data': 'Can view business registration information'
    },
    
    # System Management Rights
    'system_management': {
        'view_system_statistics': 'Can view system-wide statistics and metrics',
        'access_system_dashboard': 'Can access system administrator dashboard',
        'view_system_health': 'Can monitor system health and performance',
        'access_system_logs': 'Can view system logs and audit trails',
        'manage_global_settings': 'Can manage global system settings',
        'view_system_analytics': 'Can view system growth trends and analytics',
        'monitor_system_activity': 'Can monitor system-wide activity',
        'access_system_monitoring': 'Can access system monitoring tools'
    },
    
    # Data Management Rights
    'data_management': {
        'view_all_sales_data': 'Can view sales data from all businesses',
        'view_all_inventory_data': 'Can view inventory data from all businesses', 
        'view_all_financial_data': 'Can view financial data from all businesses',
        'access_cross_business_reports': 'Can generate reports across all businesses',
        'view_all_audit_logs': 'Can view audit logs from all businesses',
        'manage_data_integrity': 'Can manage referential integrity across businesses'
    },
    
    # Administrative Rights
    'administrative': {
        'password_reset_management': 'Can manage password reset requests for all users',
        'account_deletion_management': 'Can manage account deletion requests',
        'backup_management': 'Can create, restore, and manage system backups',
        'system_maintenance': 'Can perform system maintenance tasks',
        'tenant_management': 'Can manage tenant registrations and configurations',
        'security_management': 'Can manage system security settings',
        'audit_trail_management': 'Can manage and review audit trails'
    },
    
    # Special Privileges
    'special_privileges': {
        'bypass_business_context': 'Can bypass business context filtering',
        'cross_tenant_access': 'Can access data across different tenants',
        'system_level_operations': 'Can perform system-level operations',
        'emergency_access': 'Can access system in emergency situations',
        'super_user_privileges': 'Has super user privileges for system management'
    }
}

# Navigation permissions for system administrators
SYSTEM_ADMIN_NAVIGATION = [
    'system_dashboard',
    'user_management', 
    'business_management',
    'system_analytics',
    'system_monitoring',
    'system_settings',
    'backup_management',
    'audit_logs'
]

# Default role permissions (for reference)
DEFAULT_ROLE_PERMISSIONS = {
    'system_administrator': ['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'],
    'admin': ['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'],
    'manager': ['dashboard', 'pos', 'menu', 'inventory', 'reports'],
    'cashier': ['dashboard', 'pos'],
    'inventory': ['dashboard', 'inventory', 'menu'],
    'finance': ['dashboard', 'finance', 'reports'],
    'employee': ['dashboard']
}

def get_system_admin_rights():
    """Get all system administrator rights"""
    return SYSTEM_ADMIN_RIGHTS

def has_system_admin_right(right_category, right_name):
    """Check if a specific system admin right exists"""
    return (right_category in SYSTEM_ADMIN_RIGHTS and 
            right_name in SYSTEM_ADMIN_RIGHTS[right_category])

def get_all_system_admin_rights_list():
    """Get a flat list of all system admin rights"""
    all_rights = []
    for category, rights in SYSTEM_ADMIN_RIGHTS.items():
        for right_name, description in rights.items():
            all_rights.append({
                'category': category,
                'right': right_name,
                'description': description
            })
    return all_rights
