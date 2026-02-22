'use client';

import { useEffect, useState } from 'react';

import {
  Badge,
  Button,
  Card,
  Divider,
  Drawer,
  DrawerProps,
  Group,
  List,
  LoadingOverlay,
  Stack,
  Textarea,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconCheck, IconX } from '@tabler/icons-react';

import { apiPost, useApiGet, useOrder } from '@/lib/hooks/useApi';
import type { OrderListItem } from '@/types/order';

interface EditOrderDrawerProps extends Omit<DrawerProps, 'title' | 'children'> {
  order: OrderListItem | null; // Changed to match parent
  onOrderUpdated?: () => void;
}

export const EditOrderDrawer = ({
  order: initialOrder,
  onOrderUpdated,
  ...drawerProps
}: EditOrderDrawerProps) => {
  const [loading, setLoading] = useState(false);
  const [decisionReason, setDecisionReason] = useState('');

  // Fetch full order details
  const { data: fullOrderData, refetch } = useOrder(initialOrder?.id || '');
  const orderDetails = fullOrderData?.data;

  // Fetch risk analysis
  const { data: riskData } = useApiGet<any>(
    initialOrder?.id ? `/api/orders/${initialOrder.id}/risk-analysis` : ''
  );

  const risk = riskData?.data;

  useEffect(() => {
    setDecisionReason('');
  }, [initialOrder?.id]);

  const handleApprove = async () => {
    if (!initialOrder?.id) return;
    setLoading(true);
    try {
      const res = await apiPost(`/api/orders/${initialOrder.id}/approve`, {});
      if (!res.succeeded) throw new Error(res.message);
      notifications.show({ title: 'Success', message: 'Order approved', color: 'green' });
      setDecisionReason('');
      onOrderUpdated?.();
      refetch();
      drawerProps.onClose?.();
    } catch (err: any) {
      notifications.show({ title: 'Error', message: err.message, color: 'red' });
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!initialOrder?.id) return;
    const trimmedReason = decisionReason.trim();
    if (trimmedReason.length < 3) {
      notifications.show({
        title: 'Reason required',
        message: 'Please provide a rejection reason (at least 3 characters).',
        color: 'red',
      });
      return;
    }

    setLoading(true);
    try {
      const res = await apiPost(`/api/orders/${initialOrder.id}/reject`, {
        reason: trimmedReason,
      });
      if (!res.succeeded) throw new Error(res.message);
      notifications.show({ title: 'Rejected', message: 'Order rejected', color: 'blue' });
      setDecisionReason('');
      onOrderUpdated?.();
      refetch();
      drawerProps.onClose?.();
    } catch (err: any) {
      notifications.show({ title: 'Error', message: err.message, color: 'red' });
    } finally {
      setLoading(false);
    }
  };

  const statusColorMap: Record<string, string> = {
    pending: 'yellow',
    pending_approval: 'orange',
    paid: 'teal',
    confirmed: 'blue',
    cancelled: 'red',
    completed: 'green',
    refunded: 'red',
    draft: 'gray',
    preparing: 'orange',
    ready: 'green',
  };

  return (
    <Drawer {...drawerProps} title="Order Details" size="xl" position="right">
      <LoadingOverlay visible={loading} />

      {orderDetails ? (
        <Stack gap="md">
          {/* Header info */}
          <Group justify="space-between">
            <div>
              <Title order={4}>Order #{orderDetails.order_number}</Title>
              <Text size="sm" c="dimmed">
                {new Date(orderDetails.created_at).toLocaleString()}
              </Text>
            </div>
            <Badge size="lg" color={statusColorMap[orderDetails.status] || 'gray'}>
              {orderDetails.status.replace('_', ' ').toUpperCase()}
            </Badge>
          </Group>

          {/* Approve / Reject Actions */}
          {(orderDetails.status === 'pending' || orderDetails.status === 'pending_approval') && (
            <Card withBorder radius="md" padding="md" bg="var(--mantine-color-orange-light)">
              <Stack gap="xs">
                <Group>
                  <ThemeIcon color="orange" variant="light"><IconAlertTriangle /></ThemeIcon>
                  <Text fw={600}>Action Required: Review Order</Text>
                </Group>
                <Text size="sm">
                  {orderDetails.status === 'pending'
                    ? 'This order is waiting for admin decision. You can approve directly or reject with a reason.'
                    : 'This order is authorized but payment is not captured. You can approve directly or reject with a reason.'}
                </Text>
                <Textarea
                  label="Rejection reason (required only for reject)"
                  placeholder="Add reason if you are rejecting this order..."
                  minRows={2}
                  autosize
                  value={decisionReason}
                  onChange={(event) => setDecisionReason(event.currentTarget.value)}
                />
                <Group grow>
                  <Button
                    color="green"
                    leftSection={<IconCheck size={16} />}
                    onClick={handleApprove}
                  >
                    {orderDetails.status === 'pending_approval' ? 'Approve & Capture' : 'Approve Order'}
                  </Button>
                  <Button
                    color="red"
                    variant="outline"
                    leftSection={<IconX size={16} />}
                    onClick={handleReject}
                    disabled={decisionReason.trim().length < 3}
                  >
                    Reject Order
                  </Button>
                </Group>
              </Stack>
            </Card>
          )}

          {/* Risk Analysis */}
          {risk && (
            <Card withBorder radius="md">
              <Title order={5} mb="sm">Risk Analysis (Pro)</Title>
              <Group mb="xs">
                <Badge
                  color={risk.risk_level === 'High' ? 'red' : risk.risk_level === 'Medium' ? 'yellow' : 'green'}
                  size="lg"
                >
                  Risk Level: {risk.risk_level} ({risk.risk_score}/100)
                </Badge>
              </Group>

              <List size="sm" spacing="xs" icon={<ThemeIcon color="red" size={16} radius="xl"><IconAlertTriangle size={10} /></ThemeIcon>}>
                {risk.risk_factors.map((factor: string, i: number) => (
                  <List.Item key={i}>{factor}</List.Item>
                ))}
              </List>
              {risk.risk_factors.length === 0 && <Text size="sm" c="green">No risk factors detected.</Text>}

              <Divider my="sm" />
              <Text size="sm"><b>Customer Stats:</b> {risk.customer_stats.order_count} orders, Total ${risk.customer_stats.total_spent}</Text>
            </Card>
          )}

          {/* Order Items */}
          <Card withBorder radius="md">
            <Title order={5} mb="md">Items</Title>
            <Stack gap="sm">
              {orderDetails.items.map((item) => (
                <Group key={item.id} justify="space-between" align="flex-start">
                  <div>
                    <Text fw={500}>{item.product_name} {item.variant_name ? `(${item.variant_name})` : ''}</Text>
                    <Text size="xs" c="dimmed">Qty: {item.quantity} x ${item.unit_price}</Text>
                    {item.cake_message && <Text size="xs" c="blue">Message: "{item.cake_message}"</Text>}
                  </div>
                  <Text fw={600}>${item.line_total}</Text>
                </Group>
              ))}
              <Divider />
              <Group justify="space-between">
                <Text fw={700}>Total</Text>
                <Text fw={700} size="lg">${orderDetails.total}</Text>
              </Group>
            </Stack>
          </Card>

          {/* Customer Info */}
          <Card withBorder radius="md">
            <Title order={5} mb="md">Customer</Title>
            <Stack gap="xs">
              <Text size="sm"><b>Name:</b> {orderDetails.customer_name}</Text>
              <Text size="sm"><b>Email:</b> {orderDetails.customer_email}</Text>
              <Text size="sm"><b>Phone:</b> {orderDetails.customer_phone || 'N/A'}</Text>
              <Text size="sm"><b>Pickup:</b> {orderDetails.pickup_date ? new Date(orderDetails.pickup_date).toLocaleDateString() : 'N/A'}</Text>
            </Stack>
          </Card>

        </Stack>
      ) : (
        <Title order={5}>Select an order to view details</Title>
      )}
    </Drawer>
  );
};
