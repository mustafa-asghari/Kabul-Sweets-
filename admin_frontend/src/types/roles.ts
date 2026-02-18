/**
 * User roles for role-based access control (RBAC)
 */
export enum UserRole {
    ADMIN = 'admin',
    STAFF = 'staff',
    CUSTOMER = 'customer',
}

/**
 * Permissions by role
 */
export const ROLE_PERMISSIONS = {
    [UserRole.ADMIN]: {
        canViewSensitiveData: true,
        canManageUsers: true,
        canManageProducts: true,
        canViewAnalytics: true,
        canManageOrders: true,
        canViewFinancials: true,
        canManageSettings: true,
    },
    [UserRole.STAFF]: {
        canViewSensitiveData: false, // Staff cannot see sensitive info
        canManageUsers: false,
        canManageProducts: true,
        canViewAnalytics: true,
        canManageOrders: true,
        canViewFinancials: false, // No financial access
        canManageSettings: false,
    },
    [UserRole.CUSTOMER]: {
        canViewSensitiveData: false,
        canManageUsers: false,
        canManageProducts: false,
        canViewAnalytics: false,
        canManageOrders: false,
        canViewFinancials: false,
        canManageSettings: false,
    },
} as const;

export type Permission = keyof typeof ROLE_PERMISSIONS[UserRole.ADMIN];
