'use client';

import { useState } from 'react';

import {
  Anchor,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconMoodEmpty, IconPackage } from '@tabler/icons-react';

import { ErrorAlert, PageHeader, Surface } from '@/components';
import { useInventoryTurnover, apiPost } from '@/lib/hooks/useApi';
import { PATH_DASHBOARD } from '@/routes';
import type { InventoryTurnover } from '@/types/analytics';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.ecommerce },
  { title: 'Store', href: '#' },
  { title: 'Inventory', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

function getStockStatus(stock: number, turnover: InventoryTurnover) {
  if (stock === 0) return { label: 'Out of Stock', color: 'red' };
  if (turnover.days_of_stock_remaining != null && turnover.days_of_stock_remaining < 7)
    return { label: 'Low Stock', color: 'orange' };
  return { label: 'In Stock', color: 'green' };
}

function Inventory() {
  const { data, loading, error, refetch } = useInventoryTurnover();
  const [stockOpened, { open: openStock, close: closeStock }] =
    useDisclosure(false);
  const [selectedItem, setSelectedItem] = useState<InventoryTurnover | null>(null);
  const [quantityChange, setQuantityChange] = useState(0);
  const [reason, setReason] = useState('restock');
  const [notes, setNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const handleStockAdjust = async () => {
    if (!selectedItem || quantityChange === 0) return;
    setActionLoading(true);
    try {
      const result = await apiPost(`/api/products/${selectedItem.product_id}/stock`, {
        variant_id: selectedItem.variant_id,
        quantity_change: quantityChange,
        reason,
        notes: notes || undefined,
      });
      if (!result.succeeded) throw new Error(result.message);
      notifications.show({
        title: 'Stock Updated',
        message: `Stock adjusted by ${quantityChange > 0 ? '+' : ''}${quantityChange}`,
        color: 'green',
      });
      closeStock();
      refetch();
    } catch (err) {
      notifications.show({
        title: 'Error',
        message: err instanceof Error ? err.message : 'Failed to adjust stock',
        color: 'red',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <Stack gap="sm">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} height={50} />
          ))}
        </Stack>
      );
    }

    if (error || (data && !data.succeeded)) {
      return <ErrorAlert title="Error loading inventory" message={data?.message} />;
    }

    const inventory = data?.data || [];

    if (!inventory.length) {
      return (
        <Surface p="md">
          <Stack align="center">
            <IconMoodEmpty size={24} />
            <Title order={4}>No inventory data</Title>
            <Text>No products with variants found.</Text>
          </Stack>
        </Surface>
      );
    }

    return (
      <Surface>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Product</Table.Th>
              <Table.Th>Variant</Table.Th>
              <Table.Th>Current Stock</Table.Th>
              <Table.Th>Sold (30d)</Table.Th>
              <Table.Th>Turnover Rate</Table.Th>
              <Table.Th>Days Remaining</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {inventory.map((item, idx) => {
              const status = getStockStatus(item.current_stock, item);
              return (
                <Table.Tr key={idx}>
                  <Table.Td fw={500}>{item.product_name}</Table.Td>
                  <Table.Td>{item.variant_name}</Table.Td>
                  <Table.Td fw={600}>{item.current_stock}</Table.Td>
                  <Table.Td>{item.total_sold_30d}</Table.Td>
                  <Table.Td>{item.turnover_rate.toFixed(2)}</Table.Td>
                  <Table.Td>
                    {item.days_of_stock_remaining != null
                      ? Math.round(item.days_of_stock_remaining)
                      : '-'}
                  </Table.Td>
                  <Table.Td>
                    <Badge color={status.color} variant="filled" radius="sm" size="sm">
                      {status.label}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<IconPackage size={14} />}
                      onClick={() => {
                        setSelectedItem(item);
                        setQuantityChange(0);
                        setReason('restock');
                        setNotes('');
                        openStock();
                      }}
                    >
                      Adjust
                    </Button>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Surface>
    );
  };

  return (
    <>
      <>
        <title>Inventory | Kabul Sweets Admin</title>
        <meta name="description" content="Manage inventory and stock levels" />
      </>
      <PageHeader title="Inventory Management" breadcrumbItems={items} />

      {renderContent()}

      <Modal opened={stockOpened} onClose={closeStock} title="Stock Adjustment">
        <Stack>
          {selectedItem && (
            <Text>
              Adjusting stock for{' '}
              <strong>{selectedItem.product_name} - {selectedItem.variant_name}</strong>
              <br />
              Current stock: <strong>{selectedItem.current_stock}</strong>
            </Text>
          )}
          <NumberInput
            label="Quantity Change"
            description="Positive = restock, Negative = remove"
            value={quantityChange}
            onChange={(v) => setQuantityChange(Number(v))}
            required
          />
          <TextInput
            label="Reason"
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            required
          />
          <Textarea
            label="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />
          <Button
            onClick={handleStockAdjust}
            loading={actionLoading}
            disabled={quantityChange === 0}
          >
            Adjust Stock
          </Button>
        </Stack>
      </Modal>
    </>
  );
}

export default Inventory;
