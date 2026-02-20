'use client';

import { useEffect, useRef, useState } from 'react';

import {
  Button,
  Divider,
  Drawer,
  DrawerProps,
  FileButton,
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
import { IconPlus, IconTrash, IconUpload } from '@tabler/icons-react';

import { apiPatch, apiDelete, apiPost, apiPostFormData, useApiGet } from '@/lib/hooks/useApi';
import type { ProductListItem, Product, ProductVariant } from '@/types/products';

const CATEGORY_OPTIONS = [
  { value: 'cake', label: 'Cake' },
  { value: 'pastry', label: 'Pastry' },
  { value: 'cookie', label: 'Cookie' },
  { value: 'bread', label: 'Bread' },
  { value: 'sweet', label: 'Sweet' },
  { value: 'drink', label: 'Drink' },
  { value: 'other', label: 'Other' },
];

type EditProductDrawerProps = Omit<DrawerProps, 'title' | 'children'> & {
  product: ProductListItem | null;
  onProductUpdated?: () => void;
};

interface EditableVariant {
  id?: string;
  name: string;
  price: number;
  stock_quantity: number;
  low_stock_threshold: number;
  serves: number | null;
  is_active: boolean;
}

function toEditableVariant(variant: ProductVariant): EditableVariant {
  return {
    id: variant.id,
    name: variant.name,
    price: Number(variant.price) || 0,
    stock_quantity: variant.stock_quantity ?? 0,
    low_stock_threshold: variant.low_stock_threshold ?? 5,
    serves: variant.serves ?? null,
    is_active: variant.is_active ?? true,
  };
}

export const EditProductDrawer = ({
  product,
  onProductUpdated,
  ...drawerProps
}: EditProductDrawerProps) => {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [variants, setVariants] = useState<EditableVariant[]>([]);
  const [deletedVariantIds, setDeletedVariantIds] = useState<string[]>([]);

  // Fetch full product details (includes description)
  const { data: fullProductData } = useApiGet<Product>(
    product?.id ? `/api/products/${product.id}` : ''
  );
  const fullProduct = fullProductData?.data;

  // Track which product ID we have already initialised the form for.
  // This prevents fullProduct's async arrival (or any later re-fetch) from
  // clobbering field values the user has already edited (e.g. a newly
  // uploaded thumbnail URL).
  const initialisedForRef = useRef<string | null>(null);

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
      is_active: true,
    },
    validate: {
      name: isNotEmpty('Product name cannot be empty'),
      category: isNotEmpty('Category is required'),
      base_price: (v) => (v <= 0 ? 'Price must be greater than 0' : null),
    },
  });

  useEffect(() => {
    // Reset so the next product open re-initialises the form.
    if (!product) {
      initialisedForRef.current = null;
      return;
    }

    // Wait until we have the full product data before populating.
    // Only do this ONCE per product (identified by its id) so that
    // subsequent re-fetches of fullProduct don't overwrite user edits.
    if (initialisedForRef.current === product.id) return;
    if (!fullProduct) return;

    initialisedForRef.current = product.id;

    form.setValues({
      name: product.name || '',
      description: fullProduct.description || '',
      short_description: product.short_description || '',
      thumbnail: fullProduct.thumbnail || '',
      image_urls: (fullProduct.images || []).join('\n'),
      category: product.category || 'other',
      base_price: Number(product.base_price) || 0,
      is_cake: product.is_cake || false,
      is_featured: product.is_featured || false,
      is_active: product.is_active ?? true,
    });

    setVariants((fullProduct.variants ?? product.variants ?? []).map(toEditableVariant));
    setDeletedVariantIds([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product, fullProduct]);

  const addVariant = () => {
    setVariants((current) => [
      ...current,
      {
        name: '',
        price: 0,
        stock_quantity: 0,
        low_stock_threshold: 5,
        serves: null,
        is_active: true,
      },
    ]);
  };

  const removeVariant = (index: number) => {
    setVariants((current) => {
      const target = current[index];
      if (target?.id) {
        setDeletedVariantIds((deleted) => [...deleted, target.id as string]);
      }
      return current.filter((_, i) => i !== index);
    });
  };

  const updateVariant = <K extends keyof EditableVariant>(
    index: number,
    field: K,
    value: EditableVariant[K]
  ) => {
    setVariants((current) =>
      current.map((variant, i) =>
        i === index ? { ...variant, [field]: value } : variant
      )
    );
  };

  const handleSubmit = async (values: typeof form.values) => {
    if (!product) return;

    const invalidVariant = variants.find(
      (variant) => !variant.name.trim() || variant.price < 0 || variant.stock_quantity < 0
    );
    if (invalidVariant) {
      notifications.show({
        title: 'Invalid variant data',
        message: 'Each variant needs a name and non-negative price/stock.',
        color: 'red',
      });
      return;
    }

    setLoading(true);
    try {
      const productPayload = {
        name: values.name,
        description: values.description,
        short_description: values.short_description,
        thumbnail: values.thumbnail.trim() || null,
        images: values.image_urls
          .split(/[\n,]/)
          .map((url) => url.trim())
          .filter(Boolean),
        category: values.category,
        base_price: values.base_price,
        is_cake: values.is_cake,
        is_featured: values.is_featured,
        is_active: values.is_active,
      };
      const result = await apiPatch(`/api/products/${product.id}`, productPayload);

      if (!result.succeeded) {
        throw new Error(result.message || 'Failed to update product');
      }

      for (const variantId of deletedVariantIds) {
        const deleteResult = await apiDelete(`/api/products/variants/${variantId}`);
        if (!deleteResult.succeeded) {
          throw new Error(deleteResult.message || 'Failed to delete product variant');
        }
      }

      for (const variant of variants) {
        const variantPayload = {
          name: variant.name,
          price: variant.price,
          stock_quantity: variant.stock_quantity,
          low_stock_threshold: variant.low_stock_threshold,
          serves: variant.serves ?? undefined,
          is_active: variant.is_active,
        };

        if (variant.id) {
          const updateResult = await apiPatch(
            `/api/products/variants/${variant.id}`,
            variantPayload
          );
          if (!updateResult.succeeded) {
            throw new Error(updateResult.message || 'Failed to update product variant');
          }
        } else {
          const createResult = await apiPost(
            `/api/products/${product.id}/variants`,
            variantPayload
          );
          if (!createResult.succeeded) {
            throw new Error(createResult.message || 'Failed to create product variant');
          }
        }
      }

      notifications.show({
        title: 'Success',
        message: 'Product and variants updated successfully',
        color: 'green',
      });

      drawerProps.onClose?.();
      onProductUpdated?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error ? error.message : 'Failed to update product',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!product) return;
    if (!window.confirm('Are you sure you want to delete this product?')) return;

    setLoading(true);
    try {
      const result = await apiDelete(`/api/products/${product.id}`);

      if (!result.succeeded) {
        throw new Error(result.message || 'Failed to delete product');
      }

      notifications.show({
        title: 'Success',
        message: 'Product deleted successfully',
        color: 'green',
      });

      drawerProps.onClose?.();
      onProductUpdated?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error ? error.message : 'Failed to delete product',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Drawer {...drawerProps} title="Edit product" size="lg">
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
            placeholder="Brief description"
            {...form.getInputProps('short_description')}
          />
          <Stack gap="xs">
            <TextInput
              label="Thumbnail URL"
              placeholder="https://… or upload below"
              {...form.getInputProps('thumbnail')}
            />
            <FileButton
              onChange={async (files) => {
                const file = Array.isArray(files) ? files[0] : files;
                if (!file) return;

                setUploading(true);
                const formData = new FormData();
                formData.append('file', file);

                try {
                  const res = await apiPostFormData<{ image_id: string }>(
                    '/api/images',
                    formData
                  );

                  if (res.data?.image_id) {
                    const url = `/api/v1/images/${res.data.image_id}/serve`;
                    form.setFieldValue('thumbnail', url);
                    const current = form.values.image_urls.trim();
                    form.setFieldValue(
                      'image_urls',
                      current ? `${current}\n${url}` : url
                    );
                    notifications.show({
                      title: 'Image uploaded',
                      message: 'Thumbnail updated successfully.',
                      color: 'green',
                    });
                  } else {
                    throw new Error('Upload failed');
                  }
                } catch {
                  notifications.show({
                    title: 'Upload failed',
                    message: 'Could not upload image. Please try again.',
                    color: 'red',
                  });
                } finally {
                  setUploading(false);
                }
              }}
              accept="image/png,image/jpeg,image/webp"
            >
              {(props) => (
                <Button
                  {...props}
                  variant="light"
                  size="xs"
                  loading={uploading}
                  leftSection={!uploading && <IconUpload size={14} />}
                >
                  Upload Thumbnail
                </Button>
              )}
            </FileButton>
          </Stack>
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
            prefix="$"
            decimalScale={2}
            min={0}
            {...form.getInputProps('base_price')}
            required
          />
          <Group>
            <Switch
              label="Active"
              {...form.getInputProps('is_active', { type: 'checkbox' })}
            />
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
            <Title order={5}>Variants ({variants.length})</Title>
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
            <Stack
              key={variant.id || `new-${index}`}
              gap="xs"
              p="sm"
              style={{ border: '1px solid var(--mantine-color-gray-3)', borderRadius: 8 }}
            >
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
                onChange={(event) =>
                  updateVariant(index, 'name', event.currentTarget.value)
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
                  onChange={(value) =>
                    updateVariant(
                      index,
                      'price',
                      typeof value === 'number' ? value : Number(value) || 0
                    )
                  }
                />
                <NumberInput
                  label="Stock"
                  min={0}
                  value={variant.stock_quantity}
                  onChange={(value) =>
                    updateVariant(
                      index,
                      'stock_quantity',
                      typeof value === 'number' ? value : Number(value) || 0
                    )
                  }
                />
                <NumberInput
                  label="Low stock threshold"
                  min={0}
                  value={variant.low_stock_threshold}
                  onChange={(value) =>
                    updateVariant(
                      index,
                      'low_stock_threshold',
                      typeof value === 'number' ? value : Number(value) || 0
                    )
                  }
                />
                <NumberInput
                  label="Serves"
                  min={1}
                  value={variant.serves || ''}
                  onChange={(value) =>
                    updateVariant(
                      index,
                      'serves',
                      typeof value === 'number' ? value : null
                    )
                  }
                />
              </Group>
              <Switch
                label="Variant active"
                checked={variant.is_active}
                onChange={(event) =>
                  updateVariant(index, 'is_active', event.currentTarget.checked)
                }
              />
            </Stack>
          ))}

          <Group justify="space-between" mt="xl">
            <Button color="red" variant="outline" onClick={handleDelete}>
              Delete Product
            </Button>
            <Button type="submit" loading={loading}>
              Update Product
            </Button>
          </Group>
        </Stack>
      </form>
    </Drawer>
  );
};

export default EditProductDrawer;
