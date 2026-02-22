'use client';

import { useCallback, useState } from 'react';

import {
  Anchor,
  Button,
  Group,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconMoodEmpty, IconPlus } from '@tabler/icons-react';

import { ErrorAlert, OrdersTable, PageHeader, Surface } from '@/components';
import type { OrderListItem } from '@/types';
import { useOrders } from '@/lib/hooks/useApi';
import { PATH_DASHBOARD } from '@/routes';

import { EditOrderDrawer } from './components/EditOrderDrawer';
import { NewOrderDrawer } from './components/NewOrderDrawer';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.ecommerce },
  { title: 'Store', href: '#' },
  { title: 'Orders', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

function Orders() {
  const [selectedOrder, setSelectedOrder] = useState<OrderListItem | null>(null);

  const {
    data: ordersData,
    loading: ordersLoading,
    error: ordersError,
    refetch: refetchOrders,
  } = useOrders();

  const [newDrawerOpened, { open: newOrderOpen, close: newOrderClose }] =
    useDisclosure(false);

  const [editDrawerOpened, { open: editOrderOpen, close: editOrderClose }] =
    useDisclosure(false);

  const handleOrderCreated = useCallback(() => {
    refetchOrders();
  }, [refetchOrders]);

  const handleOrderUpdated = useCallback(() => {
    refetchOrders();
  }, [refetchOrders]);

  const handleEditOrder = (order: OrderListItem) => {
    setSelectedOrder(order);
    editOrderOpen();
  };

  const handleViewOrder = (order: OrderListItem) => {
    setSelectedOrder(order);
    editOrderOpen();
  };

  const handleApproveOrder = (order: OrderListItem) => {
    setSelectedOrder(order);
    editOrderOpen();
  };

  const handleRejectOrder = (order: OrderListItem) => {
    setSelectedOrder(order);
    editOrderOpen();
  };

  const renderContent = () => {
    if (ordersLoading) {
      return (
        <Surface>
          <Stack gap="sm" p="md">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={`order-loading-${i}`} visible={true} height={40} />
            ))}
          </Stack>
        </Surface>
      );
    }

    if (ordersError) {
      return (
        <ErrorAlert
          title="Error loading orders"
          message={ordersError?.message || 'Failed to load orders'}
        />
      );
    }

    if (!ordersData?.data?.length) {
      return (
        <Surface p="md">
          <Stack align="center">
            <IconMoodEmpty size={24} />
            <Title order={4}>No orders found</Title>
            <Text>
              You don&apos;t have any orders yet. Create one to get started.
            </Text>
            <Button leftSection={<IconPlus size={18} />} onClick={newOrderOpen}>
              New Order
            </Button>
          </Stack>
        </Surface>
      );
    }

    return (
      <Surface>
        <OrdersTable
          data={ordersData.data}
          loading={false}
          onEdit={handleEditOrder}
          onView={handleViewOrder}
          onApprove={handleApproveOrder}
          onReject={handleRejectOrder}
        />
      </Surface>
    );
  };

  return (
    <>
      <>
        <title>Orders | Kabul Sweets Admin</title>
        <meta name="description" content="Manage bakery orders" />
      </>
      <PageHeader
        title="Orders"
        breadcrumbItems={items}
        actionButton={
          ordersData?.data && ordersData.data?.length > 0 ? (
            <Button leftSection={<IconPlus size={18} />} onClick={newOrderOpen}>
              New Order
            </Button>
          ) : undefined
        }
      />

      {renderContent()}

      <NewOrderDrawer
        opened={newDrawerOpened}
        onClose={newOrderClose}
        position="right"
        onOrderCreated={handleOrderCreated}
      />

      <EditOrderDrawer
        opened={editDrawerOpened}
        onClose={editOrderClose}
        position="right"
        order={selectedOrder}
        onOrderUpdated={handleOrderUpdated}
      />
    </>
  );
}

export default Orders;
