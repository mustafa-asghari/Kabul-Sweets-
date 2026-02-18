'use client';

import { useState } from 'react';

import {
  Button,
  Divider,
  Drawer,
  DrawerProps,
  Group,
  LoadingOverlay,
  NumberInput,
  Select,
  Stack,
  Switch,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconTrash } from '@tabler/icons-react';

import { apiPost } from '@/lib/hooks/useApi';
import type { ProductCreate, VariantCreate } from '@/types/products';

const CATEGORY_OPTIONS = [
  { value: 'cake', label: 'Cake' },
  { value: 'pastry', label: 'Pastry' },
  { value: 'cookie', label: 'Cookie' },
  { value: 'bread', label: 'Bread' },
  { value: 'sweet', label: 'Sweet' },
  { value: 'drink', label: 'Drink' },
  { value: 'other', label: 'Other' },
];

type NewProductDrawerProps = Omit<DrawerProps, 'title' | 'children'> & {
  onProductCreated?: () => void;
};

export const NewProductDrawer = ({
  onProductCreated,
  ...drawerProps
}: NewProductDrawerProps) => {
  const [loading, setLoading] = useState(false);
  const [variants, setVariants] = useState<VariantCreate[]>([]);

  const form = useForm({
    mode: 'controlled',
    initialValues: {
      name: '',
      description: '',
      short_description: '',
      thumbnail: '',
      image_urls: '',
      category: 'cake',
      base_price: 0,
      is_cake: false,
      is_featured: false,
    },
    validate: {
      name: isNotEmpty('Product name cannot be empty'),
      category: isNotEmpty('Category is required'),
      base_price: (v) => (v <= 0 ? 'Price must be greater than 0' : null),
    },
  });

  const addVariant = () => {
    setVariants([
      ...variants,
      { name: '', price: 0, stock_quantity: 0, serves: undefined },
    ]);
  };

  const removeVariant = (index: number) => {
    setVariants(variants.filter((_, i) => i !== index));
  };

  const updateVariant = <K extends keyof VariantCreate>(
    index: number,
    field: K,
    value: VariantCreate[K]
  ) => {
    setVariants((prev) =>
      prev.map((variant, i) =>
        i === index ? { ...variant, [field]: value } : variant
      )
    );
  };

  const handleSubmit = async (values: typeof form.values) => {
    setLoading(true);
    try {
      const payload: ProductCreate = {
        name: values.name,
        description: values.description,
        short_description: values.short_description,
        thumbnail: values.thumbnail.trim() || undefined,
        images: values.image_urls
          .split(/[\n,]/)
          .map((url) => url.trim())
          .filter(Boolean),
        category: values.category as ProductCreate['category'],
        base_price: values.base_price,
        is_cake: values.is_cake,
        is_featured: values.is_featured,
        variants: variants.length > 0 ? variants : undefined,
      };

      const result = await apiPost('/api/products', payload);

      if (!result.succeeded) {
        throw new Error(result.message || 'Failed to create product');
      }

      notifications.show({
        title: 'Success',
        message: 'Product created successfully',
        color: 'green',
      });

      form.reset();
      setVariants([]);
      drawerProps.onClose?.();
      onProductCreated?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error ? error.message : 'Failed to create product',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Drawer {...drawerProps} title="Create a new product" size="lg">
      <LoadingOverlay visible={loading} />
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <TextInput
            label="Name"
            placeholder="Product name"
            {...form.getInputProps('name')}
            required
          />
          <Textarea
            label="Description"
            placeholder="Full product description"
            {...form.getInputProps('description')}
          />
          <TextInput
            label="Short Description"
            placeholder="Brief description (max 500 chars)"
            {...form.getInputProps('short_description')}
          />
          <TextInput
            label="Thumbnail URL"
            placeholder="https://..."
            {...form.getInputProps('thumbnail')}
          />
          <Textarea
            label="Image URLs"
            placeholder="One URL per line, or comma separated"
            minRows={2}
            autosize
            {...form.getInputProps('image_urls')}
          />
          <Select
            label="Category"
            data={CATEGORY_OPTIONS}
            {...form.getInputProps('category')}
            required
          />
          <NumberInput
            label="Base Price"
            placeholder="0.00"
            prefix="$"
            decimalScale={2}
            min={0}
            {...form.getInputProps('base_price')}
            required
          />
          <Group>
            <Switch
              label="Is a cake product"
              {...form.getInputProps('is_cake', { type: 'checkbox' })}
            />
            <Switch
              label="Featured"
              {...form.getInputProps('is_featured', { type: 'checkbox' })}
            />
          </Group>

          <Divider my="sm" />
          <Group justify="space-between">
            <Title order={5}>Variants</Title>
            <Button
              size="xs"
              variant="light"
              leftSection={<IconPlus size={14} />}
              onClick={addVariant}
            >
              Add Variant
            </Button>
          </Group>

          {variants.map((variant, index) => (
            <Stack key={index} gap="xs" p="sm" style={{ border: '1px solid var(--mantine-color-gray-3)', borderRadius: 8 }}>
              <Group justify="space-between">
                <Title order={6}>Variant {index + 1}</Title>
                <Button
                  size="xs"
                  variant="subtle"
                  color="red"
                  onClick={() => removeVariant(index)}
                  leftSection={<IconTrash size={14} />}
                >
                  Remove
                </Button>
              </Group>
              <TextInput
                label="Variant Name"
                placeholder="e.g., Small, Medium, Large"
                value={variant.name}
                onChange={(e) =>
                  updateVariant(index, 'name', e.currentTarget.value)
                }
                required
              />
              <Group grow>
                <NumberInput
                  label="Price"
                  prefix="$"
                  decimalScale={2}
                  min={0}
                  value={variant.price}
                  onChange={(v) =>
                    updateVariant(
                      index,
                      'price',
                      typeof v === 'number' ? v : Number(v) || 0
                    )
                  }
                />
                <NumberInput
                  label="Stock"
                  min={0}
                  value={variant.stock_quantity}
                  onChange={(v) =>
                    updateVariant(
                      index,
                      'stock_quantity',
                      typeof v === 'number' ? v : Number(v) || 0
                    )
                  }
                />
                <NumberInput
                  label="Serves"
                  min={1}
                  value={variant.serves || ''}
                  onChange={(v) =>
                    updateVariant(
                      index,
                      'serves',
                      typeof v === 'number' ? v : undefined
                    )
                  }
                />
              </Group>
            </Stack>
          ))}

          <Button type="submit" mt="md" loading={loading}>
            Create Product
          </Button>
        </Stack>
      </form>
    </Drawer>
  );
};

export default NewProductDrawer;
