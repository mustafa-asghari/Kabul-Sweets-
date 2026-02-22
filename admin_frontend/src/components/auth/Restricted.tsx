'use client';

import { ReactNode } from 'react';
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/types/roles';
import { useAuth } from '@/contexts/auth/AuthContext';

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
    loadingFallback?: ReactNode;
}

/**
 * Component that restricts content based on user roles
 * Usage: <RoleGuard allowedRoles={['admin']}>Admin only content</RoleGuard>
 */
export function RoleGuard({
    children,
    allowedRoles,
    fallback = null,
    loadingFallback = null,
}: RoleGuardProps) {
    const { user, isLoading } = useAuth();

    if (isLoading) {
        return <>{loadingFallback}</>;
    }

    const normalizedRole = (user?.role || '').toLowerCase().trim();
    const normalizedAllowedRoles = allowedRoles.map((role) => role.toLowerCase().trim());

    if (!normalizedRole || !normalizedAllowedRoles.includes(normalizedRole)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
