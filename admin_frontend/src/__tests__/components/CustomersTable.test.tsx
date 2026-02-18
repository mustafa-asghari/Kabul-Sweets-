import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import CustomersTable from '@/components/customers-table/CustomersTable';
import { mockUsers } from '../fixtures';
import { render } from '../test-utils';

describe('CustomersTable', () => {
  it('renders the DataTable component', () => {
    const { container } = render(<CustomersTable data={mockUsers} />);
    expect(container.querySelector('.mantine-datatable')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    const { container } = render(<CustomersTable data={mockUsers} />);
    const headers = container.querySelectorAll('th');
    expect(headers.length).toBeGreaterThan(0);
  });

  it('shows error alert when error is provided', () => {
    render(<CustomersTable data={[]} error="Something went wrong" />);
    expect(screen.getByText('Error loading users')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    const { container } = render(<CustomersTable data={[]} />);
    expect(container.querySelector('.mantine-datatable')).toBeInTheDocument();
  });
});
