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
  useCartRecoveryAnalytics,
  usePopularCakeSizes,
  useProductPageViews,
  useVisitorAnalytics,
  useWorstSellers,
} from '@/lib/hooks/useApi';

const PAPER_PROPS: PaperProps = {
  p: 'md',
  style: { minHeight: '100%' },
};

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 0,
  }).format(amount);

const formatNumber = (value: number) =>
  new Intl.NumberFormat('en-AU', {
    maximumFractionDigits: 0,
  }).format(value);

const prettifySlug = (slug: string) => {
  try {
    const cleaned = decodeURIComponent(slug).replace(/[-_]+/g, ' ').trim();
    return cleaned
      ? cleaned.replace(/\b\w/g, (char) => char.toUpperCase())
      : 'Unknown Product';
  } catch {
    return slug || 'Unknown Product';
  }
};

type RankedRow = {
  id: string;
  label: string;
  value: number;
  meta?: string;
  badge?: string;
};

type RankedProgressListProps = {
  title: string;
  subtitle?: string;
  color: string;
  rows: RankedRow[];
  emptyText: string;
  valueFormatter?: (value: number) => string;
};

function RankedProgressList({
  title,
  subtitle,
  color,
  rows,
  emptyText,
  valueFormatter = formatNumber,
}: RankedProgressListProps) {
  const maxValue = Math.max(1, ...rows.map((row) => row.value));

  return (
    <Surface {...PAPER_PROPS}>
      <Text size="lg" fw={700} mb={4}>
        {title}
      </Text>
      {subtitle ? (
        <Text size="sm" c="dimmed" mb="lg">
          {subtitle}
        </Text>
      ) : null}

      {rows.length === 0 ? (
        <Text c="dimmed">{emptyText}</Text>
      ) : (
        <Stack gap="md">
          {rows.map((row, index) => {
            const progress = (row.value / maxValue) * 100;
            return (
              <div key={row.id}>
                <Group justify="space-between" mb={4} wrap="nowrap">
                  <Group gap="xs" wrap="nowrap" style={{ minWidth: 0, flex: 1 }}>
                    <Badge variant="light" color={color} radius="sm">
                      {index + 1}
                    </Badge>
                    <Text fw={600} size="sm" lineClamp={1}>
                      {row.label}
                    </Text>
                  </Group>
                  <Text fw={700} size="sm">
                    {valueFormatter(row.value)}
                  </Text>
                </Group>
                <Progress value={progress} size="md" radius="xl" color={color} />
                {row.meta || row.badge ? (
                  <Group gap="xs" mt={6} wrap="nowrap">
                    {row.badge ? (
                      <Badge size="xs" variant="outline" color={color}>
                        {row.badge}
                      </Badge>
                    ) : null}
                    {row.meta ? (
                      <Text size="xs" c="dimmed" lineClamp={1}>
                        {row.meta}
                      </Text>
                    ) : null}
                  </Group>
                ) : null}
              </div>
            );
          })}
        </Stack>
      )}
    </Surface>
  );
}

function TrafficOverviewCards() {
  const theme = useMantineTheme();
  const { data: visitorsData, loading: visitorsLoading, error: visitorsError } =
    useVisitorAnalytics('days=30');
  const { data: cartData, loading: cartLoading, error: cartError } =
    useCartRecoveryAnalytics('min_age_hours=1');

  if (visitorsLoading || cartLoading) {
    return (
      <SimpleGrid cols={{ base: 2, md: 5 }} spacing="md">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={`traffic-card-${i}`} height={104} />
        ))}
      </SimpleGrid>
    );
  }

  if (visitorsError || cartError || !visitorsData?.succeeded || !cartData?.succeeded) {
    return (
      <ErrorAlert
        title="Error loading traffic analytics"
        message={visitorsData?.message || cartData?.message}
      />
    );
  }

  const visits = visitorsData.data?.visits_over_time || [];
  const totalVisits = visits.reduce((acc, row) => acc + row.visits, 0);
  const totalUniqueVisitors = visits.reduce((acc, row) => acc + row.unique_visitors, 0);
  const cart = cartData.data;

  const cards = [
    { label: 'Frontend Visits (30d)', value: formatNumber(totalVisits), color: 'indigo' },
    {
      label: 'Unique Visitors (30d)',
      value: formatNumber(totalUniqueVisitors),
      color: 'teal',
    },
    {
      label: 'Checkout Not Purchased',
      value: formatNumber(cart?.current_abandoned_carts || 0),
      color: 'red',
    },
    { label: 'Converted Carts', value: formatNumber(cart?.converted_carts || 0), color: 'green' },
    { label: 'Cart Conversion Rate', value: cart?.conversion_rate || '0%', color: 'orange' },
  ];

  return (
    <SimpleGrid cols={{ base: 2, md: 5 }} spacing="md">
      {cards.map((card) => (
        <Surface
          key={card.label}
          p="md"
          radius="lg"
          shadow="sm"
          style={{
            border: `1px solid ${theme.colors.gray[2]}`,
            background: `linear-gradient(155deg, ${theme.white}, ${theme.colors.gray[0]})`,
          }}
        >
          <Stack gap={6}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              {card.label}
            </Text>
            <Text size="xl" fw={800}>
              {card.value}
            </Text>
            <div
              style={{
                width: 42,
                height: 4,
                borderRadius: 999,
                background: theme.colors[card.color][6],
              }}
            />
          </Stack>
        </Surface>
      ))}
    </SimpleGrid>
  );
}

