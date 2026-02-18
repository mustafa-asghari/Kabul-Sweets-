# Role-Based Access Control (RBAC) Implementation

## Overview

This admin dashboard implements a two-tier user system:
- **ADMIN**: Full access to all features including sensitive data
- **STAFF**: Limited access, cannot view sensitive information like financials, customer data, etc.

## User Roles

### Admin (`admin`)
- Full system access
- Can view sensitive data (revenue, customer details, etc.)
- Can manage users and settings
- Can view financial reports

### Staff (`staff`)
- Basic dashboard access
- Can manage products and orders
- Can view analytics (non-sensitive)
- **Cannot** view sensitive financial data
- **Cannot** manage other users
- **Cannot** access system settings

### Customer (`customer`)
- Not allowed in admin dashboard

## Usage

### Using the usePermissions Hook

```typescript
import { usePermissions } from '@/hooks/usePermissions';

function MyComponent() {
  const { canViewSensitiveData, isAdmin, isStaff } = usePermissions();

  return (
    <div>
      {canViewSensitiveData && <div>Revenue: $12,345</div>}
      {isAdmin && <Button>Manage Users</Button>}
    </div>
  );
}
```

### Using the Restricted Component

```typescript
import { Restricted } from '@/components/auth';

function Dashboard() {
  return (
    <div>
      <Restricted permission="canViewFinancials">
        <RevenueChart />
      </Restricted>
      
      <Restricted 
        permission="canManageUsers"
        fallback={<Text>You don't have permission to manage users</Text>}
      >
        <UserManagement />
      </Restricted>
    </div>
  );
}
```

### Using the RoleGuard Component

```typescript
import { RoleGuard } from '@/components/auth';

function Settings() {
  return (
    <RoleGuard allowedRoles={['admin']}>
      <SystemSettings />
    </RoleGuard>
  );
}
```

### Using SensitiveData Components

```typescript
import { SensitiveData, MaskedData } from '@/components/auth';

function OrderDetails() {
  return (
    <div>
      <div>
        Customer Email: 
        <MaskedData>customer@example.com</MaskedData>
      </div>
      
      <div>
        Revenue: 
        <SensitiveData>$12,345.67</SensitiveData>
      </div>
    </div>
  );
}
```

## Permissions

Available permissions:
- `canViewSensitiveData` - View sensitive customer/financial data
- `canManageUsers` - Create, edit, delete users
- `canManageProducts` - Manage product catalog
- `canViewAnalytics` - View analytics dashboards
- `canManageOrders` - Process and manage orders
- `canViewFinancials` - View financial reports and revenue
- `canManageSettings` - Access system settings

## Backend Integration

The frontend communicates with the backend `/api/auth/me` endpoint to retrieve the current user's profile and role. The backend enforces authorization using:

- `require_admin` - Admin-only endpoints
- `require_staff_or_admin` - Endpoints accessible by both staff and admin

## Example API Routes

```python
# Admin only
@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users():
    ...

# Staff or Admin
@router.get("/products", dependencies=[Depends(require_staff_or_admin)])
async def list_products():
    ...
```
