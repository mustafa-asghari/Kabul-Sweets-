'use client';

import { useCallback, useState } from 'react';

import {
  Anchor,
  Button,
  Center,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconMoodEmpty, IconPlus } from '@tabler/icons-react';

import { CustomersTable, ErrorAlert, PageHeader, Surface, RoleGuard } from '@/components';
import type { UserResponse } from '@/types';
import { useUsers } from '@/lib/hooks/useApi';
import { PATH_DASHBOARD } from '@/routes';

import { EditCustomerDrawer } from './components/EditCustomerDrawer';
import { NewCustomerDrawer } from './components/NewCustomerDrawer';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.ecommerce },
  { title: 'Admin', href: '#' },
  { title: 'Users', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

function Customers() {
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null);

  const {
    data: usersData,
    loading: usersLoading,
    error: usersError,
    refetch: refetchUsers,
  } = useUsers();

  const [newDrawerOpened, { open: newCustomerOpen, close: newCustomerClose }] =
    useDisclosure(false);

  const [editDrawerOpened, { open: editCustomerOpen, close: editCustomerClose }] =
    useDisclosure(false);

  const handleCustomerCreated = useCallback(() => {
    refetchUsers();
  }, [refetchUsers]);

  const handleCustomerUpdated = useCallback(() => {
    refetchUsers();
  }, [refetchUsers]);

  const handleEditUser = (user: UserResponse) => {
    setSelectedUser(user);
    editCustomerOpen();
  };

  const handleViewUser = (user: UserResponse) => {
    setSelectedUser(user);
    editCustomerOpen();
  };

  const renderContent = () => {
    if (loadingFallback) return loadingFallback; // Should not happen inside RoleGuard logic usually

    if (usersLoading) {
      return (
        <Surface>
          <Stack gap="sm" p="md">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={`user-loading-${i}`} visible={true} height={40} />
            ))}
          </Stack>
        </Surface>
      );
    }

    if (usersError) {
      return (
        <ErrorAlert
          title="Error loading users"
          message={usersError?.message || 'Failed to load users'}
        />
      );
    }

    if (!usersData?.data?.length) {
      return (
        <Surface p="md">
          <Stack align="center">
            <IconMoodEmpty size={24} />
            <Title order={4}>No users found</Title>
            <Text>No users in the system yet.</Text>
            <Button leftSection={<IconPlus size={18} />} onClick={newCustomerOpen}>
              New User
            </Button>
          </Stack>
        </Surface>
      );
    }

    return (
      <Surface mt="md">
        <CustomersTable
          data={usersData.data}
          loading={false}
          onEdit={handleEditUser}
          onView={handleViewUser}
        />
      </Surface>
    );
  };

  // Helper to fix typescript complaint about loadingFallback if I used it
  const loadingFallback = null;

  return (
    <RoleGuard
      allowedRoles={['admin']}
      fallback={
        <Center h="50vh">
          <Stack align="center">
            <Title order={3}>Access Denied</Title>
            <Text c="dimmed">You do not have permission to view this page.</Text>
          </Stack>
        </Center>
      }
    >
      <>
        <>
          <title>Users | Kabul Sweets Admin</title>
          <meta name="description" content="Manage users" />
        </>
        <PageHeader
          title="User Management"
          breadcrumbItems={items}
          actionButton={
            usersData?.data && usersData.data?.length > 0 ? (
              <Button
                leftSection={<IconPlus size={18} />}
                onClick={newCustomerOpen}
              >
                New User
              </Button>
            ) : undefined
          }
        />

        {renderContent()}

        <NewCustomerDrawer
          opened={newDrawerOpened}
          onClose={newCustomerClose}
          position="right"
          onCustomerCreated={handleCustomerCreated}
        />

        <EditCustomerDrawer
          opened={editDrawerOpened}
          onClose={editCustomerClose}
          position="right"
          customer={selectedUser}
          onCustomerUpdated={handleCustomerUpdated}
        />
      </>
    </RoleGuard>
  );
}

export default Customers;
