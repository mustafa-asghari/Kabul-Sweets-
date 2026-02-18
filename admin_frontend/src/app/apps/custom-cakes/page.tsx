'use client';

import { useState } from 'react';

import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Divider,
  Drawer,
  Group,
  Image,
  MantineColor,
  Modal,
  NumberInput,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
  Tooltip,
} from '@mantine/core';
import { Dropzone, IMAGE_MIME_TYPE } from '@mantine/dropzone';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import {
  IconCheck,
  IconEye,
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
import {
  apiPost,
  useApiGet,
  useCustomCake,
  useCustomCakes,
} from '@/lib/hooks/useApi';
import { PATH_DASHBOARD } from '@/routes';
import type { CustomCake, CustomCakeStatus } from '@/types/custom-cake';

const items = [
  { title: 'Dashboard', href: PATH_DASHBOARD.ecommerce },
  { title: 'Store', href: '#' },
  { title: 'Custom Cakes', href: '#' },
].map((item, index) => (
  <Anchor href={item.href} key={index}>
    {item.title}
  </Anchor>
));

const STATUS_COLORS: Record<CustomCakeStatus, MantineColor> = {
  pending_review: 'yellow',
  approved_awaiting_payment: 'blue',
  paid: 'green',
  in_production: 'orange',
  completed: 'teal',
  rejected: 'red',
  cancelled: 'gray',
};

const formatCurrency = (amount: number | null) => {
  if (amount == null) return '-';
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
  }).format(amount);
};

const formatDate = (dateValue: string | null | undefined) => {
  if (!dateValue) return '-';
  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) return dateValue;
  return parsed.toLocaleDateString('en-AU');
};

const formatDateTime = (dateValue: string | null | undefined) => {
  if (!dateValue) return '-';
  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) return dateValue;
  return parsed.toLocaleString('en-AU');
};

interface CakeImageRecord {
  id: string;
  status: string;
  admin_chosen: string | null;
  has_processed: boolean;
  created_at: string;
}

