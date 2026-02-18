'use client';

import { useAuth } from '@/contexts/auth/AuthContext';
import { UserRole, ROLE_PERMISSIONS, Permission } from '@/types/roles';

/**
 * Hook to check user permissions based on their role
 */
export function usePermissions() {
    const { user, isAuthenticated } = useAuth();

    const hasPermission = (permission: Permission): boolean => {
        if (!isAuthenticated || !user) return false;

        const userRole = user.role as UserRole;
        const rolePermissions = ROLE_PERMISSIONS[userRole];

        return rolePermissions?.[permission] ?? false;
    };

    const isAdmin = user?.role === UserRole.ADMIN;
    const isStaff = user?.role === UserRole.STAFF;
    const isCustomer = user?.role === UserRole.CUSTOMER;
    const isStaffOrAdmin = isAdmin || isStaff;

    return {
        hasPermission,
        isAdmin,
        isStaff,
        isCustomer,
        isStaffOrAdmin,
        // Quick permission checks
        canViewSensitiveData: hasPermission('canViewSensitiveData'),
        canManageUsers: hasPermission('canManageUsers'),
        canManageProducts: hasPermission('canManageProducts'),
        canViewAnalytics: hasPermission('canViewAnalytics'),
        canManageOrders: hasPermission('canManageOrders'),
        canViewFinancials: hasPermission('canViewFinancials'),
        canManageSettings: hasPermission('canManageSettings'),
    };
}
