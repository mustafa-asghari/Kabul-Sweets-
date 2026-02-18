'use client';

import { useState } from 'react';

import {
  Button,
  Drawer,
  DrawerProps,
  Group,
  LoadingOverlay,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core';
import { isEmail, isNotEmpty, useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconTrash } from '@tabler/icons-react';

import { apiPost } from '@/lib/hooks/useApi';
import type { Order, OrderCreate } from '@/types/order';

interface OrderItemForm {
  product_id: string;
  variant_id: string;
  quantity: number;
  cake_message: string;
}

interface NewOrderFormValues {
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  pickup_date: string;
  pickup_time_slot: string;
  special_instructions: string;
  discount_code: string;
  items: OrderItemForm[];
}

type NewOrderDrawerProps = Omit<DrawerProps, 'title' | 'children'> & {
  onOrderCreated?: () => void;
};

export const NewOrderDrawer = ({
  onOrderCreated,
  ...drawerProps
}: NewOrderDrawerProps) => {
  const [loading, setLoading] = useState(false);

  const form = useForm<NewOrderFormValues>({
    mode: 'controlled',
    initialValues: {
      customer_name: '',
      customer_email: '',
      customer_phone: '',
      pickup_date: '',
      pickup_time_slot: '',
      special_instructions: '',
      discount_code: '',
      items: [{ product_id: '', variant_id: '', quantity: 1, cake_message: '' }],
    },
    validate: {
      customer_name: isNotEmpty('Customer name is required'),
      customer_email: isEmail('Invalid email'),
      items: {
        product_id: isNotEmpty('Product ID is required'),
        quantity: (value) => (value > 0 ? null : 'Quantity must be at least 1'),
      },
    },
  });

  const handleSubmit = async (values: NewOrderFormValues) => {
    setLoading(true);
    try {
      const payload: OrderCreate = {
        customer_name: values.customer_name,
        customer_email: values.customer_email,
        customer_phone: values.customer_phone || undefined,
        pickup_date: values.pickup_date || undefined,
        pickup_time_slot: values.pickup_time_slot || undefined,
        special_instructions: values.special_instructions || undefined,
        discount_code: values.discount_code || undefined,
        items: values.items
          .filter((item) => item.product_id)
          .map((item) => ({
            product_id: item.product_id,
            variant_id: item.variant_id || undefined,
            quantity: item.quantity,
            cake_message: item.cake_message || undefined,
          })),
      };

      const result = await apiPost<Order>('/api/orders', payload);

      if (!result.succeeded) {
        throw new Error(result.message || 'Failed to create order');
      }

      notifications.show({
        title: 'Order Created',
        message: `Order for ${values.customer_name} created successfully.`,
        color: 'green',
      });

      form.reset();
      drawerProps.onClose?.();
      onOrderCreated?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error ? error.message : 'Failed to create order',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const addItem = () => {
    form.insertListItem('items', {
      product_id: '',
      variant_id: '',
      quantity: 1,
      cake_message: '',
    });
  };

  const removeItem = (index: number) => {
    form.removeListItem('items', index);
  };

  return (
    <Drawer {...drawerProps} title="Create New Order" size="lg">
      <LoadingOverlay visible={loading} />
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <Title order={4}>Customer Information</Title>
          <TextInput
            label="Customer Name"
            placeholder="Enter customer name"
            key={form.key('customer_name')}
            {...form.getInputProps('customer_name')}
            required
          />
          <TextInput
            label="Customer Email"
            placeholder="customer@example.com"
            key={form.key('customer_email')}
            {...form.getInputProps('customer_email')}
            required
          />
          <TextInput
            label="Customer Phone"
            placeholder="+61 400 000 000"
            key={form.key('customer_phone')}
            {...form.getInputProps('customer_phone')}
          />

          <Title order={4} mt="md">Order Items</Title>
          {form.values.items.map((_, index) => (
            <Group key={index} align="flex-end" gap="xs">
              <TextInput
                label="Product ID"
                placeholder="UUID"
                style={{ flex: 2 }}
                key={form.key(`items.${index}.product_id`)}
                {...form.getInputProps(`items.${index}.product_id`)}
                required
              />
              <TextInput
                label="Variant ID"
                placeholder="UUID (optional)"
                style={{ flex: 2 }}
                key={form.key(`items.${index}.variant_id`)}
                {...form.getInputProps(`items.${index}.variant_id`)}
              />
              <NumberInput
                label="Qty"
                min={1}
                style={{ flex: 1 }}
                key={form.key(`items.${index}.quantity`)}
                {...form.getInputProps(`items.${index}.quantity`)}
                required
              />
              {form.values.items.length > 1 && (
                <Button
                  color="red"
                  variant="subtle"
                  size="sm"
                  onClick={() => removeItem(index)}
                >
                  <IconTrash size={16} />
                </Button>
              )}
            </Group>
          ))}
          <Button
            variant="light"
            leftSection={<IconPlus size={16} />}
            onClick={addItem}
            size="sm"
          >
            Add Item
          </Button>

          <Title order={4} mt="md">Pickup Details</Title>
          <TextInput
            label="Pickup Date"
            type="date"
            key={form.key('pickup_date')}
            {...form.getInputProps('pickup_date')}
          />
          <Select
            label="Pickup Time Slot"
            data={[
              { value: 'morning', label: 'Morning (9am-12pm)' },
              { value: 'afternoon', label: 'Afternoon (12pm-3pm)' },
              { value: 'evening', label: 'Evening (3pm-6pm)' },
            ]}
            key={form.key('pickup_time_slot')}
            {...form.getInputProps('pickup_time_slot')}
            clearable
          />
          <Textarea
            label="Special Instructions"
            placeholder="Any special requests..."
            key={form.key('special_instructions')}
            {...form.getInputProps('special_instructions')}
          />
          <TextInput
            label="Discount Code"
            placeholder="Enter discount code (optional)"
            key={form.key('discount_code')}
            {...form.getInputProps('discount_code')}
          />

          <Button type="submit" mt="md" loading={loading}>
            Create Order
          </Button>
        </Stack>
      </form>
    </Drawer>
  );
};
