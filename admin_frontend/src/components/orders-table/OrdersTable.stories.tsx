import OrdersTable from './OrdersTable';

import type { OrderListItem } from '@/types';
import type { StoryObj } from '@storybook/react';

const MOCK_ORDERS: OrderListItem[] = [
  {
    id: '9613cdf1-272e-4901-8d0d-120e74a8d42b',
    order_number: 'KS-1001',
    customer_name: 'Fatima A.',
    status: 'ready',
    has_cake: true,
    total: 704.32,
    pickup_date: '2023-04-25',
    created_at: '2023-04-23T08:10:00.000Z',
  },
  {
    id: '067c4dcd-4b07-42b8-8cd0-55a6b3e9d608',
    order_number: 'KS-1002',
    customer_name: 'Ahmad K.',
    status: 'preparing',
    has_cake: false,
    total: 450.25,
    pickup_date: '2023-06-11',
    created_at: '2023-06-10T09:22:00.000Z',
  },
  {
    id: '57c40c53-9fc8-427d-be5d-a0506cabc381',
    order_number: 'KS-1003',
    customer_name: 'Sahar M.',
    status: 'pending',
    has_cake: true,
    total: 177.06,
    pickup_date: '2022-11-24',
    created_at: '2022-11-23T11:35:00.000Z',
  },
  {
    id: '34d00d61-1b4d-40ed-81bf-8c2a3f9e44db',
    order_number: 'KS-1004',
    customer_name: 'Bilal R.',
    status: 'completed',
    has_cake: false,
    total: 821.33,
    pickup_date: '2023-03-14',
    created_at: '2023-03-13T14:00:00.000Z',
  },
  {
    id: '760368e7-07b2-4c9a-87f3-7bf7eb9fa106',
    order_number: 'KS-1005',
    customer_name: 'Nadia S.',
    status: 'confirmed',
    has_cake: false,
    total: 639.56,
    pickup_date: '2022-10-24',
    created_at: '2022-10-23T15:40:00.000Z',
  },
  {
    id: '0d8a8369-283b-4137-8a8e-953d753f121c',
    order_number: 'KS-1006',
    customer_name: 'Mina H.',
    status: 'draft',
    has_cake: true,
    total: 402.8,
    pickup_date: '2023-07-01',
    created_at: '2023-06-30T10:05:00.000Z',
  },
  {
    id: '2465a917-571f-4b20-8328-213e674daf66',
    order_number: 'KS-1007',
    customer_name: 'Karim T.',
    status: 'cancelled',
    has_cake: false,
    total: 293.06,
    pickup_date: '2022-12-10',
    created_at: '2022-12-09T16:55:00.000Z',
  },
  {
    id: 'c245f961-0ecb-495b-8e4f-e012e71671b9',
    order_number: 'KS-1008',
    customer_name: 'Latifa N.',
    status: 'paid',
    has_cake: true,
    total: 386.86,
    pickup_date: '2023-01-23',
    created_at: '2023-01-22T12:00:00.000Z',
  },
];

// More on how to set up stories at: https://storybook.js.org/docs/react/writing-stories/introduction#default-export
const meta = {
  title: 'Orders/Table',
  component: OrdersTable,
  parameters: {
    // Optional parameter to center the component in the Canvas. More info: https://storybook.js.org/docs/react/configure/story-layout
    layout: 'centered',
  },
  // This component will have an automatically generated Autodocs entry: https://storybook.js.org/docs/react/writing-docs/autodocs
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof OrdersTable>;

// More on writing stories with args: https://storybook.js.org/docs/react/writing-stories/args
export const Default: Story = {
  args: {
    data: MOCK_ORDERS,
  },
};

export const Loading: Story = {
  args: {
    data: [],
    loading: true,
  },
};

export const Error: Story = {
  args: {
    data: [],
    error: 'Error loading orders',
  },
};