function TrafficAndCheckoutCharts() {
  const theme = useMantineTheme();
  const { data: visitorsData, loading: visitorsLoading, error: visitorsError } =
    useVisitorAnalytics('days=30');
  const { data: cartData, loading: cartLoading, error: cartError } =
    useCartRecoveryAnalytics('min_age_hours=1');

  if (visitorsLoading || cartLoading) return <Skeleton height={420} />;

  if (visitorsError || cartError || !visitorsData?.succeeded || !cartData?.succeeded) {
    return (
      <ErrorAlert
        title="Error loading traffic charts"
        message={visitorsData?.message || cartData?.message}
      />
    );
  }

  const visits = visitorsData.data?.visits_over_time || [];
  const cart = cartData.data;

  const checkoutOutcome = [
    {
      name: 'Converted',
      value: cart?.converted_carts || 0,
      color: theme.colors.green[6],
    },
    {
      name: 'Abandoned',
      value: cart?.current_abandoned_carts || 0,
      color: theme.colors.red[6],
    },
    {
      name: 'Recovered',
      value: cart?.recovered_carts || 0,
      color: theme.colors.teal[6],
    },
  ];

  const checkoutFlowRows: RankedRow[] = [
    {
      id: 'active-carts',
      label: 'Active Carts',
      value: cart?.active_carts || 0,
      meta: 'Current carts being edited by users',
    },
    {
      id: 'converted-carts',
      label: 'Converted Carts',
      value: cart?.converted_carts || 0,
      meta: 'Carts that completed payment',
      badge: cart?.conversion_rate || '0%',
    },
    {
      id: 'abandoned-carts',
      label: 'Checkout Not Purchased',
      value: cart?.current_abandoned_carts || 0,
      meta: 'Users reached checkout but did not buy',
    },
    {
      id: 'recovered-carts',
      label: 'Recovered Carts',
      value: cart?.recovered_carts || 0,
      meta: 'Abandoned carts recovered later',
    },
  ];

  return (
    <Grid>
      <Grid.Col span={{ base: 12, lg: 8 }}>
        <Surface {...PAPER_PROPS}>
          <Text size="lg" fw={700} mb={4}>
            Frontend Visits Trend
          </Text>
          <Text size="sm" c="dimmed" mb="md">
            Last 30 days of total visits and unique visitors.
          </Text>
          {visits.length === 0 ? (
            <Text c="dimmed">
              No visit events yet. This chart will fill automatically when page views are tracked.
            </Text>
          ) : (
            <LineChart
              h={320}
              data={visits.map((row) => ({
                date: new Date(row.date).toLocaleDateString('en-AU', {
                  month: 'short',
                  day: 'numeric',
                }),
                visits: row.visits,
                unique: row.unique_visitors,
              }))}
              dataKey="date"
              curveType="natural"
              withDots={false}
              strokeWidth={3}
              withLegend
              series={[
                { name: 'visits', label: 'Visits', color: theme.colors.indigo[6] },
                { name: 'unique', label: 'Unique Visitors', color: theme.colors.teal[6] },
              ]}
            />
          )}
        </Surface>
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 4 }}>
        <Surface h="100%" {...PAPER_PROPS}>
          <Text size="lg" fw={700} mb={4}>
            Checkout Outcome
          </Text>
          <Text size="sm" c="dimmed" mb="md">
            Split of checkout completion, abandonment, and recovery.
          </Text>
          <DonutChart
            data={checkoutOutcome}
            thickness={24}
            withLabels
            withLabelsLine={false}
            size={220}
            chartLabel={cart?.conversion_rate || '0%'}
          />
        </Surface>
      </Grid.Col>
      <Grid.Col span={12}>
        <RankedProgressList
          title="Checkout Flow"
          subtitle="How many users reach checkout, convert, or drop off."
          color="orange"
          rows={checkoutFlowRows}
          emptyText="No checkout data available yet."
        />
      </Grid.Col>
    </Grid>
  );
}

