'use client';

import { useState } from 'react';

import {
  Alert,
  Button,
  Center,
  Checkbox,
  Group,
  Paper,
  PasswordInput,
  Text,
  TextInput,
  TextProps,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertCircle } from '@tabler/icons-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';

import { Surface } from '@/components';
import { useAuth } from '@/contexts/auth';
import { PATH_AUTH, PATH_DASHBOARD } from '@/routes';

import classes from './page.module.css';

const LINK_PROPS: TextProps = {
  className: classes.link,
};

function Page() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || PATH_DASHBOARD.ecommerce;
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const form = useForm({
    initialValues: {
      email: 'admin@kabulsweets.com.au',
      password: 'Admin@2024!',
    },
    validate: {
      email: (value: string) =>
        /^\S+@\S+$/.test(value) ? null : 'Invalid email',
      password: (value: string | undefined) =>
        value && value?.length < 6
          ? 'Password must include at least 6 characters'
          : null,
    },
  });

  const handleSubmit = async (values: typeof form.values) => {
    try {
      setIsLoading(true);
      setError(null);

      const result = await login(values.email, values.password);

      if (result.success) {
        router.push(callbackUrl);
      } else {
        setError(result.error || 'Login failed');
      }
    } catch (error) {
      setError('An unexpected error occurred');
      console.error('Sign in error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <title>Sign in | Kabul Sweets Admin</title>
      <meta
        name="description"
        content="Sign in to Kabul Sweets admin dashboard."
      />

      <Title ta="center">Welcome back!</Title>
      <Text ta="center">Sign in to your account to continue</Text>

      <Surface component={Paper} className={classes.card}>
        {error && (
          <Alert
            icon={<IconAlertCircle size="1rem" />}
            title="Authentication Error"
            color="red"
            mb="md"
          >
            {error}
          </Alert>
        )}

        <form onSubmit={form.onSubmit(handleSubmit)}>
          <TextInput
            label="Email"
            placeholder="admin@kabulsweets.com.au"
            required
            classNames={{ label: classes.label }}
            {...form.getInputProps('email')}
          />
          <PasswordInput
            label="Password"
            placeholder="Your password"
            required
            mt="md"
            classNames={{ label: classes.label }}
            {...form.getInputProps('password')}
          />
          <Group justify="space-between" mt="lg">
            <Checkbox
              label="Remember me"
              classNames={{ label: classes.label }}
            />
            <Text
              component={Link}
              href={PATH_AUTH.passwordReset}
              size="sm"
              {...LINK_PROPS}
            >
              Forgot password?
            </Text>
          </Group>
          <Button fullWidth mt="xl" type="submit" loading={isLoading}>
            Sign in
          </Button>
        </form>
        <Center mt="md">
          <Text
            fz="sm"
            ta="center"
            component={Link}
            href={PATH_AUTH.signup}
            {...LINK_PROPS}
          >
            Do not have an account yet? Create account
          </Text>
        </Center>
      </Surface>
    </>
  );
}

export default Page;
