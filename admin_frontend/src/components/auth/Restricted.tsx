'use client';

import { ReactNode } from 'react';
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/types/roles';

interface RestrictedProps {
    children: ReactNode;
    permission: Permission;
    fallback?: ReactNode;
}

/**
 * Component that restricts content based on user permissions
 * Usage: <Restricted permission="canViewSensitiveData">Sensitive content</Restricted>
 */
export function Restricted({ children, permission, fallback = null }: RestrictedProps) {
    const { hasPermission } = usePermissions();

    if (!hasPermission(permission)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}

interface RoleGuardProps {
    children: ReactNode;
    allowedRoles: string[];
    fallback?: ReactNode;
}

/**
 * Component that restricts content based on user roles
 * Usage: <RoleGuard allowedRoles={['admin']}>Admin only content</RoleGuard>
 */
export function RoleGuard({ children, allowedRoles, fallback = null }: RoleGuardProps) {
    const { user } = usePermissions() as any;

    if (!user || !allowedRoles.includes(user.role)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
