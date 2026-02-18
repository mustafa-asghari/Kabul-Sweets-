'use client';

import { useState } from 'react';

import {
  Alert,
  Button,
  Center,
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
import { useRouter } from 'next/navigation';

import { Surface } from '@/components';
import { PATH_AUTH } from '@/routes';

import classes from './page.module.css';

const LINK_PROPS: TextProps = {
  className: classes.link,
};

function Page() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm({
    initialValues: {
      full_name: '',
      email: '',
      password: '',
      confirmPassword: '',
      phone: '',
    },
    validate: {
      full_name: (value) =>
        value.trim().length < 1 ? 'Name is required' : null,
      email: (value) =>
        /^\S+@\S+$/.test(value) ? null : 'Invalid email',
      password: (value) =>
        value.length < 8 ? 'Password must be at least 8 characters' : null,
      confirmPassword: (value, values) =>
        value !== values.password ? 'Passwords do not match' : null,
    },
  });

  const handleSubmit = async (values: typeof form.values) => {
    try {
      setIsLoading(true);
      setError(null);

      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: values.email,
          password: values.password,
          full_name: values.full_name,
          phone: values.phone || undefined,
        }),
      });

      const json = await res.json();

      if (!res.ok || !json.succeeded) {
        setError(json.message || 'Registration failed');
        return;
      }

      // Redirect to signin with success message
      router.push(`${PATH_AUTH.signin}?registered=true`);
    } catch {
      setError('Could not connect to server');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <title>Sign up | Kabul Sweets</title>
      <meta
        name="description"
        content="Create a Kabul Sweets account."
      />

      <Title ta="center">Welcome!</Title>
      <Text ta="center">Create your account to continue</Text>

      <Surface component={Paper} className={classes.card}>
        {error && (
          <Alert
            icon={<IconAlertCircle size="1rem" />}
            title="Registration Error"
            color="red"
            mb="md"
          >
            {error}
          </Alert>
        )}

        <form onSubmit={form.onSubmit(handleSubmit)}>
          <TextInput
            label="Full Name"
            placeholder="John Doe"
            required
            classNames={{ label: classes.label }}
            {...form.getInputProps('full_name')}
          />
          <TextInput
            label="Email"
            placeholder="you@example.com"
            required
            mt="md"
            classNames={{ label: classes.label }}
            {...form.getInputProps('email')}
          />
          <TextInput
            label="Phone (optional)"
            placeholder="+61 400 000 000"
            mt="md"
            classNames={{ label: classes.label }}
            {...form.getInputProps('phone')}
          />
          <PasswordInput
            label="Password"
            placeholder="Minimum 8 characters"
            required
            mt="md"
            classNames={{ label: classes.label }}
            {...form.getInputProps('password')}
          />
          <PasswordInput
            label="Confirm Password"
            placeholder="Confirm password"
            required
            mt="md"
            classNames={{ label: classes.label }}
            {...form.getInputProps('confirmPassword')}
          />
          <Button fullWidth mt="xl" type="submit" loading={isLoading}>
            Create account
          </Button>
        </form>
        <Center mt="md">
          <Text
            size="sm"
            component={Link}
            href={PATH_AUTH.signin}
            {...LINK_PROPS}
          >
            Already have an account? Sign in
          </Text>
        </Center>
      </Surface>
    </>
  );
}

export default Page;
