'use client';

import { useEffect, useState } from 'react';

import {
  Badge,
  Button,
  Drawer,
  DrawerProps,
  Group,
  LoadingOverlay,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { isEmail, isNotEmpty, useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';

import { apiPatch } from '@/lib/hooks/useApi';
import type { UserResponse } from '@/types/user';

interface EditCustomerFormValues {
  full_name: string;
  phone: string;
}

type EditCustomerDrawerProps = Omit<DrawerProps, 'title' | 'children'> & {
  customer: UserResponse | null;
  onCustomerUpdated?: () => void;
};

export const EditCustomerDrawer = ({
  customer,
  onCustomerUpdated,
  ...drawerProps
}: EditCustomerDrawerProps) => {
  const [loading, setLoading] = useState(false);

  const form = useForm<EditCustomerFormValues>({
    mode: 'controlled',
    initialValues: {
      full_name: '',
      phone: '',
    },
    validate: {
      full_name: isNotEmpty('Name cannot be empty'),
    },
  });

  const handleSubmit = async (values: EditCustomerFormValues) => {
    if (!customer?.id) return;

    setLoading(true);
    try {
      const result = await apiPatch<UserResponse>(
        `/api/customers/${customer.id}`,
        {
          full_name: values.full_name,
          phone: values.phone || null,
        }
      );

      if (!result.succeeded) {
        throw new Error(result.message || 'Failed to update user');
      }

      notifications.show({
        title: 'User Updated',
        message: `${values.full_name} has been updated successfully.`,
        color: 'green',
      });

      drawerProps.onClose?.();
      onCustomerUpdated?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error ? error.message : 'Failed to update user',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async () => {
    if (!customer?.id) return;

    setLoading(true);
    try {
      const action = customer.is_active ? 'deactivate' : 'activate';
      const result = await apiPatch<{ message: string }>(
        `/api/customers/${customer.id}/${action}`,
        {}
      );

      if (!result.succeeded) {
        throw new Error(result.message || `Failed to ${action} user`);
      }

      notifications.show({
        title: 'Success',
        message: `User ${action}d successfully.`,
        color: 'green',
      });

      drawerProps.onClose?.();
      onCustomerUpdated?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: error instanceof Error ? error.message : 'Action failed',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (customer) {
      form.setValues({
        full_name: customer.full_name || '',
        phone: customer.phone || '',
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customer]);

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-AU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <Drawer {...drawerProps} title="User Details" size="md">
      <LoadingOverlay visible={loading} />

      {customer && (
        <Stack>
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={4}>{customer.full_name}</Title>
              <Text size="sm" c="dimmed">
                {customer.email}
              </Text>
            </div>
            <Group gap="xs">
              <Badge
                color={customer.role === 'admin' ? 'blue' : customer.role === 'staff' ? 'indigo' : 'gray'}
                variant="light"
              >
                {customer.role}
              </Badge>
              <Badge
                color={customer.is_active ? 'green' : 'red'}
                variant="filled"
                size="sm"
              >
                {customer.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </Group>
          </Group>

          <Group grow>
            <Stack gap={4}>
              <Text size="xs" c="dimmed">Joined</Text>
              <Text size="sm" fw={500}>{formatDate(customer.created_at)}</Text>
            </Stack>
            <Stack gap={4}>
              <Text size="xs" c="dimmed">Last Login</Text>
              <Text size="sm" fw={500}>{formatDate(customer.last_login)}</Text>
            </Stack>
          </Group>

          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack>
              <Title order={4} mt="md">Edit Information</Title>
              <TextInput
                label="Full Name"
                placeholder="Enter full name"
                key={form.key('full_name')}
                {...form.getInputProps('full_name')}
                required
              />
              <TextInput
                label="Phone"
                placeholder="+61 400 000 000"
                key={form.key('phone')}
                {...form.getInputProps('phone')}
              />

              <Group justify="space-between" mt="xl">
                <Button
                  color={customer.is_active ? 'red' : 'green'}
                  onClick={handleToggleActive}
                  variant="outline"
                >
                  {customer.is_active ? 'Deactivate' : 'Activate'} User
                </Button>
                <Button type="submit" loading={loading}>
                  Update User
                </Button>
              </Group>
            </Stack>
          </form>
        </Stack>
      )}
    </Drawer>
  );
};
