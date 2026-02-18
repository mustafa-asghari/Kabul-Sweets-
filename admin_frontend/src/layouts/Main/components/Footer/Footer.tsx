import {
  Group,
  Text,
} from '@mantine/core';

const FooterNav = () => {
  return (
    <Group justify="space-between">
      <Group gap={16}>
        <Text size="sm" c="dimmed">
          Orders
        </Text>
        <Text size="sm" c="dimmed">
          Products
        </Text>
        <Text size="sm" c="dimmed">
          Customers
        </Text>
        <Text size="sm" c="dimmed">
          Analytics
        </Text>
      </Group>
      <Text c="dimmed">
        &copy;&nbsp;{new Date().getFullYear()}&nbsp;Kabul Sweets Admin
      </Text>
    </Group>
  );
};

export default FooterNav;
