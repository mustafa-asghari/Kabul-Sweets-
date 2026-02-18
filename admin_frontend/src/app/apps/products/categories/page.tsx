'use client';

import {
  Alert,
  Anchor,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useFetch } from '@mantine/hooks';
import { IconInfoCircle, IconMoodEmpty } from '@tabler/icons-react';

import { ErrorAlert, PageHeader, Surface } from '@/components';
import { PATH_DASHBOARD } from '@/routes';
import { IApiResponse } from '@/types/api-response';
import { IProductCategory } from '@/types/products';

import { CategoryCard } from './components/CategoryCard';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.default },
  { title: 'Apps', href: '#' },
  { title: 'Products', href: '#' },
  { title: 'Categories', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

function Categories() {
  const {
    data: categoriesData,
    loading: categoriesLoading,
    error: categoriesError,
  } = useFetch<IApiResponse<IProductCategory[]>>('/api/product-categories', {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const categoryItems = categoriesData?.data?.map((category) => (
    <CategoryCard key={category.id} data={category} />
  ));

  const renderContent = () => {
    if (categoriesLoading) {
      return (
        <SimpleGrid
          cols={{ base: 1, sm: 2, lg: 3, xl: 4 }}
          spacing={{ base: 10, sm: 'xl' }}
          verticalSpacing={{ base: 'md', sm: 'xl' }}
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton
              key={`category-loading-${i}`}
              visible={true}
              height={150}
            />
          ))}
        </SimpleGrid>
      );
    }

    if (categoriesError || !categoriesData?.succeeded) {
      return (
        <ErrorAlert
          title="Error loading categories"
          message={categoriesData?.errors?.join(',')}
        />
      );
    }

    if (!categoriesData?.data?.length) {
      return (
        <Surface p="md">
          <Stack align="center">
            <IconMoodEmpty size={24} />
            <Title order={4}>No categories found</Title>
            <Text>
              No product categories are available.
            </Text>
          </Stack>
        </Surface>
      );
    }

    return (
      <SimpleGrid
        cols={{ base: 1, sm: 2, lg: 3, xl: 4 }}
        spacing={{ base: 10, sm: 'xl' }}
        verticalSpacing={{ base: 'md', sm: 'xl' }}
      >
        {categoryItems}
      </SimpleGrid>
    );
  };

  return (
    <>
      <>
        <title>Product Categories | Kabul Sweets</title>
        <meta
          name="description"
          content="View available product categories"
        />
      </>
      <PageHeader title="Product Categories" breadcrumbItems={items} />

      <Alert
        mb="lg"
        variant="light"
        color="indigo"
        icon={<IconInfoCircle size={16} />}
        title="Categories are predefined"
      >
        Product categories are configured in the backend as system values and
        cannot be created, edited, or deleted from the admin dashboard.
      </Alert>

      {renderContent()}
    </>
  );
}

export default Categories;
