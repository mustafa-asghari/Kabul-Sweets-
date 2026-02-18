'use client';

import { ReactNode, useEffect, useMemo, useState } from 'react';

import {
  ActionIcon,
  Badge,
  Group,
  MultiSelect,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconEdit, IconEye, IconSearch } from '@tabler/icons-react';
import sortBy from 'lodash/sortBy';
import {
  DataTable,
  DataTableProps,
  DataTableSortStatus,
} from 'mantine-datatable';

import { ErrorAlert } from '@/components';
import type { UserResponse } from '@/types';

const PAGE_SIZES = [5, 10, 20];

type UsersTableProps = {
  data: UserResponse[];
  error?: ReactNode;
  loading?: boolean;
  onEdit?: (user: UserResponse) => void;
  onView?: (user: UserResponse) => void;
};

const CustomersTable = ({
  data = [],
  loading,
  error,
  onEdit,
  onView,
}: UsersTableProps) => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZES[1]);
  const [selectedRecords, setSelectedRecords] = useState<UserResponse[]>([]);
  const [records, setRecords] = useState<UserResponse[]>(data.slice(0, pageSize));
  const [sortStatus, setSortStatus] = useState<DataTableSortStatus<UserResponse>>({
    columnAccessor: 'full_name',
    direction: 'asc',
  });
  const [query, setQuery] = useState('');
  const [debouncedQuery] = useDebouncedValue(query, 200);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);

  const roles = useMemo(() => {
    const unique = new Set(data.map((e) => e.role));
    return Array.from(unique);
  }, [data]);

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-AU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const columns: DataTableProps<UserResponse>['columns'] = [
    {
      accessor: 'full_name',
      title: 'Name',
      sortable: true,
      filter: (
        <TextInput
          label="Search"
          description="Search by name or email"
          placeholder="Search..."
          leftSection={<IconSearch size={16} />}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
        />
      ),
      filtering: query !== '',
    },
    {
      accessor: 'email',
      sortable: true,
    },
    {
      accessor: 'phone',
      title: 'Phone',
      render: (item: UserResponse) => item.phone || '-',
    },
    {
      accessor: 'role',
      render: (item: UserResponse) => (
        <Badge
          color={item.role === 'admin' ? 'blue' : 'gray'}
          variant="light"
          size="sm"
        >
          {item.role}
        </Badge>
      ),
      filter: (
        <MultiSelect
          label="Role"
          data={roles}
          value={selectedRoles}
          placeholder="Filter by role"
          onChange={setSelectedRoles}
          clearable
          searchable
        />
      ),
      filtering: selectedRoles.length > 0,
    },
    {
      accessor: 'is_active',
      title: 'Status',
      render: (item: UserResponse) => (
        <Badge
          color={item.is_active ? 'green' : 'red'}
          variant="filled"
          radius="sm"
          size="sm"
        >
          {item.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      accessor: 'created_at',
      title: 'Joined',
      sortable: true,
      render: (item: UserResponse) => formatDate(item.created_at),
    },
    {
      accessor: 'last_login',
      title: 'Last Login',
      sortable: true,
      render: (item: UserResponse) => formatDate(item.last_login),
    },
    {
      accessor: 'actions',
      title: 'Actions',
      textAlign: 'right',
      render: (item: UserResponse) => (
        <Group gap="xs" justify="flex-end">
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
        ({ full_name, email }) =>
          full_name?.toLowerCase().includes(q) ||
          email?.toLowerCase().includes(q)
      );
    }

    if (selectedRoles.length) {
      filtered = filtered.filter(({ role }) => selectedRoles.includes(role));
    }

    const sorted = sortBy(filtered, sortStatus.columnAccessor) as UserResponse[];
    if (sortStatus.direction === 'desc') sorted.reverse();

    setRecords(sorted.slice(from, to));
  }, [sortStatus, data, page, pageSize, debouncedQuery, selectedRoles]);

  return error ? (
    <ErrorAlert title="Error loading users" message={error.toString()} />
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
        debouncedQuery || selectedRoles.length > 0
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

export default CustomersTable;
