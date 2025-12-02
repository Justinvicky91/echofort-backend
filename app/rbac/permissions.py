"""
Role-Based Access Control (RBAC) Permissions Matrix
Block 24 - Part A

Defines which roles can access which areas of the Super Admin panel.
"""

from enum import Enum
from typing import Dict, List, Set

class Role(str, Enum):
    """Available roles in the system"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    EMPLOYEE_SUPPORT = "employee_support"
    EMPLOYEE_MARKETING = "employee_marketing"
    EMPLOYEE_LEGAL = "employee_legal"
    EMPLOYEE_ENGINEERING = "employee_engineering"
    USER_PERSONAL = "user_personal"
    USER_FAMILY_OWNER = "user_family_owner"
    USER_FAMILY_MEMBER = "user_family_member"


class Permission(str, Enum):
    """Available permissions/areas in the system"""
    # Command Center & Overview
    COMMAND_CENTER = "command_center"
    APPROVAL_CENTER = "approval_center"
    TEAM_MATRIX = "team_matrix"
    
    # Customer & User Management
    CUSTOMER_HUB = "customer_hub"
    
    # Financial
    FINANCIAL_CENTER = "financial_center"
    
    # Features & Configuration
    FEATURES_USAGE = "features_usage"
    SYSTEM_CONFIG = "system_config"
    
    # Infrastructure & Technical
    INFRASTRUCTURE = "infrastructure"
    PAYMENT_CORE = "payment_core"
    
    # Security & Vault
    SECURE_VAULT = "secure_vault"
    VIP_ACCESS = "vip_access"
    
    # Threat Intelligence
    THREAT_INTEL = "threat_intel"
    
    # AI Systems
    ECHOFORT_AI = "echofort_ai"
    AI_LEARNING_CENTER = "ai_learning_center"
    AI_PENDING_ACTIONS = "ai_pending_actions"
    
    # Analytics & Data
    DEEP_ANALYTICS = "deep_analytics"
    DATA_CORE = "data_core"
    
    # Support & Communication
    WHATSAPP_SUPPORT = "whatsapp_support"
    RECOVERY_CODES = "recovery_codes"


# Permissions Matrix: Role -> Set of Permissions
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: {
        # Super Admin has access to EVERYTHING
        Permission.COMMAND_CENTER,
        Permission.APPROVAL_CENTER,
        Permission.TEAM_MATRIX,
        Permission.CUSTOMER_HUB,
        Permission.FINANCIAL_CENTER,
        Permission.FEATURES_USAGE,
        Permission.SYSTEM_CONFIG,
        Permission.INFRASTRUCTURE,
        Permission.PAYMENT_CORE,
        Permission.SECURE_VAULT,
        Permission.VIP_ACCESS,
        Permission.THREAT_INTEL,
        Permission.ECHOFORT_AI,
        Permission.AI_LEARNING_CENTER,
        Permission.AI_PENDING_ACTIONS,
        Permission.DEEP_ANALYTICS,
        Permission.DATA_CORE,
        Permission.WHATSAPP_SUPPORT,
        Permission.RECOVERY_CODES,
    },
    
    Role.ADMIN: {
        # Admin has broad access but NOT to Vault, System Config, or low-level infra
        Permission.COMMAND_CENTER,
        Permission.APPROVAL_CENTER,
        Permission.TEAM_MATRIX,
        Permission.CUSTOMER_HUB,
        Permission.FINANCIAL_CENTER,
        Permission.FEATURES_USAGE,
        Permission.THREAT_INTEL,
        Permission.ECHOFORT_AI,
        Permission.DEEP_ANALYTICS,
        Permission.DATA_CORE,
        Permission.WHATSAPP_SUPPORT,
        # NO: SECURE_VAULT, SYSTEM_CONFIG, INFRASTRUCTURE, PAYMENT_CORE, VIP_ACCESS, AI_LEARNING_CENTER, AI_PENDING_ACTIONS, RECOVERY_CODES
    },
    
    Role.EMPLOYEE_SUPPORT: {
        # Support team: Customer Hub, Support tickets, limited read-only access
        Permission.CUSTOMER_HUB,
        Permission.WHATSAPP_SUPPORT,
        Permission.THREAT_INTEL,  # Read-only for context
        # NO: Financial, Vault, Config, Infrastructure
    },
    
    Role.EMPLOYEE_MARKETING: {
        # Marketing team: Metrics, conversions, plan stats
        Permission.DEEP_ANALYTICS,
        Permission.FEATURES_USAGE,
        Permission.CUSTOMER_HUB,  # For user stats
        # NO: Evidence, Vault, Config, Infrastructure, Financial details
    },
    
    Role.EMPLOYEE_LEGAL: {
        # Legal team: Investigation cases, Evidence metadata, complaint drafts
        Permission.THREAT_INTEL,
        Permission.SECURE_VAULT,  # Metadata only, not raw secrets
        Permission.CUSTOMER_HUB,  # For case context
        # NO: System Config, Infrastructure, Financial, AI tools
    },
    
    Role.EMPLOYEE_ENGINEERING: {
        # Engineering team: Logs, errors, AI Pending Actions, System Config
        Permission.SYSTEM_CONFIG,
        Permission.INFRASTRUCTURE,
        Permission.AI_PENDING_ACTIONS,
        Permission.DATA_CORE,
        Permission.ECHOFORT_AI,
        # NO: Vault, Financial, Customer personal data
    },
    
    # End-user roles have NO access to Super Admin panel
    Role.USER_PERSONAL: set(),
    Role.USER_FAMILY_OWNER: set(),
    Role.USER_FAMILY_MEMBER: set(),
}


# Reverse mapping: Permission -> Set of Roles that can access it
PERMISSION_ROLES: Dict[Permission, Set[Role]] = {}
for role, permissions in ROLE_PERMISSIONS.items():
    for permission in permissions:
        if permission not in PERMISSION_ROLES:
            PERMISSION_ROLES[permission] = set()
        PERMISSION_ROLES[permission].add(role)


def has_permission(role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.
    
    Args:
        role: Role string (e.g., "super_admin", "admin")
        permission: Permission string (e.g., "command_center", "secure_vault")
    
    Returns:
        True if role has permission, False otherwise
    """
    try:
        role_enum = Role(role)
        permission_enum = Permission(permission)
        return permission_enum in ROLE_PERMISSIONS.get(role_enum, set())
    except (ValueError, KeyError):
        return False


