import { Badge, Group, PaperProps, Text, Title } from '@mantine/core';

import { Surface } from '@/components';
import { IProductCategory } from '@/types/products';

interface ProductCategoryCardProps extends Omit<PaperProps, 'children'> {
  data: IProductCategory;
}

export const CategoryCard = ({ data }: ProductCategoryCardProps) => {
  return (
    <Surface p="md">
      <Title order={4} mb="xs">
        {data.title}
      </Title>
      <Text size="sm" c="dimmed" mb="md" lineClamp={2}>
        {data.description || 'No description'}
      </Text>
      <Group>
        <Text size="sm">Products: {data.productCount}</Text>
        <Badge variant="light" color="indigo">
          System
        </Badge>
      </Group>
    </Surface>
  );
};
