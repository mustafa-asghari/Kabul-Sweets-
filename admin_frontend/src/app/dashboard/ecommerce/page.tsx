'use client';

import {
  Badge,
  Container,
  Grid,
  Group,
  PaperProps,
  Progress,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  useMantineTheme,
} from '@mantine/core';
import { DonutChart, LineChart } from '@mantine/charts';

import { ErrorAlert, PageHeader, Surface } from '@/components';
import {
  useBestSellers,
  useDailyRevenue,
  useDashboardSummary,
  useOrdersStatusMix,
} from '@/lib/hooks/useApi';

const PAPER_PROPS: PaperProps = {
  p: 'md',
  style: { minHeight: '100%' },
};

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
  }).format(amount);

function DashboardMetricCards() {
  const theme = useMantineTheme();
  const { data, loading, error } = useDashboardSummary();

  if (loading) {
    return (
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 3 }} spacing="md">
        {Array.from({ length: 9 }).map((_, i) => (
          <Skeleton key={`kpi-${i}`} height={112} />
        ))}
      </SimpleGrid>
    );
  }

  if (error || !data?.succeeded || !data.data) {
    return <ErrorAlert title="Error loading KPIs" message={data?.message} />;
  }

  const summary = data.data;

  const metrics = [
    { label: 'Revenue Today', value: formatCurrency(summary.revenue_today), tone: 'indigo' },
    { label: 'Revenue This Week', value: formatCurrency(summary.revenue_this_week), tone: 'blue' },
    { label: 'Revenue This Month', value: formatCurrency(summary.revenue_this_month), tone: 'grape' },
    { label: 'Orders Today', value: String(summary.orders_today), tone: 'teal' },
    { label: 'Pending Orders', value: String(summary.orders_pending), tone: 'yellow' },
    { label: 'Preparing', value: String(summary.orders_preparing), tone: 'orange' },
    { label: 'Cake Orders Today', value: String(summary.cake_orders_today), tone: 'pink' },
    { label: 'Low Stock', value: String(summary.low_stock_count), tone: 'red' },
    { label: 'Total Customers', value: String(summary.total_customers), tone: 'cyan' },
  ];

  return (
    <SimpleGrid cols={{ base: 2, sm: 3, lg: 3 }} spacing="md">
      {metrics.map((metric) => (
        <Surface
          key={metric.label}
          p="md"
          shadow="sm"
          radius="md"
          style={{
            border: `1px solid ${theme.colors.gray[2]}`,
            background: `linear-gradient(145deg, ${theme.white}, ${theme.colors.gray[0]})`,
          }}
        >
          <Stack gap={6}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              {metric.label}
            </Text>
            <Text size="xl" fw={800}>
              {metric.value}
            </Text>
            <div
              style={{
                width: 40,
                height: 4,
                borderRadius: 999,
                background: theme.colors[metric.tone][6],
              }}
            />
          </Stack>
        </Surface>
      ))}
    </SimpleGrid>
  );
}