def get_permissions(role: str) -> List[str]:
    """
    Get all permissions for a role.
    
    Args:
        role: Role string (e.g., "super_admin", "admin")
    
    Returns:
        List of permission strings
    """
    try:
        role_enum = Role(role)
        return [p.value for p in ROLE_PERMISSIONS.get(role_enum, set())]
    except (ValueError, KeyError):
        return []


def get_roles_for_permission(permission: str) -> List[str]:
    """
    Get all roles that have a specific permission.
    
    Args:
        permission: Permission string (e.g., "command_center")
    
    Returns:
        List of role strings
    """
    try:
        permission_enum = Permission(permission)
        return [r.value for r in PERMISSION_ROLES.get(permission_enum, set())]
    except (ValueError, KeyError):
        return []


def is_admin_role(role: str) -> bool:
    """
    Check if a role is an admin/employee role (has access to Super Admin panel).
    
    Args:
        role: Role string
    
    Returns:
        True if role is admin/employee, False if end-user role
    """
    try:
        role_enum = Role(role)
        return role_enum not in {
            Role.USER_PERSONAL,
            Role.USER_FAMILY_OWNER,
            Role.USER_FAMILY_MEMBER,
        }
    except (ValueError, KeyError):
        return False


# Sidebar menu items and their required permissions
SIDEBAR_ITEMS = {
    "Command Center": Permission.COMMAND_CENTER,
    "Approval Center": Permission.APPROVAL_CENTER,
    "Team Matrix": Permission.TEAM_MATRIX,
    "Customer Hub": Permission.CUSTOMER_HUB,
    "Financial Center": Permission.FINANCIAL_CENTER,
    "Features & Usage": Permission.FEATURES_USAGE,
    "Infrastructure": Permission.INFRASTRUCTURE,
    "Payment Core": Permission.PAYMENT_CORE,
    "VIP Access": Permission.VIP_ACCESS,
    "Secure Vault": Permission.SECURE_VAULT,
    "Threat Intel": Permission.THREAT_INTEL,
    "EchoFort AI": Permission.ECHOFORT_AI,
    "Deep Analytics": Permission.DEEP_ANALYTICS,
    "Data Core": Permission.DATA_CORE,
    "System Config": Permission.SYSTEM_CONFIG,
    "WhatsApp Support": Permission.WHATSAPP_SUPPORT,
    "Recovery Codes": Permission.RECOVERY_CODES,
    "AI Learning Center": Permission.AI_LEARNING_CENTER,
    "AI Pending Actions": Permission.AI_PENDING_ACTIONS,
}


def get_sidebar_items_for_role(role: str) -> List[str]:
    """
    Get list of sidebar items that should be visible for a role.
    
    Args:
        role: Role string (e.g., "super_admin", "admin")
    
    Returns:
        List of sidebar item names that the role can access
    """
    visible_items = []
    for item_name, required_permission in SIDEBAR_ITEMS.items():
        if has_permission(role, required_permission.value):
            visible_items.append(item_name)
    return visible_items
