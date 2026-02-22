'use client';

import { useEffect, useRef, useState } from 'react';

import {
  Anchor,
  Badge,
  Button,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
  Modal,
  Image,
} from '@mantine/core';
import { Dropzone, IMAGE_MIME_TYPE } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import {
  IconDatabase,
  IconMoodEmpty,
  IconPhoto,
  IconTrash,
  IconUpload,
  IconX,
  IconEye,
  IconPlus,
} from '@tabler/icons-react';

import {
  AuthenticatedImage,
  ErrorAlert,
  PageHeader,
  Surface,
} from '@/components';
import { NewProductDrawer } from '../products/components/NewProductDrawer';
import { useApiGet, apiPost } from '@/lib/hooks/useApi';
import { PATH_DASHBOARD } from '@/routes';

const PROCESSING_STATUSES = new Set(['processing', 'reprocessing']);

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.ecommerce },
  { title: 'Media', href: '#' },
  { title: 'Image Processing', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

function Images() {
  const { data, loading, error, refetch } = useApiGet<any[]>('/api/images');
  const [uploading, setUploading] = useState(false);
  const [migrating, setMigrating] = useState(false);
  const [migratingS3, setMigratingS3] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [createProductUrl, setCreateProductUrl] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Poll every 4 seconds while any image is still processing
  useEffect(() => {
    const images: any[] = data?.data || [];
    const hasProcessing = images.some((img: any) =>
      PROCESSING_STATUSES.has(img.status),
    );

    if (hasProcessing) {
      pollRef.current = setTimeout(() => refetch(), 4000);
    }

    return () => {
      if (pollRef.current) {
        clearTimeout(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [data, refetch]);

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('/api/images', {
          method: 'POST',
          body: formData,
        });
        const result = await res.json();

        if (!result.succeeded) {
          throw new Error(result.message || `Failed to upload ${file.name}`);
        }
      }

      notifications.show({
        title: 'Upload Complete',
        message: `${files.length} image(s) uploaded successfully`,
        color: 'green',
      });
      refetch();
    } catch (err) {
      notifications.show({
        title: 'Upload Error',
        message: err instanceof Error ? err.message : 'Upload failed',
        color: 'red',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleMigrateUrls = async () => {
    if (!window.confirm('Rewrite all /original product thumbnail URLs to /serve in the database?\n\nSafe to run multiple times.')) return;
    setMigrating(true);
    try {
      const res = await fetch('/api/images/migrate-urls', { method: 'POST', credentials: 'include' });
      const result = await res.json();
      notifications.show({
        title: 'URL migration complete',
        message: `${result.data?.thumbnails_updated ?? 0} thumbnail(s) updated.`,
        color: 'green',
      });
    } catch (err) {
      notifications.show({ title: 'Failed', message: err instanceof Error ? err.message : 'Error', color: 'red' });
    } finally { setMigrating(false); }
  };

  const handleMigrateBase64ToS3 = async () => {
    if (!window.confirm('Upload all base64 DB images to S3?\n\nThis fixes Gemini results saving to DB. May take a while.')) return;
    setMigratingS3(true);
    try {
      const res = await fetch('/api/images/migrate-base64-to-s3', { method: 'POST', credentials: 'include' });
      const result = await res.json();
      notifications.show({
        title: 'S3 migration complete',
        message: `${result.data?.images_migrated ?? 0} image(s) moved to S3. ${result.data?.errors ?? 0} error(s).`,
        color: result.data?.errors > 0 ? 'yellow' : 'green',
      });
    } catch (err) {
      notifications.show({ title: 'Failed', message: err instanceof Error ? err.message : 'Error', color: 'red' });
    } finally { setMigratingS3(false); }
  };

  const handleProcess = async (imageId: string, category: string) => {
    try {
      const result = await apiPost(`/api/images/${imageId}`, {
        action: 'process',
        category,
      });
      if (!result.succeeded) throw new Error(result.message);
      notifications.show({
        title: 'Processing',
        message: 'Image processing started',
        color: 'blue',
      });
      refetch();
    } catch (err) {
      notifications.show({
        title: 'Error',
        message: err instanceof Error ? err.message : 'Failed to process',
        color: 'red',
      });
    }
  };

  const handleChoose = async (
    imageId: string,
    choice: 'original' | 'processed',
  ) => {
    try {
      const result = await apiPost(`/api/images/${imageId}`, {
        action: 'choose',
        choice,
      });
      if (!result.succeeded) throw new Error(result.message);
      notifications.show({
        title: 'Selected',
        message: `${choice} image selected`,
        color: 'green',
      });
      refetch();
    } catch (err) {
      notifications.show({
        title: 'Error',
        message: err instanceof Error ? err.message : 'Failed to select',
        color: 'red',
      });
    }
  };

  const handleDelete = async (imageId: string) => {
    if (!window.confirm('Delete this image? This removes it from S3 and the database permanently.')) return;
    try {
      const res = await fetch(`/api/images/${imageId}`, { method: 'DELETE', credentials: 'include' });
      const result = await res.json();
      if (result.succeeded === false) throw new Error(result.message);
      notifications.show({ title: 'Deleted', message: 'Image deleted successfully', color: 'red' });
      refetch();
    } catch (err) {
      notifications.show({
        title: 'Delete failed',
        message: err instanceof Error ? err.message : 'Unknown error',
        color: 'red',
      });
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <Stack gap="sm">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} height={200} />
          ))}
        </Stack>
      );
    }

    if (error || (data && !data.succeeded)) {
      return (
        <ErrorAlert title="Error loading images" message={data?.message} />
      );
    }

    const images = data?.data || [];

    if (!images.length) {
      return (
        <Surface p="md">
          <Stack align="center">
            <IconMoodEmpty size={24} />
            <Title order={4}>No images</Title>
            <Text>Upload images to get started with AI processing.</Text>
          </Stack>
        </Surface>
      );
    }

    return (
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3, xl: 4 }} spacing="md">
        {images.map((img: any) => (
          <Surface key={img.id} p="sm">
            <Stack>
              {/* Image Preview */}
              <div
                style={{
                  position: 'relative',
                  aspectRatio: '1/1',
                  overflow: 'hidden',
                  borderRadius: '8px',
                }}
              >
                <div style={{ height: 200, position: 'relative' }}>
                  <AuthenticatedImage
                    src={
                      img.status === 'completed'
                        ? `/api/images/${img.id}/processed`
                        : `/api/images/${img.id}/original`
                    }
                    alt="Product"
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                    }}
                  />
                  {img.status === 'completed' && (
                    <Badge
                      color="green"
                      variant="filled"
                      pos="absolute"
                      top={10}
                      right={10}
                    >
                      Processed
                    </Badge>
                  )}
                  {PROCESSING_STATUSES.has(img.status) && (
                    <Badge
                      color="blue"
                      variant="filled"
                      pos="absolute"
                      top={10}
                      right={10}
                    >
                      Processing
                    </Badge>
                  )}
                  {img.status === 'failed' && (
                    <Badge
                      color="red"
                      variant="filled"
                      pos="absolute"
                      top={10}
                      right={10}
                    >
                      Failed
                    </Badge>
                  )}
                  {img.admin_chosen && (
                    <Badge
                      color="yellow"
                      variant="filled"
                      pos="absolute"
                      top={10}
                      left={10}
                    >
                      Chosen: {img.admin_chosen}
                    </Badge>
                  )}
                </div>
              </div>

              <Text size="sm" lineClamp={1}>
                ID: {img.id?.slice(0, 8)}
              </Text>
              <Text size="xs" c="dimmed">
                Product: {img.product_id?.slice(0, 8) || 'None'}
              </Text>

              {/* Public thumbnail URL to copy into the product form */}
              <div>
                <Text size="xs" c="dimmed" mb={4}>
                  Thumbnail URL (paste into product form):
                </Text>
                <Group gap={4} wrap="nowrap">
                  <Text
                    size="xs"
                    ff="monospace"
                    style={{
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      background: 'var(--mantine-color-gray-1)',
                      padding: '2px 6px',
                      borderRadius: 4,
                    }}
                  >
                    {img.admin_chosen
                      ? `/api/v1/images/${img.id}/selected/public`
                      : `/api/v1/images/${img.id}/serve`}
                  </Text>
                  <Button
                    size="xs"
                    variant="subtle"
                    onClick={() =>
                      navigator.clipboard.writeText(
                        img.admin_chosen
                          ? `/api/v1/images/${img.id}/selected/public`
                          : `/api/v1/images/${img.id}/serve`
                      )
                    }
                  >
                    Copy
                  </Button>
                </Group>
              </div>

              {/* Actions */}
              <Group grow>
                <Button
                  size="xs"
                  variant="light"
                  color="blue"
                  leftSection={<IconEye size={12} />}
                  onClick={() => setPreviewUrl(img.admin_chosen
                    ? `/api/v1/images/${img.id}/selected/public`
                    : `/api/v1/images/${img.id}/serve`)}
                >
                  Preview
                </Button>
                <Button
                  size="xs"
                  variant="light"
                  color="violet"
                  leftSection={<IconPlus size={12} />}
                  onClick={() => setCreateProductUrl(img.admin_chosen
                    ? `/api/v1/images/${img.id}/selected/public`
                    : `/api/v1/images/${img.id}/serve`)}
                >
                  Add Product
                </Button>
              </Group>

              <Group grow>
                <Button
                  size="xs"
                  variant="light"
                  disabled={
                    PROCESSING_STATUSES.has(img.status) ||
                    img.status === 'completed'
                  }
                  onClick={() => handleProcess(img.id, 'cake')}
                >
                  AI Process
                </Button>
                <Button
                  size="xs"
                  variant="light"
                  color="red"
                  leftSection={<IconTrash size={12} />}
                  onClick={() => handleDelete(img.id)}
                >
                  Delete
                </Button>
              </Group>

              {img.status === 'completed' && (
                <Group grow>
                  <Button
                    size="xs"
                    color="green"
                    variant={
                      img.admin_chosen === 'processed' ? 'filled' : 'light'
                    }
                    onClick={() => handleChoose(img.id, 'processed')}
                  >
                    Pick Processed
                  </Button>
                  <Button
                    size="xs"
                    color="gray"
                    variant={
                      img.admin_chosen === 'original' ? 'filled' : 'light'
                    }
                    onClick={() => handleChoose(img.id, 'original')}
                  >
                    Pick Original
                  </Button>
                </Group>
              )}
            </Stack>
          </Surface>
        ))}
      </SimpleGrid>
    );
  };

  return (
    <>
      <>
        <title>Images | Kabul Sweets Admin</title>
        <meta
          name="description"
          content="Manage product images with AI processing"
        />
      </>
      <PageHeader
        title="Image Processing"
        breadcrumbItems={items}
        actionButton={
          <Group gap="xs">
            <Button size="xs" variant="light" color="violet"
              leftSection={<IconDatabase size={14} />}
              loading={migratingS3} onClick={handleMigrateBase64ToS3}>
              Upload DB Images to S3
            </Button>
            <Button size="xs" variant="light" color="orange"
              leftSection={<IconDatabase size={14} />}
              loading={migrating} onClick={handleMigrateUrls}>
              Fix Legacy URLs
            </Button>
          </Group>
        }
      />

      <Surface p="md" mb="md">
        <Dropzone
          onDrop={handleUpload}
          accept={IMAGE_MIME_TYPE}
          loading={uploading}
          maxSize={10 * 1024 * 1024}
        >
          <Group
            justify="center"
            gap="xl"
            mih={100}
            style={{ pointerEvents: 'none' }}
          >
            <Dropzone.Accept>
              <IconUpload size={40} stroke={1.5} />
            </Dropzone.Accept>
            <Dropzone.Reject>
              <IconX size={40} stroke={1.5} />
            </Dropzone.Reject>
            <Dropzone.Idle>
              <IconPhoto size={40} stroke={1.5} />
            </Dropzone.Idle>
            <div>
              <Text size="lg" inline>
                Drag images here or click to select
              </Text>
              <Text size="sm" c="dimmed" inline mt={7}>
                Max file size: 10MB. Supported: JPEG, PNG, WebP, GIF
              </Text>
            </div>
          </Group>
        </Dropzone>
      </Surface>

      {renderContent()}

      <Modal
        opened={!!previewUrl}
        onClose={() => setPreviewUrl(null)}
        title="Image Preview"
        size="xl"
      >
        {previewUrl && <Image src={previewUrl} alt="Preview" width="100%" height="auto" />}
      </Modal>

      <NewProductDrawer
        opened={!!createProductUrl}
        onClose={() => setCreateProductUrl(null)}
        onProductCreated={() => setCreateProductUrl(null)}
        initialThumbnailUrl={createProductUrl || ''}
      />
    </>
  );
}

export default Images;
