function path(root: string, sublink: string) {
  return `${root}${sublink}`;
}

const ROOTS_DASHBOARD = '/dashboard';
const ROOT_APPS = '/apps';
const ROOTS_AUTH = '/auth';

export const PATH_DASHBOARD = {
  root: ROOTS_DASHBOARD,
  default: path(ROOTS_DASHBOARD, '/ecommerce'),
  ecommerce: path(ROOTS_DASHBOARD, '/ecommerce'),
  analytics: path(ROOTS_DASHBOARD, '/analytics'),
  saas: path(ROOTS_DASHBOARD, '/analytics'),
};

export const PATH_APPS = {
  root: ROOT_APPS,
  orders: path(ROOT_APPS, '/orders'),
  customers: path(ROOT_APPS, '/customers'),
  products: {
    root: path(ROOT_APPS, '/products'),
  },
  customCakes: path(ROOT_APPS, '/custom-cakes'),
  inventory: path(ROOT_APPS, '/inventory'),
  images: path(ROOT_APPS, '/images'),
  profile: path(ROOT_APPS, '/profile'),
  settings: path(ROOT_APPS, '/settings'),
};

export const PATH_AUTH = {
  root: ROOTS_AUTH,
  signin: path(ROOTS_AUTH, '/signin'),
  signup: path(ROOTS_AUTH, '/signup'),
  passwordReset: path(ROOTS_AUTH, '/password-reset'),
};

export const PATH_DOCS = {
  root: 'https://github.com/design-sparx/mantine-analytics-dashboard#readme',
};

export const PATH_GITHUB = {
  repo: 'https://github.com/design-sparx/mantine-analytics-dashboard',
};
