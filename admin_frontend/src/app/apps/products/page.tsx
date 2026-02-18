'use client';

import { useCallback, useState } from 'react';

import {
  Anchor,
  Badge,
  Button,
  PaperProps,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconMoodEmpty, IconPlus } from '@tabler/icons-react';

import EditProductDrawer from '@/app/apps/products/components/EditProductDrawer';
import NewProductDrawer from '@/app/apps/products/components/NewProductDrawer';
import { ErrorAlert, PageHeader, Surface } from '@/components';
import { useProducts } from '@/lib/hooks/useApi';
import { PATH_DASHBOARD } from '@/routes';
import type { ProductListItem } from '@/types/products';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.ecommerce },
  { title: 'Store', href: '#' },
  { title: 'Products', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

const CARD_PROPS: Omit<PaperProps, 'children'> = {
  p: 'md',
  shadow: 'md',
  radius: 'md',
};

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(
    amount
  );

function ProductCard({
  product,
  onEdit,
}: {
  product: ProductListItem;
  onEdit: (p: ProductListItem) => void;
}) {
  const totalStock = product.variants?.reduce(
    (sum, v) => sum + v.stock_quantity,
    0
  ) || 0;

  return (
    <Surface {...CARD_PROPS}>
      <Stack gap="xs">
        <Title order={5}>{product.name}</Title>
        {product.short_description && (
          <Text size="sm" c="dimmed" lineClamp={2}>
            {product.short_description}
          </Text>
        )}
        <Text fw={600}>{formatCurrency(Number(product.base_price))}</Text>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          <Badge size="sm" variant="light">
            {product.category}
          </Badge>
          {product.is_cake && (
            <Badge size="sm" color="pink" variant="light">
              Cake
            </Badge>
          )}
          {product.is_featured && (
            <Badge size="sm" color="yellow" variant="light">
              Featured
            </Badge>
          )}
          {!product.is_active && (
            <Badge size="sm" color="red" variant="light">
              Inactive
            </Badge>
          )}
        </div>
        <Text size="xs" c="dimmed">
          {product.variants?.length || 0} variants | Stock: {totalStock}
        </Text>
        <Button size="xs" variant="light" onClick={() => onEdit(product)}>
          Edit
        </Button>
      </Stack>
    </Surface>
  );
}

function Products() {
  const [selectedProduct, setSelectedProduct] =
    useState<ProductListItem | null>(null);

  const {
    data: productsData,
    loading: productsLoading,
    error: productsError,
    refetch: refetchProducts,
  } = useProducts();

  const [newDrawerOpened, { open: newProductOpen, close: newProductClose }] =
    useDisclosure(false);

  const [editDrawerOpened, { open: editProductOpen, close: editProductClose }] =
    useDisclosure(false);

  const handleProductCreated = useCallback(() => {
    refetchProducts();
  }, [refetchProducts]);

  const handleProductUpdated = useCallback(() => {
    refetchProducts();
  }, [refetchProducts]);

  const handleEditProduct = (product: ProductListItem) => {
    setSelectedProduct(product);
    editProductOpen();
  };

  const renderContent = () => {
    if (productsLoading) {
      return (
        <SimpleGrid
          cols={{ base: 1, sm: 2, lg: 3, xl: 4 }}
          spacing={{ base: 10, sm: 'xl' }}
          verticalSpacing={{ base: 'md', sm: 'xl' }}
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={`product-loading-${i}`} visible={true} height={200} />
          ))}
        </SimpleGrid>
      );
    }

    if (productsError || (productsData && !productsData.succeeded)) {
      return (
        <ErrorAlert
          title="Error loading products"
          message={productsData?.message || 'Failed to load products'}
        />
      );
    }

    const products = productsData?.data || [];

    if (!products.length) {
      return (
        <Surface p="md">
          <Stack align="center">
            <IconMoodEmpty size={24} />
            <Title order={4}>No products found</Title>
            <Text>
              You don&apos;t have any products yet. Create one to get started.
            </Text>
            <Button
              leftSection={<IconPlus size={18} />}
              onClick={newProductOpen}
            >
              New Product
            </Button>
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
        {products.map((p) => (
          <ProductCard key={p.id} product={p} onEdit={handleEditProduct} />
        ))}
      </SimpleGrid>
    );
  };

  return (
    <>
      <>
        <title>Products | Kabul Sweets Admin</title>
        <meta name="description" content="Manage bakery products" />
      </>
      <PageHeader
        title="Products"
        breadcrumbItems={items}
        actionButton={
          productsData?.data?.length ? (
            <Button
              leftSection={<IconPlus size={18} />}
              onClick={newProductOpen}
            >
              New Product
            </Button>
          ) : undefined
        }
      />

      {renderContent()}

      <NewProductDrawer
        opened={newDrawerOpened}
        onClose={newProductClose}
        position="right"
        onProductCreated={handleProductCreated}
      />

      <EditProductDrawer
        opened={editDrawerOpened}
        onClose={editProductClose}
        position="right"
        product={selectedProduct}
        onProductUpdated={handleProductUpdated}
      />
    </>
  );
}

export default Products;