function RevenueAndOperationsCharts() {
  const theme = useMantineTheme();
  const {
    data: summaryData,
    loading: summaryLoading,
    error: summaryError,
  } = useDashboardSummary();
  const {
    data: revenueData,
    loading: revenueLoading,
    error: revenueError,
  } = useDailyRevenue('limit=30');
  const {
    data: statusMixData,
    loading: statusMixLoading,
    error: statusMixError,
  } = useOrdersStatusMix();

  if (summaryLoading || revenueLoading || statusMixLoading) return <Skeleton height={380} />;

  if (
    summaryError ||
    revenueError ||
    statusMixError ||
    !summaryData?.succeeded ||
    !revenueData?.succeeded ||
    !statusMixData?.succeeded
  ) {
    return (
      <ErrorAlert
        title="Error loading chart analytics"
        message={summaryData?.message || revenueData?.message || statusMixData?.message}
      />
    );
  }

  const summary = summaryData.data;
  const revenues = revenueData.data || [];
  const weeklyMix = statusMixData.data;

  if (!summary || !weeklyMix) {
    return <ErrorAlert title="Dashboard data unavailable" message="No KPI summary returned." />;
  }

  const orderMix = [
    {
      name: 'Passed',
      value: weeklyMix.passed_orders,
      color: theme.colors.green[7],
    },
    {
      name: 'Rejected',
      value: weeklyMix.rejected_orders,
      color: theme.colors.red[7],
    },
    {
      name: 'Pending',
      value: weeklyMix.pending_orders,
      color: theme.colors.yellow[7],
    },
  ];

  const revenuePulse = [
    { period: 'Today', revenue: Number(summary.revenue_today) },
    { period: 'This Week', revenue: Number(summary.revenue_this_week) },
    { period: 'This Month', revenue: Number(summary.revenue_this_month) },
  ];

  return (
    <Grid>
      <Grid.Col span={{ base: 12, lg: 8 }}>
        <Surface {...PAPER_PROPS}>
          <Text size="lg" fw={700} mb="md">
            Revenue Trend (Last 30 Days)
          </Text>
          {revenues.length === 0 ? (
            <Text c="dimmed">No revenue trend data available.</Text>
          ) : (
            <LineChart
              h={320}
              data={revenues.map((row) => ({
                date: new Date(row.date).toLocaleDateString('en-AU', {
                  month: 'short',
                  day: 'numeric',
                }),
                revenue: Number(row.total_revenue),
                avg: Number(row.average_order_value),
              }))}
              dataKey="date"
              curveType="natural"
              withDots={false}
              strokeWidth={3}
              withLegend
              series={[
                { name: 'revenue', label: 'Revenue', color: theme.colors.indigo[6] },
                { name: 'avg', label: 'Avg Order', color: theme.colors.cyan[6] },
              ]}
            />
          )}
        </Surface>
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 4 }}>
        <Stack gap="md">
          <Surface {...PAPER_PROPS}>
            <Text size="lg" fw={700} mb="md">
              Operations Mix (This Week)
            </Text>
            <Text size="sm" c="dimmed" mb="md">
              Passed, rejected, and pending orders from {weeklyMix.week_start} to{' '}
              {weeklyMix.week_end}.
            </Text>
            <DonutChart
              data={orderMix}
              withLabels
              withLabelsLine={false}
              thickness={24}
              size={220}
              chartLabel={String(weeklyMix.total_orders)}
            />
          </Surface>
          <Surface {...PAPER_PROPS}>
            <Text size="lg" fw={700} mb="md">
              Revenue Pulse
            </Text>
            <LineChart
              h={180}
              data={revenuePulse}
              dataKey="period"
              curveType="natural"
              withDots={false}
              strokeWidth={3}
              withLegend={false}
              series={[{ name: 'revenue', color: theme.colors.grape[6] }]}
            />
          </Surface>
        </Stack>
      </Grid.Col>
    </Grid>
  );
}

function BestSellersRevenueList() {
  const { data, loading, error } = useBestSellers('days=30&limit=8');

  if (loading) return <Skeleton height={320} />;
  if (error || !data?.succeeded) {
    return <ErrorAlert title="Error loading best sellers" message={data?.message} />;
  }

  const sellers = data.data || [];
  const maxRevenue = Math.max(
    1,
    ...sellers.map((item) => Number(item.total_revenue || 0))
  );

  return (
    <Surface {...PAPER_PROPS}>
      <Text size="lg" fw={700} mb="sm">
        Best Sellers Revenue Leaderboard
      </Text>
      <Text size="sm" c="dimmed" mb="lg">
        Ranked by revenue over the last 30 days.
      </Text>
      {sellers.length === 0 ? (
        <Text c="dimmed">No sales data available.</Text>
      ) : (
        <Stack gap="md">
          {sellers.map((seller, index) => {
            const revenue = Number(seller.total_revenue || 0);
            const progress = (revenue / maxRevenue) * 100;
            return (
              <div key={seller.product_id}>
                <Group justify="space-between" mb={4}>
                  <Text fw={600} size="sm">
                    {index + 1}. {seller.product_name}
                  </Text>
                  <Text fw={700} size="sm">
                    {formatCurrency(revenue)}
                  </Text>
                </Group>
                <Progress value={progress} size="md" radius="xl" color="indigo" />
                <Group gap="xs" mt={6}>
                  <Badge size="xs" variant="light">
                    Sold: {seller.total_quantity_sold}
                  </Badge>
                  <Badge size="xs" variant="outline">
                    {seller.category}
                  </Badge>
                </Group>
              </div>
            );
          })}
        </Stack>
      )}
    </Surface>
  );
}

export default function Page() {
  return (
    <>
      <>
        <title>Dashboard | Kabul Sweets Admin</title>
        <meta name="description" content="Kabul Sweets bakery dashboard" />
      </>
      <Container fluid>
        <Stack gap="lg">
          <PageHeader title="Dashboard" withActions={true} />
          <DashboardMetricCards />
          <RevenueAndOperationsCharts />
          <BestSellersRevenueList />
        </Stack>
      </Container>
    </>
  );
}
