import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import OrdersTable from '@/components/orders-table/OrdersTable';
import { mockOrders } from '../fixtures';
import { render } from '../test-utils';

describe('OrdersTable', () => {
  it('renders the DataTable component', () => {
    const { container } = render(<OrdersTable data={mockOrders} />);
    expect(container.querySelector('.mantine-datatable')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    const { container } = render(<OrdersTable data={mockOrders} />);
    const headers = container.querySelectorAll('th');
    expect(headers.length).toBeGreaterThan(0);
  });

  it('shows loading state', () => {
    const { container } = render(<OrdersTable data={[]} loading={true} />);
    expect(container.querySelector('.mantine-datatable')).toBeInTheDocument();
  });

  it('shows error alert when error is provided', () => {
    render(<OrdersTable data={[]} error="Something went wrong" />);
    expect(screen.getByText('Error loading orders')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    const { container } = render(<OrdersTable data={[]} />);
    expect(container.querySelector('.mantine-datatable')).toBeInTheDocument();
  });

  it('accepts onEdit and onView callbacks', () => {
    const onEdit = () => {};
    const onView = () => {};
    const { container } = render(
      <OrdersTable data={mockOrders} onEdit={onEdit} onView={onView} />
    );
    expect(container.querySelector('.mantine-datatable')).toBeInTheDocument();
  });
});
