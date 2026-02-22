'use client';

import { ReactNode, useEffect, useMemo, useState } from 'react';

import {
  ActionIcon,
  Badge,
  Group,
  MantineColor,
  MultiSelect,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconCheck, IconEdit, IconEye, IconSearch, IconX } from '@tabler/icons-react';
import sortBy from 'lodash/sortBy';
import {
  DataTable,
  DataTableProps,
  DataTableSortStatus,
} from 'mantine-datatable';

import { ErrorAlert } from '@/components';
import type { OrderListItem, OrderStatus } from '@/types';

const STATUS_COLORS: Record<string, MantineColor> = {
  draft: 'gray',
  pending: 'yellow',
  pending_approval: 'orange',
  paid: 'blue',
  confirmed: 'indigo',
  preparing: 'orange',
  ready: 'teal',
  completed: 'green',
  cancelled: 'red',
  refunded: 'pink',
};

type StatusBadgeProps = {
  status?: OrderStatus;
};

const StatusBadge = ({ status }: StatusBadgeProps) => {
  if (!status)
    return (
      <Badge color="gray" variant="filled" radius="sm">
        Unknown
      </Badge>
    );

  return (
    <Badge color={STATUS_COLORS[status] || 'gray'} variant="filled" radius="sm">
      {status.replace('_', ' ')}
    </Badge>
  );
};

const PAGE_SIZES = [5, 10, 20];

type OrdersTableProps = {
  data: OrderListItem[];
  error?: ReactNode;
  loading?: boolean;
  onEdit?: (order: OrderListItem) => void;
  onView?: (order: OrderListItem) => void;
  onApprove?: (order: OrderListItem) => void;
  onReject?: (order: OrderListItem) => void;
};

const OrdersTable = ({
  data = [],
  loading,
  error,
  onEdit,
  onView,
  onApprove,
  onReject,
}: OrdersTableProps) => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZES[1]);
  const [selectedRecords, setSelectedRecords] = useState<OrderListItem[]>([]);
  const [records, setRecords] = useState<OrderListItem[]>(data.slice(0, pageSize));
  const [sortStatus, setSortStatus] = useState<DataTableSortStatus<OrderListItem>>({
    columnAccessor: 'created_at',
    direction: 'desc',
  });
  const [query, setQuery] = useState('');
  const [debouncedQuery] = useDebouncedValue(query, 200);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);

  const statuses = useMemo(() => {
    const unique = new Set(data.map((e) => e.status));
    return Array.from(unique);
  }, [data]);

  const formatCurrency = (amount?: number) => {
    if (amount == null) return 'N/A';
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD',
    }).format(amount);
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-AU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const columns: DataTableProps<OrderListItem>['columns'] = [
    {
      accessor: 'order_number',
      title: 'Order #',
      sortable: true,
      filter: (
        <TextInput
          label="Search"
          description="Search by order number or customer name"
          placeholder="Search..."
          leftSection={<IconSearch size={16} />}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
        />
      ),
      filtering: query !== '',
    },
    {
      accessor: 'customer_name',
      title: 'Customer',
      sortable: true,
    },
    {
      accessor: 'status',
      render: (item: OrderListItem) => <StatusBadge status={item.status} />,
      filter: (
        <MultiSelect
          label="Status"
          data={statuses}
          value={selectedStatuses}
          placeholder="Filter by status"
          onChange={setSelectedStatuses}
          leftSection={<IconSearch size={16} />}
          clearable
          searchable
        />
      ),
      filtering: selectedStatuses.length > 0,
    },
    {
      accessor: 'total',
      sortable: true,
      render: (item: OrderListItem) => formatCurrency(item.total),
    },
    {
      accessor: 'has_cake',
      title: 'Cake',
      render: (item: OrderListItem) =>
        item.has_cake ? (
          <Badge color="pink" variant="light" size="sm">
            Cake
          </Badge>
        ) : null,
    },
    {
      accessor: 'pickup_date',
      title: 'Pickup',
      sortable: true,
      render: (item: OrderListItem) => formatDate(item.pickup_date),
    },
    {
      accessor: 'created_at',
      title: 'Created',
      sortable: true,
      render: (item: OrderListItem) => formatDate(item.created_at),
    },
    {
      accessor: 'actions',
      title: 'Actions',
      textAlign: 'right',
      render: (item: OrderListItem) => (
        <Group gap="xs" justify="flex-end">
          {(item.status === 'pending' || item.status === 'pending_approval') && onApprove && (
            <Tooltip label="Approve">
              <ActionIcon
                variant="subtle"
                color="green"
                onClick={() => onApprove(item)}
              >
                <IconCheck size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          {(item.status === 'pending' || item.status === 'pending_approval') && onReject && (
            <Tooltip label="Reject">
              <ActionIcon
                variant="subtle"
                color="red"
                onClick={() => onReject(item)}
              >
                <IconX size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          {onView && (
            <Tooltip label="View">
              <ActionIcon
                variant="subtle"
                color="blue"
                onClick={() => onView(item)}
              >
                <IconEye size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          {onEdit && (
            <Tooltip label="Edit">
              <ActionIcon
                variant="subtle"
                color="gray"
                onClick={() => onEdit(item)}
              >
                <IconEdit size={16} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      ),
    },
  ];

  useEffect(() => {
    setPage(1);
  }, [pageSize]);

  useEffect(() => {
    const from = (page - 1) * pageSize;
    const to = from + pageSize;
    let filtered = data;

    if (debouncedQuery) {
      const q = debouncedQuery.trim().toLowerCase();
      filtered = filtered.filter(
        ({ order_number, customer_name }) =>
          order_number?.toLowerCase().includes(q) ||
          customer_name?.toLowerCase().includes(q)
      );
    }

    if (selectedStatuses.length) {
      filtered = filtered.filter(({ status }) =>
        selectedStatuses.includes(status)
      );
    }

    const sorted = sortBy(filtered, sortStatus.columnAccessor) as OrderListItem[];
    if (sortStatus.direction === 'desc') sorted.reverse();

    setRecords(sorted.slice(from, to));
  }, [sortStatus, data, page, pageSize, debouncedQuery, selectedStatuses]);

  return error ? (
    <ErrorAlert title="Error loading orders" message={error.toString()} />
  ) : (
    <DataTable
      minHeight={200}
      verticalSpacing="sm"
      striped={true}
      columns={columns}
      records={records}
      selectedRecords={selectedRecords}
      onSelectedRecordsChange={setSelectedRecords}
      totalRecords={
        debouncedQuery || selectedStatuses.length > 0
          ? records.length
          : data.length
      }
      recordsPerPage={pageSize}
      page={page}
      onPageChange={(p) => setPage(p)}
      recordsPerPageOptions={PAGE_SIZES}
      onRecordsPerPageChange={setPageSize}
      sortStatus={sortStatus}
      onSortStatusChange={setSortStatus}
      fetching={loading}
    />
  );
};

export default OrdersTable;
