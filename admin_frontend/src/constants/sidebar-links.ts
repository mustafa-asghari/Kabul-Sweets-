import {
  IconCake,
  IconChartInfographic,
  IconPackage,
  IconPackages,
  IconPhoto,
  IconSettings,
  IconShoppingCart,
  IconUserCircle,
  IconUsers,
  IconListDetails,
} from '@tabler/icons-react';

import { PATH_APPS, PATH_DASHBOARD } from '@/routes';
import type { Permission } from '@/types/roles';

export interface SidebarLink {
  label: string;
  icon: any;
  link: string;
  requiredPermission?: Permission;
}

export interface SidebarSection {
  title: string;
  links: SidebarLink[];
}

export const SIDEBAR_LINKS: SidebarSection[] = [
  {
    title: 'Dashboard',
    links: [
      {
        label: 'Overview',
        icon: IconShoppingCart,
        link: PATH_DASHBOARD.ecommerce,
      },
      {
        label: 'Product & Traffic',
        icon: IconChartInfographic,
        link: PATH_DASHBOARD.analytics,
        requiredPermission: 'canViewAnalytics',
      },
    ],
  },
  {
    title: 'Store',
    links: [
      {
        label: 'Products',
        icon: IconPackages,
        link: PATH_APPS.products.root,
        requiredPermission: 'canManageProducts',
      },
      {
        label: 'Orders',
        icon: IconListDetails,
        link: PATH_APPS.orders,
        requiredPermission: 'canManageOrders',
      },
      {
        label: 'Custom Cakes',
        icon: IconCake,
        link: PATH_APPS.customCakes,
        requiredPermission: 'canManageOrders',
      },
      {
        label: 'Inventory',
        icon: IconPackage,
        link: PATH_APPS.inventory,
        requiredPermission: 'canManageProducts',
      },
    ],
  },
  {
    title: 'Users',
    links: [
      {
        label: 'User Management',
        icon: IconUsers,
        link: PATH_APPS.customers,
        requiredPermission: 'canManageUsers',
      },
    ],
  },
  {
    title: 'Media',
    links: [
      {
        label: 'Image Processing',
        icon: IconPhoto,
        link: PATH_APPS.images,
        requiredPermission: 'canManageProducts',
      },
    ],
  },
  {
    title: 'Account',
    links: [
      { label: 'Profile', icon: IconUserCircle, link: PATH_APPS.profile },
      {
        label: 'Settings',
        icon: IconSettings,
        link: PATH_APPS.settings,
        requiredPermission: 'canManageSettings',
      },
    ],
  },
];
