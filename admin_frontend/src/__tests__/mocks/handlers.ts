import { http, HttpResponse } from 'msw';
import {
  mockProducts,
  mockOrders,
  mockUsers,
  mockDashboardSummary,
  mockDailyRevenue,
  mockBestSellers,
  mockInventory,
  mockCustomCakes,
  wrapApiResponse,
} from '../fixtures';

export const handlers = [
  // Auth
  http.post('/api/auth/login', async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.email === 'admin@kabulsweets.com.au' && body.password === 'Admin@2024!') {
      return HttpResponse.json({ succeeded: true, message: 'Login successful' });
    }
    return HttpResponse.json({ succeeded: false, message: 'Invalid credentials' }, { status: 401 });
  }),

  http.post('/api/auth/logout', () => {
    return HttpResponse.json({ succeeded: true });
  }),

  http.get('/api/auth/me', () => {
    return HttpResponse.json(
      wrapApiResponse({
        id: 'user-1',
        email: 'admin@kabulsweets.com.au',
        full_name: 'Admin User',
        phone: '+61400000000',
        role: 'admin',
        is_active: true,
        is_verified: true,
        created_at: '2024-01-01T00:00:00Z',
        last_login: '2025-01-30T08:00:00Z',
      })
    );
  }),

  // Products
  http.get('/api/products', () => {
    return HttpResponse.json(wrapApiResponse(mockProducts));
  }),

  http.post('/api/products', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(wrapApiResponse({ id: 'new-prod', ...body }), { status: 201 });
  }),

  // Orders
  http.get('/api/orders', () => {
    return HttpResponse.json(wrapApiResponse(mockOrders));
  }),

  // Customers
  http.get('/api/customers', () => {
    return HttpResponse.json(wrapApiResponse(mockUsers));
  }),

  // Analytics
  http.get('/api/analytics/dashboard', () => {
    return HttpResponse.json(wrapApiResponse(mockDashboardSummary));
  }),

  http.get('/api/analytics/revenue', () => {
    return HttpResponse.json(wrapApiResponse(mockDailyRevenue));
  }),

  http.get('/api/analytics/best-sellers', () => {
    return HttpResponse.json(wrapApiResponse(mockBestSellers));
  }),

  http.get('/api/analytics/inventory-turnover', () => {
    return HttpResponse.json(wrapApiResponse(mockInventory));
  }),

  // Custom Cakes
  http.get('/api/custom-cakes', () => {
    return HttpResponse.json(wrapApiResponse(mockCustomCakes));
  }),

  http.post('/api/custom-cakes/:id', async ({ request }) => {
    const body = (await request.json()) as { action: string };
    return HttpResponse.json(
      wrapApiResponse({ message: `Action ${body.action} completed` })
    );
  }),

  // Images
  http.get('/api/images', () => {
    return HttpResponse.json(wrapApiResponse([]));
  }),
];
