'use client';

import { useState } from 'react';

import {
  Button,
  Drawer,
  DrawerProps,
  LoadingOverlay,
  PasswordInput,
  Select,
  Stack,
  TextInput,
  Title,
} from '@mantine/core';
import { isEmail, isNotEmpty, useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';

import { apiPost } from '@/lib/hooks/useApi';
import type { UserResponse, UserCreateAdmin } from '@/types/user';

type NewCustomerDrawerProps = Omit<DrawerProps, 'title' | 'children'> & {
  onCustomerCreated?: () => void;
};

export const NewCustomerDrawer = ({
  onCustomerCreated,
  ...drawerProps
}: NewCustomerDrawerProps) => {
  const [loading, setLoading] = useState(false);

  const form = useForm({
    mode: 'controlled',
    initialValues: {
      email: '',
      password: '',
      full_name: '',
      phone: '',
      role: 'customer',
    },
    validate: {
      full_name: isNotEmpty('Name cannot be empty'),
      email: isEmail('Invalid email'),
      password: (value) =>
        value.length < 8 ? 'Password must be at least 8 characters' : null,
    },
  });

  const handleSubmit = async (values: typeof form.values) => {
    setLoading(true);
    try {
      const payload: UserCreateAdmin = {
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        phone: values.phone || undefined,
        role: values.role,
      };

      const result = await apiPost<UserResponse>('/api/customers', payload);

      if (!result.succeeded) {
        throw new Error(result.message || 'Failed to create user');
      }

      notifications.show({
        title: 'User Created',
        message: `${values.full_name} has been created successfully.`,
        color: 'green',
      });

      form.reset();
      drawerProps.onClose?.();
      onCustomerCreated?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error ? error.message : 'Failed to create user',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Drawer {...drawerProps} title="Create New User" size="md">
      <LoadingOverlay visible={loading} />
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <Title order={4}>User Information</Title>
          <TextInput
            label="Full Name"
            placeholder="Enter full name"
            key={form.key('full_name')}
            {...form.getInputProps('full_name')}
            required
          />
          <TextInput
            label="Email"
            placeholder="user@example.com"
            key={form.key('email')}
            {...form.getInputProps('email')}
            required
          />
          <PasswordInput
            label="Password"
            placeholder="Minimum 8 characters"
            key={form.key('password')}
            {...form.getInputProps('password')}
            required
          />
          <TextInput
            label="Phone"
            placeholder="+61 400 000 000"
            key={form.key('phone')}
            {...form.getInputProps('phone')}
          />
          <Select
            label="Role"
            data={[
              { value: 'customer', label: 'Customer' },
              { value: 'staff', label: 'Staff' },
              { value: 'admin', label: 'Admin' },
            ]}
            key={form.key('role')}
            {...form.getInputProps('role')}
            required
          />

          <Button type="submit" mt="md" loading={loading}>
            Create User
          </Button>
        </Stack>
      </form>
    </Drawer>
  );
};