function CustomCakes() {
  const { data, loading, error, refetch } = useCustomCakes();
  const [selectedCake, setSelectedCake] = useState<CustomCake | null>(null);
  const [selectedCakeId, setSelectedCakeId] = useState<string | null>(null);
  const [approveOpened, { open: openApprove, close: closeApprove }] =
    useDisclosure(false);
  const [rejectOpened, { open: openReject, close: closeReject }] =
    useDisclosure(false);
  const [detailsOpened, { open: openDetails, close: closeDetails }] =
    useDisclosure(false);
  const [finalPrice, setFinalPrice] = useState<number>(0);
  const [adminNotes, setAdminNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [uploadingImages, setUploadingImages] = useState(false);

  const {
    data: detailData,
    loading: detailLoading,
    error: detailError,
    refetch: refetchDetail,
  } = useCustomCake(selectedCakeId);

  const {
    data: cakeImagesData,
    loading: cakeImagesLoading,
    error: cakeImagesError,
    refetch: refetchCakeImages,
  } = useApiGet<CakeImageRecord[]>(
    selectedCakeId ? `/api/images?custom_cake_id=${selectedCakeId}` : null,
  );

  const cakeDetails = detailData?.data;
  const cakeImages = cakeImagesData?.data || [];

  const handleApprove = async () => {
    if (!selectedCake || finalPrice <= 0) return;
    setActionLoading(true);
    try {
      const result = await apiPost(`/api/custom-cakes/${selectedCake.id}`, {
        action: 'approve',
        final_price: finalPrice,
        admin_notes: adminNotes || undefined,
      });
      if (!result.succeeded) throw new Error(result.message);
      notifications.show({
        title: 'Approved',
        message: 'Custom cake approved',
        color: 'green',
      });
      closeApprove();
      refetch();
      if (selectedCakeId === selectedCake.id) {
        refetchDetail();
      }
    } catch (err) {
      notifications.show({
        title: 'Error',
        message: err instanceof Error ? err.message : 'Failed to approve',
        color: 'red',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedCake || rejectionReason.length < 10) return;
    setActionLoading(true);
    try {
      const result = await apiPost(`/api/custom-cakes/${selectedCake.id}`, {
        action: 'reject',
        rejection_reason: rejectionReason,
      });
      if (!result.succeeded) throw new Error(result.message);
      notifications.show({
        title: 'Rejected',
        message: 'Custom cake rejected',
        color: 'orange',
      });
      closeReject();
      refetch();
      if (selectedCakeId === selectedCake.id) {
        refetchDetail();
      }
    } catch (err) {
      notifications.show({
        title: 'Error',
        message: err instanceof Error ? err.message : 'Failed to reject',
        color: 'red',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleViewDetails = (cake: CustomCake) => {
    setSelectedCakeId(cake.id);
    openDetails();
  };

  const handleCloseDetails = () => {
    closeDetails();
    setSelectedCakeId(null);
  };

  const handleUploadImages = async (files: File[]) => {
    if (!selectedCakeId || !files.length) return;

    setUploadingImages(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('custom_cake_id', selectedCakeId);

        const response = await fetch('/api/images', {
          method: 'POST',
          body: formData,
        });
        const result = await response.json();

        if (!response.ok || !result.succeeded) {
          throw new Error(result.message || `Failed to upload ${file.name}`);
        }
      }

      notifications.show({
        title: 'Upload complete',
        message: `${files.length} image(s) saved for this cake request`,
        color: 'green',
      });

      refetchCakeImages();
      refetchDetail();
    } catch (err) {
      notifications.show({
        title: 'Upload error',
        message: err instanceof Error ? err.message : 'Failed to upload image',
        color: 'red',
      });
    } finally {
      setUploadingImages(false);
    }
  };

  const renderDetailsContent = () => {
    if (detailLoading) {
      return (
        <Stack gap="sm">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={`cake-detail-loading-${index}`} height={80} />
          ))}
        </Stack>
      );
    }

    if (detailError || (detailData && !detailData.succeeded)) {
      return (
        <ErrorAlert
          title="Error loading cake details"
          message={detailData?.message || detailError?.message}
        />
      );
    }

    if (!cakeDetails) {
      return <Text size="sm">Select a custom cake to view full details.</Text>;
    }

    return (
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={4}>{cakeDetails.flavor} Cake</Title>
            <Text size="sm" c="dimmed">
              Customer:{' '}
              {cakeDetails.customer_name ||
                cakeDetails.customer_email ||
                cakeDetails.customer_id}
            </Text>
            <Text size="xs" c="dimmed">
              Created: {formatDateTime(cakeDetails.created_at)}
            </Text>
          </div>
          <Badge
            color={STATUS_COLORS[cakeDetails.status]}
            radius="sm"
            size="lg"
          >
            {cakeDetails.status.replace(/_/g, ' ')}
          </Badge>
        </Group>

        <Card withBorder radius="md">
          <Title order={5} mb="sm">
            Cake Details
          </Title>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <Text size="sm">
              <b>Flavor:</b> {cakeDetails.flavor}
            </Text>
            <Text size="sm">
              <b>Shape:</b> {cakeDetails.shape}
            </Text>
            <Text size="sm">
              <b>Size:</b> {cakeDetails.diameter_inches}&quot; x{' '}
              {cakeDetails.height_inches}
              &quot;
            </Text>
            <Text size="sm">
              <b>Layers:</b> {cakeDetails.layers}
            </Text>
            <Text size="sm">
              <b>Decoration:</b> {cakeDetails.decoration_complexity}
            </Text>
            <Text size="sm">
              <b>Rush Order:</b> {cakeDetails.is_rush_order ? 'Yes' : 'No'}
            </Text>
            <Text size="sm">
              <b>Event Type:</b> {cakeDetails.event_type || '-'}
            </Text>
            <Text size="sm">
              <b>Requested Date:</b> {formatDate(cakeDetails.requested_date)}
            </Text>
          </SimpleGrid>
        </Card>

        <Card withBorder radius="md">
          <Title order={5} mb="sm">
            Pricing
          </Title>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <Text size="sm">
              <b>Predicted Price:</b>{' '}
              {formatCurrency(cakeDetails.predicted_price)}
            </Text>
            <Text size="sm">
              <b>Final Price:</b> {formatCurrency(cakeDetails.final_price)}
            </Text>
            <Text size="sm">
              <b>Predicted Servings:</b> {cakeDetails.predicted_servings ?? '-'}
            </Text>
            <Text size="sm">
              <b>Time Slot:</b> {cakeDetails.time_slot || '-'}
            </Text>
          </SimpleGrid>
        </Card>

        <Card withBorder radius="md">
          <Title order={5} mb="sm">
            Notes
          </Title>
          <Stack gap="xs">
            <Text size="sm">
              <b>Cake Message:</b> {cakeDetails.cake_message || '-'}
            </Text>
            <Text size="sm">
              <b>Decoration Description:</b>{' '}
              {cakeDetails.decoration_description || '-'}
            </Text>
            <Text size="sm">
              <b>Allergen Notes:</b> {cakeDetails.allergen_notes || '-'}
            </Text>
            <Text size="sm">
              <b>Admin Notes:</b> {cakeDetails.admin_notes || '-'}
            </Text>
            {cakeDetails.rejection_reason && (
              <Text size="sm" c="red.7">
                <b>Rejection Reason:</b> {cakeDetails.rejection_reason}
              </Text>
            )}
          </Stack>
        </Card>

        {(cakeDetails.ai_description_short ||
          cakeDetails.ai_description_long) && (
          <Card withBorder radius="md">
            <Title order={5} mb="sm">
              AI Descriptions
            </Title>
            <Stack gap="xs">
              {cakeDetails.ai_description_short && (
                <Text size="sm">{cakeDetails.ai_description_short}</Text>
              )}
              {cakeDetails.ai_description_long && (
                <>
                  <Divider />
                  <Text size="sm">{cakeDetails.ai_description_long}</Text>
                </>
              )}
            </Stack>
          </Card>
        )}

        <Card withBorder radius="md">
          <Title order={5} mb="sm">
            Upload Reference Images
          </Title>
          <Text size="sm" c="dimmed" mb="sm">
            Images uploaded here are stored in the database and linked to this
            custom cake request.
          </Text>
          <Dropzone
            onDrop={handleUploadImages}
            accept={IMAGE_MIME_TYPE}
            loading={uploadingImages}
            maxSize={10 * 1024 * 1024}
          >
            <Group
              justify="center"
              gap="xl"
              mih={110}
              style={{ pointerEvents: 'none' }}
            >
              <Dropzone.Accept>
                <IconUpload size={36} />
              </Dropzone.Accept>
              <Dropzone.Reject>
                <IconX size={36} />
              </Dropzone.Reject>
              <Dropzone.Idle>
                <IconPhoto size={36} />
              </Dropzone.Idle>
              <div>
                <Text size="sm">Drag image(s) here or click to select</Text>
                <Text size="xs" c="dimmed">
                  Max 10MB per image. JPEG, PNG, WebP, GIF.
                </Text>
              </div>
            </Group>
          </Dropzone>
        </Card>

        <Card withBorder radius="md">
          <Title order={5} mb="sm">
            Uploaded Cake Images
          </Title>
          {cakeImagesLoading ? (
            <Stack gap="sm">
              <Skeleton height={120} />
              <Skeleton height={120} />
            </Stack>
          ) : cakeImagesError ? (
            <Text size="sm" c="red">
              Failed to load uploaded images.
            </Text>
          ) : cakeImages.length ? (
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              {cakeImages.map((image) => {
                const showProcessed =
                  image.admin_chosen === 'processed' ||
                  (image.status === 'completed' && image.has_processed);

                return (
                  <Card key={image.id} withBorder p="xs">
                    <div
                      style={{
                        height: 140,
                        overflow: 'hidden',
                        borderRadius: 8,
                      }}
                    >
                      <AuthenticatedImage
                        src={`/api/images/${image.id}/${
                          showProcessed ? 'processed' : 'original'
                        }`}
                        alt={`Cake image ${image.id}`}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                        }}
                      />
                    </div>
                    <Group justify="space-between" mt="xs">
                      <Badge size="xs" variant="light">
                        {image.status}
                      </Badge>
                      {image.admin_chosen && (
                        <Badge size="xs" color="blue" variant="dot">
                          chosen: {image.admin_chosen}
                        </Badge>
                      )}
                    </Group>
                    <Text size="xs" c="dimmed" mt={4}>
                      Uploaded: {formatDateTime(image.created_at)}
                    </Text>
                  </Card>
                );
              })}
            </SimpleGrid>
          ) : (
            <Text size="sm" c="dimmed">
              No uploaded images linked to this cake yet.
            </Text>
          )}
        </Card>

        {cakeDetails.reference_images?.length ? (
          <Card withBorder radius="md">
            <Title order={5} mb="sm">
              Customer Provided Reference Images
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              {cakeDetails.reference_images.map((imageUrl, index) => (
                <Card key={`${imageUrl}-${index}`} withBorder p="xs">
                  <Image
                    src={imageUrl}
                    alt={`Customer reference ${index + 1}`}
                    h={140}
                    fit="cover"
                    radius="sm"
                  />
                </Card>
              ))}
            </SimpleGrid>
          </Card>
        ) : null}
      </Stack>
    );
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
      return (
        <ErrorAlert
          title="Error loading custom cakes"
          message={data?.message}
        />
      );
    }

    const cakes = data?.data || [];

    if (!cakes.length) {
      return (
        <Surface p="md">
          <Stack align="center">
            <IconMoodEmpty size={24} />
            <Title order={4}>No custom cake submissions</Title>
            <Text>No custom cakes have been submitted yet.</Text>
          </Stack>
        </Surface>
      );
    }

    return (
      <Surface>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Customer</Table.Th>
              <Table.Th>Flavor</Table.Th>
              <Table.Th>Details</Table.Th>
              <Table.Th>Complexity</Table.Th>
              <Table.Th>Predicted Price</Table.Th>
              <Table.Th>Final Price</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {cakes.map((cake) => (
              <Table.Tr key={cake.id}>
                <Table.Td>
                  {cake.customer_name || cake.customer_email || '-'}
                </Table.Td>
                <Table.Td fw={500}>{cake.flavor}</Table.Td>
                <Table.Td>
                  <Text size="xs">
                    {cake.layers}L, {cake.diameter_inches}&quot;, {cake.shape}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light" size="sm">
                    {cake.decoration_complexity}
                  </Badge>
                </Table.Td>
                <Table.Td>{formatCurrency(cake.predicted_price)}</Table.Td>
                <Table.Td fw={600}>{formatCurrency(cake.final_price)}</Table.Td>
                <Table.Td>
                  <Badge
                    color={STATUS_COLORS[cake.status]}
                    variant="filled"
                    radius="sm"
                    size="sm"
                  >
                    {cake.status.replace(/_/g, ' ')}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" wrap="nowrap">
                    <Tooltip label="View full details">
                      <ActionIcon
                        variant="subtle"
                        color="blue"
                        onClick={() => handleViewDetails(cake)}
                      >
                        <IconEye size={16} />
                      </ActionIcon>
                    </Tooltip>

                    {cake.status === 'pending_review' && (
                      <>
                        <Button
                          size="xs"
                          color="green"
                          variant="light"
                          leftSection={<IconCheck size={14} />}
                          onClick={() => {
                            setSelectedCake(cake);
                            setFinalPrice(Number(cake.predicted_price) || 0);
                            setAdminNotes('');
                            openApprove();
                          }}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          leftSection={<IconX size={14} />}
                          onClick={() => {
                            setSelectedCake(cake);
                            setRejectionReason('');
                            openReject();
                          }}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Surface>
    );
  };

  return (
    <>
      <>
        <title>Custom Cakes | Kabul Sweets Admin</title>
        <meta name="description" content="Manage custom cake submissions" />
      </>
      <PageHeader title="Custom Cake Approvals" breadcrumbItems={items} />

      {renderContent()}

      <Drawer
        opened={detailsOpened}
        onClose={handleCloseDetails}
        title="Custom Cake Details"
        position="right"
        size="xl"
      >
        {renderDetailsContent()}
      </Drawer>

      <Modal
        opened={approveOpened}
        onClose={closeApprove}
        title="Approve Custom Cake"
      >
        <Stack>
          <Text>Set the final price for this custom cake order.</Text>
          <NumberInput
            label="Final Price"
            prefix="$"
            decimalScale={2}
            min={0}
            value={finalPrice}
            onChange={(v) => setFinalPrice(Number(v))}
            required
          />
          <Textarea
            label="Admin Notes (optional)"
            value={adminNotes}
            onChange={(e) => setAdminNotes(e.currentTarget.value)}
          />
          <Button onClick={handleApprove} loading={actionLoading} color="green">
            Approve & Send Payment Link
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={rejectOpened}
        onClose={closeReject}
        title="Reject Custom Cake"
      >
        <Stack>
          <Text>Provide a reason for rejection (min 10 characters).</Text>
          <Textarea
            label="Rejection Reason"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.currentTarget.value)}
            minLength={10}
            required
          />
          <Button
            onClick={handleReject}
            loading={actionLoading}
            color="red"
            disabled={rejectionReason.length < 10}
          >
            Reject
          </Button>
        </Stack>
      </Modal>
    </>
  );
}

export default CustomCakes;
