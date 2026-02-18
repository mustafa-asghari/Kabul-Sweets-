'use client';

import { useState } from 'react';

import {
  Anchor,
  Badge,
  Button,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { Dropzone, IMAGE_MIME_TYPE } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import {
  IconMoodEmpty,
  IconPhoto,
  IconUpload,
  IconX,
} from '@tabler/icons-react';

import {
  AuthenticatedImage,
  ErrorAlert,
  PageHeader,
  Surface,
} from '@/components';
import { useApiGet, apiPost } from '@/lib/hooks/useApi';
import { PATH_DASHBOARD } from '@/routes';

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
                      img.status === 'processed'
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
                  {img.status === 'processed' && (
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
                  {img.status === 'processing' && (
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

              {/* Actions */}
              <Group grow>
                <Button
                  size="xs"
                  variant="light"
                  disabled={
                    img.status === 'processing' || img.status === 'processed'
                  }
                  onClick={() => handleProcess(img.id, 'cake')}
                >
                  AI Process
                </Button>
              </Group>

              {img.status === 'processed' && (
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
      <PageHeader title="Image Processing" breadcrumbItems={items} />

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
    </>
  );
}

export default Images;