function ProductPerformanceCharts() {
  const {
    data: bestData,
    loading: bestLoading,
    error: bestError,
  } = useBestSellers('days=30&limit=8');
  const {
    data: worstData,
    loading: worstLoading,
    error: worstError,
  } = useWorstSellers('days=30&limit=8');
  const {
    data: sizeData,
    loading: sizeLoading,
    error: sizeError,
  } = usePopularCakeSizes('days=30&limit=8');
  const {
    data: viewsData,
    loading: viewsLoading,
    error: viewsError,
  } = useProductPageViews('days=30&limit=8');

  if (bestLoading || worstLoading || sizeLoading || viewsLoading) {
    return <Skeleton height={520} />;
  }

  const hasApiFailure =
    bestData?.succeeded === false ||
    worstData?.succeeded === false ||
    sizeData?.succeeded === false ||
    viewsData?.succeeded === false;

  if (bestError || worstError || sizeError || viewsError || hasApiFailure) {
    return (
      <ErrorAlert
        title="Error loading product analytics"
        message={
          bestData?.message ||
          worstData?.message ||
          sizeData?.message ||
          viewsData?.message ||
          'Could not load one or more product datasets.'
        }
      />
    );
  }

  const bestRows: RankedRow[] = (bestData?.data || []).map((item) => ({
    id: item.product_id,
    label: item.product_name,
    value: Number(item.total_revenue || 0),
    badge: `Sold ${formatNumber(item.total_quantity_sold)}`,
    meta: item.category,
  }));

  const visitedRows: RankedRow[] = (viewsData?.data || []).map((item) => ({
    id: `${item.product_slug}-${item.page_url}`,
    label: prettifySlug(item.product_slug),
    value: Number(item.visits || 0),
    meta: item.page_url,
  }));

  const worstRows: RankedRow[] = (worstData?.data || []).map((item) => ({
    id: `worst-${item.product_id}`,
    label: item.product_name,
    value: Number(item.total_quantity_sold || 0),
    meta: `Revenue ${formatCurrency(Number(item.total_revenue || 0))}`,
  }));

  const cakeSizeRows: RankedRow[] = (sizeData?.data || []).map((item) => ({
    id: `size-${item.variant_name}`,
    label: item.variant_name,
    value: Number(item.total_quantity_sold || 0),
    meta: `Revenue ${formatCurrency(Number(item.total_revenue || 0))}`,
  }));

  return (
    <Grid>
      <Grid.Col span={{ base: 12, lg: 7 }}>
        <RankedProgressList
          title="Best Selling Products by Revenue"
          subtitle="Last 30 days. Bars compare product revenue contribution."
          color="indigo"
          rows={bestRows}
          emptyText="No best-seller data available."
          valueFormatter={formatCurrency}
        />
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 5 }}>
        <RankedProgressList
          title="Most Visited Product Pages"
          subtitle="Real page-view tracking from frontend traffic events."
          color="teal"
          rows={visitedRows}
          emptyText="No product page visits tracked yet."
        />
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 6 }}>
        <RankedProgressList
          title="Lowest Selling Products"
          subtitle="Products with the smallest unit sales in the last 30 days."
          color="red"
          rows={worstRows}
          emptyText="No worst-seller data available."
        />
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 6 }}>
        <RankedProgressList
          title="Most Requested Cake Sizes"
          subtitle="Cake size demand ranked by quantity sold."
          color="cyan"
          rows={cakeSizeRows}
          emptyText="No cake-size analytics available."
        />
      </Grid.Col>
    </Grid>
  );
}

export default function Page() {
  return (
    <>
      <>
        <title>Product & Traffic Analytics | Kabul Sweets</title>
        <meta
          name="description"
          content="Product performance, frontend visits, and checkout abandonment analytics."
        />
      </>
      <Container fluid>
        <Stack gap="lg">
          <PageHeader title="Product & Traffic Analytics" withActions={true} />
          <TrafficOverviewCards />
          <TrafficAndCheckoutCharts />
          <ProductPerformanceCharts />
        </Stack>
      </Container>
    </>
  );
}
