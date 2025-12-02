"""
RBAC (Role-Based Access Control) Module
Block 24 - Part A
"""

from .permissions import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    PERMISSION_ROLES,
    SIDEBAR_ITEMS,
    has_permission,
    get_permissions,
    get_roles_for_permission,
    is_admin_role,
    get_sidebar_items_for_role,
)

from .middleware import (
    guard_admin,
    guard_support,
    guard_marketing,
    guard_accounting,
    guard_admin_legacy,
)

__all__ = [
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "PERMISSION_ROLES",
    "SIDEBAR_ITEMS",
    "has_permission",
    "get_permissions",
    "get_roles_for_permission",
    "is_admin_role",
    "get_sidebar_items_for_role",
    "guard_admin",
    "guard_support",
    "guard_marketing",
    "guard_accounting",
    "guard_admin_legacy",
]
