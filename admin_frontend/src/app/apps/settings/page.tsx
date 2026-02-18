'use client';

import { useEffect, useState } from 'react';

import {
  Anchor,
  Box,
  Button,
  Container,
  Grid,
  PaperProps,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconDeviceFloppy } from '@tabler/icons-react';

import { PageHeader, Surface } from '@/components';
import { apiPatch } from '@/lib/hooks/useApi';
import { useAuth } from '@/contexts/auth/AuthContext';
import { PATH_DASHBOARD } from '@/routes';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.default },
  { title: 'Apps', href: '#' },
  { title: 'Settings', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

const PAPER_PROPS: PaperProps = {
  p: 'md',
  style: { minHeight: '100%' },
};

function Settings() {
  const { user, refreshUser } = useAuth();
  const [saving, setSaving] = useState(false);

  const form = useForm({
    initialValues: {
      full_name: '',
      phone: '',
    },
    validate: {
      full_name: (value) =>
        value.trim().length < 1 ? 'Name is required' : null,
    },
  });

  useEffect(() => {
    if (user) {
      form.setValues({
        full_name: user.full_name || '',
        phone: user.phone || '',
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleSave = async () => {
    const validation = form.validate();
    if (validation.hasErrors) return;

    setSaving(true);
    try {
      const result = await apiPatch('/api/auth/me', {
        full_name: form.values.full_name,
        phone: form.values.phone || null,
      });

      if (!result.succeeded) {
        throw new Error(result.message || 'Failed to update profile');
      }

      await refreshUser();

      notifications.show({
        title: 'Success',
        message: 'Profile updated successfully',
        color: 'green',
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error ? error.message : 'Failed to update profile',
        color: 'red',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <>
        <title>Settings | Kabul Sweets</title>
        <meta name="description" content="Manage your account settings" />
      </>
      <Container fluid>
        <Stack gap="lg">
          <PageHeader title="Settings" breadcrumbItems={items} />
          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Surface {...PAPER_PROPS}>
                <Stack>
                  <Text size="lg" fw={600}>
                    Profile Information
                  </Text>
                  <TextInput
                    label="Full Name"
                    placeholder="Your full name"
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
                  <Box style={{ width: 'auto' }}>
                    <Button
                      leftSection={<IconDeviceFloppy size={16} />}
                      onClick={handleSave}
                      loading={saving}
                    >
                      Save Changes
                    </Button>
                  </Box>
                </Stack>
              </Surface>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Surface {...PAPER_PROPS}>
                <Stack>
                  <Text size="lg" fw={600}>
                    Account Details
                  </Text>
                  <TextInput
                    label="Email"
                    value={user?.email || ''}
                    readOnly
                    disabled
                  />
                  <TextInput
                    label="Role"
                    value={user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : ''}
                    readOnly
                    disabled
                  />
                  <TextInput
                    label="Status"
                    value={user?.is_active ? 'Active' : 'Inactive'}
                    readOnly
                    disabled
                  />
                  <TextInput
                    label="Member Since"
                    value={
                      user?.created_at
                        ? new Date(user.created_at).toLocaleDateString('en-AU', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })
                        : ''
                    }
                    readOnly
                    disabled
                  />
                </Stack>
              </Surface>
            </Grid.Col>
          </Grid>
        </Stack>
      </Container>
    </>
  );
}

export default Settings;
