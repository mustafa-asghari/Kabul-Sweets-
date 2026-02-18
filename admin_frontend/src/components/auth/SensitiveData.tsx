'use client';

import { ReactNode } from 'react';
import { Box, Text } from '@mantine/core';
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/types/roles';

interface SensitiveDataProps {
    children: ReactNode;
    permission?: Permission;
    blurAmount?: number;
}

/**
 * Component that blurs sensitive data for unauthorized users
 * Usage: <SensitiveData permission="canViewSensitiveData">$12,345.67</SensitiveData>
 */
export function SensitiveData({
    children,
    permission = 'canViewSensitiveData',
    blurAmount = 8
}: SensitiveDataProps) {
    const { hasPermission } = usePermissions();

    if (!hasPermission(permission)) {
        return (
            <Box
                style={{
                    filter: `blur(${blurAmount}px)`,
                    userSelect: 'none',
                    cursor: 'not-allowed',
                }}
                component="span"
            >
                {children}
            </Box>
        );
    }

    return <>{children}</>;
}

interface MaskedDataProps {
    children: ReactNode;
    permission?: Permission;
    maskChar?: string;
}

/**
 * Component that masks sensitive data with asterisks for unauthorized users
 * Usage: <MaskedData permission="canViewSensitiveData">4532-1234-5678-9012</MaskedData>
 */
export function MaskedData({
    children,
    permission = 'canViewSensitiveData',
    maskChar = '•'
}: MaskedDataProps) {
    const { hasPermission } = usePermissions();

    if (!hasPermission(permission)) {
        const text = String(children);
        const masked = maskChar.repeat(Math.min(text.length, 12));
        return <Text component="span">{masked}</Text>;
    }

    return <>{children}</>;
}
