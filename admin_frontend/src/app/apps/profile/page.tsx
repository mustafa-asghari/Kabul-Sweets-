'use client';

import {
  Anchor,
  Container,
  Grid,
  Group,
  Paper,
  PaperProps,
  Stack,
  Text,
} from '@mantine/core';
import {
  IconHome,
  IconMapPinFilled,
  IconMail,
  IconPhone,
} from '@tabler/icons-react';

import {
  PageHeader,
  Surface,
  UserProfileCard,
} from '@/components';
import { useAuth } from '@/contexts/auth/AuthContext';
import { PATH_DASHBOARD } from '@/routes';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.default },
  { title: 'Apps', href: '#' },
  { title: 'Profile', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

const PAPER_PROPS: PaperProps = {
  p: 'md',
  style: { minHeight: '100%' },
};

function Profile() {
  const { user } = useAuth();

  const userData = {
    avatar: '',
    name: user?.full_name || 'User',
    email: user?.email || '',
    job: user?.role.toUpperCase() || 'STAFF',
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-AU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <>
      <>
        <title>Profile | Kabul Sweets</title>
        <meta
          name="description"
          content="User profile management"
        />
      </>
      <Container fluid>
        <Stack gap="lg">
          <PageHeader title="Profile" breadcrumbItems={items} />
          <Grid>
            <Grid.Col span={{ base: 12, md: 5, lg: 4 }}>
              <Stack>
                <UserProfileCard data={userData} {...PAPER_PROPS} />
                <Surface {...PAPER_PROPS}>
                  <Stack>
                    <Text size="lg" fw={600}>
                      About
                    </Text>
                    <Group>
                      <IconMail size={16} />
                      <Text>{user?.email || '-'}</Text>
                    </Group>
                    {user?.phone && (
                      <Group>
                        <IconPhone size={16} />
                        <Text>{user.phone}</Text>
                      </Group>
                    )}
                    <Group>
                      <IconHome size={16} />
                      <Text>Kabul Sweets</Text>
                    </Group>
                    <Group>
                      <IconMapPinFilled size={16} />
                      <Text>Member since {formatDate(user?.created_at)}</Text>
                    </Group>
                  </Stack>
                </Surface>
              </Stack>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 7, lg: 8 }}>
              <Surface {...PAPER_PROPS}>
                <Stack>
                  <Text size="lg" fw={600}>
                    Account Details
                  </Text>
                  <Group>
                    <Text fw={500} w={120}>Role:</Text>
                    <Text tt="capitalize">{user?.role || '-'}</Text>
                  </Group>
                  <Group>
                    <Text fw={500} w={120}>Status:</Text>
                    <Text c={user?.is_active ? 'green' : 'red'}>
                      {user?.is_active ? 'Active' : 'Inactive'}
                    </Text>
                  </Group>
                  <Group>
                    <Text fw={500} w={120}>Last Login:</Text>
                    <Text>{formatDate(user?.last_login)}</Text>
                  </Group>
                </Stack>
              </Surface>
            </Grid.Col>
          </Grid>
        </Stack>
      </Container>
    </>
  );
}

export default Profile;
