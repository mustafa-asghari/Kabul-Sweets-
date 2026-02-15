Ready to code?
                                                                                   
 Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Kabul Sweets Admin Dashboard — Backend Integration Plan

 Context

 The admin frontend (Next.js + Mantine) currently uses mock JSON data. The FastAPI
  backend at localhost:8000/api/v1 is ~90% complete with: JWT auth, products with
 variants, orders, Stripe payments, analytics, Celery workers, SMS/email, PDF
 receipts, custom cake approval flow, image processing, and cart recovery.

 Goal: Connect the admin dashboard to the real backend, add missing admin pages,
 remove irrelevant template features, and create a comprehensive test suite.

 ---
 Phase 1: Auth & API Infrastructure

 1.1 Environment config

 - Create .env.local with API_URL=http://localhost:8000/api/v1

 1.2 API client utility

 - Create src/lib/api-client.ts — server-side fetch helper used by all Next.js API
  routes
   - Reads JWT from httpOnly cookies, forwards Authorization: Bearer <token> to
 backend
   - Handles 401 by attempting refresh via stored refresh_token cookie
   - Wraps backend responses in IApiResponse<T> format

 1.3 Auth API routes

 - Create src/app/api/auth/login/route.ts — POST to backend /auth/login, set
 tokens as httpOnly cookies
 - Create src/app/api/auth/logout/route.ts — POST to backend /auth/logout, clear
 cookies
 - Create src/app/api/auth/refresh/route.ts — POST to backend /auth/refresh,
 update cookies
 - Create src/app/api/auth/me/route.ts — GET from backend /users/me

 1.4 Auth context & provider

 - Create src/contexts/auth/AuthContext.tsx — user, isAuthenticated, login(),
 logout(), refreshUser()
 - Modify src/providers/index.tsx — wrap with AuthProvider

 1.5 Update signin page

 - Modify src/app/auth/signin/page.tsx — real login against /api/auth/login,
 default credentials admin@kabulsweets.com.au / Admin@2024!

 1.6 Route protection middleware

 - Modify src/middleware.ts — check access_token cookie, redirect unauthenticated
 users to /auth/signin

 ---
 Phase 2: Types & Data Layer

 2.1 Rewrite types to match backend schemas

 - Rewrite src/types/products.ts — Product, ProductVariant, ProductCategory
 (string enum), ProductCreate, VariantCreate
 - Rewrite src/types/order.ts — Order, OrderItem, OrderPayment, OrderStatus
 (string enum:
 draft/pending/paid/confirmed/preparing/ready/completed/cancelled/refunded)
 - Rewrite src/types/user.ts — UserResponse matching backend (id, email,
 full_name, phone, role, is_active, is_verified, created_at, last_login)
 - Create src/types/analytics.ts — DashboardSummary, DailyRevenue, BestSeller,
 InventoryTurnover
 - Create src/types/custom-cake.ts — CustomCake, CustomCakeStatus
 - Delete obsolete types: src/types/invoice.ts, src/types/projects.ts,
 src/types/task.ts, src/types/chat.ts, src/types/email.ts,
 src/types/notification.ts

 2.2 Update API routes to proxy to backend

 Convert each route.ts from reading public/mocks/*.json to calling backend via
 api-client.ts:

 - Modify src/app/api/products/route.ts — GET proxies to /products/admin/all, POST
  proxies to /products/
 - Create src/app/api/products/[id]/route.ts — GET/PATCH/DELETE single product
 - Create src/app/api/products/[id]/variants/route.ts — POST variant
 - Create src/app/api/products/[id]/stock/route.ts — POST stock adjustment
 - Modify src/app/api/orders/route.ts — GET proxies to /orders/, POST proxies to
 /orders/
 - Create src/app/api/orders/[id]/route.ts — GET/PATCH single order
 - Modify src/app/api/customers/route.ts — GET proxies to /users/
 - Create src/app/api/analytics/dashboard/route.ts — GET proxies to
 /analytics/dashboard
 - Create src/app/api/analytics/revenue/route.ts — GET proxies to
 /analytics/revenue/daily
 - Create src/app/api/analytics/best-sellers/route.ts — GET proxies to
 /analytics/best-sellers
 - Create src/app/api/analytics/inventory/route.ts — GET proxies to
 /analytics/inventory-turnover
 - Create src/app/api/custom-cakes/route.ts — GET proxies to /ml/custom-cakes
 - Create src/app/api/custom-cakes/[id]/route.ts — PATCH (approve/reject)
 - Create src/app/api/images/route.ts — GET list, POST upload
 - Create src/app/api/images/[id]/route.ts — GET/POST process/choose

 2.3 Update API hooks

 - Modify src/lib/hooks/useApi.ts — update all hooks with new types:
 useProducts(), useOrders(), useUsers(), useDashboardSummary(), useDailyRevenue(),
  useBestSellers(), useCustomCakes(), plus apiPost, apiPatch, apiDelete mutation
 helpers

 ---
 Phase 3: Core Pages

 3.1 Products page

 - Modify src/app/apps/products/page.tsx — use ProductListItem type
 - Modify product card component — name (was title), base_price (was price),
 category (string not object), variant count, is_cake/is_featured badges
 - Modify NewProductDrawer — bakery fields: name, description, category
 (cake/pastry/cookie/bread/sweet/drink/other), base_price, is_cake, is_featured,
 variant creation (name, price, stock_quantity, serves)
 - Modify EditProductDrawer — same fields + variant management + stock adjustment

 3.2 Orders page

 - Modify src/app/apps/orders/page.tsx — use Order/OrderListItem type
 - Modify OrdersTable — columns: order_number, customer_name, status (string
 badges with bakery colors), total, has_cake badge, pickup_date, created_at
 - Modify EditOrderDrawer — admin can update: status, pickup_date,
 pickup_time_slot, admin_notes
 - Modify NewOrderDrawer — items with product/variant selectors, customer info,
 pickup scheduling

 3.3 Users page (was Customers)

 - Modify src/app/apps/customers/page.tsx — use UserResponse type, rename to
 "Users"
 - Modify CustomersTable — columns: full_name, email, phone, role badge, is_active
  badge, created_at, last_login
 - Modify create/edit drawers for user management (create with role,
 activate/deactivate)

 3.4 E-commerce Dashboard

 - Modify src/app/dashboard/ecommerce/page.tsx — fetch from real analytics
 endpoints
 - Modify stats grid — show: Revenue Today, Revenue This Week, Revenue This Month,
  Orders Today, Pending Orders, Preparing, Cake Orders, Low Stock Count, Total
 Customers
 - Modify revenue chart — daily revenue from /api/analytics/revenue
 - Modify top products table — best sellers from /api/analytics/best-sellers
 - Modify order status chart — aggregate real order statuses

 ---
 Phase 4: Missing Admin Pages

 4.1 Custom Cake Approval page

 - Create src/app/apps/custom-cakes/page.tsx — list custom cake submissions
 - Create src/components/custom-cakes/ — table with columns: customer_name, cake
 details (flavor, layers, size), decoration_complexity, predicted_price, status
 badge, actions
 - Approval flow: view details → adjust price → approve (generates Stripe payment
 link + emails customer) or reject (with reason)
 - Status badges: PENDING_REVIEW (yellow), APPROVED_AWAITING_PAYMENT (blue), PAID
 (green), IN_PRODUCTION (orange), COMPLETED (teal), REJECTED (red)

 4.2 Image Processing page

 - Create src/app/apps/images/page.tsx — image management
 - Features: upload images (drag & drop), assign to product, trigger AI
 processing, side-by-side preview (original vs processed), approve/reject
 processed image

 4.3 Inventory Management view

 - Create src/app/apps/inventory/page.tsx — stock overview
 - Table: product name, variant name, current_stock, low_stock_threshold, status
 (in stock/low/out), days_of_stock_remaining
 - Actions: quick stock adjustment (restock), filter by low stock
 - Data from /api/analytics/inventory

 4.4 Refund Management

 - Add refund action to order detail view
 - Trigger via /api/orders/[id]/refund → backend
 /payments/admin/orders/{id}/refund
 - Confirmation modal with amount input (full or partial) and reason

 ---
 Phase 5: Cleanup

 5.1 Remove irrelevant dashboard pages

 - Delete src/app/dashboard/crm/, finance/, marketing/, healthcare/, education/,
 logistics/, hr/, real-estate/, llm/, saas/, default/
 - Keep only: ecommerce/ (main dashboard), analytics/ (can repurpose for detailed
 analytics)

 5.2 Remove irrelevant app pages

 - Delete src/app/apps/invoices/, email/, chat/, calendar/, tasks/, projects/,
 file-manager/, notifications/
 - Keep: products/, orders/, customers/, profile/, settings/

 5.3 Remove irrelevant API routes

 - Delete all mock API routes for removed features: /api/chat/, /api/invoices/,
 /api/projects/, /api/tasks/, /api/emails/, /api/sales/, /api/traffic/,
 /api/stats/, /api/languages/, /api/profile/, /api/crm/, /api/finance/,
 /api/marketing/, /api/healthcare/, /api/education/, /api/logistics/, /api/hr/,
 /api/real-estate/, /api/llm/

 5.4 Clean up mock data

 - Delete all files in public/mocks/ (no longer needed)

 5.5 Update sidebar navigation

 - Modify src/constants/sidebar-links.ts:
   - Dashboard: Overview (ecommerce)
   - Store: Products, Orders, Custom Cakes, Inventory
   - Users: User Management
   - Media: Image Processing
   - Account: Profile, Settings

 5.6 Update routes

 - Modify src/routes/index.ts — remove paths for deleted pages, add paths for new
 pages (custom-cakes, inventory, images)

 5.7 Delete obsolete components

 - Remove components for: CRM dashboard, finance dashboard, marketing dashboard,
 healthcare, education, logistics, HR, real-estate, LLM, SaaS, invoices table,
 language table, etc.

 ---
 Phase 6: Comprehensive Test Suite

 6.1 Test infrastructure setup

 - Install testing dependencies: vitest, @testing-library/react,
 @testing-library/jest-dom, msw (Mock Service Worker for API mocking)
 - Create vitest.config.ts
 - Create src/test/setup.ts — test setup with MSW handlers
 - Create src/test/mocks/handlers.ts — MSW request handlers mimicking backend
 responses
 - Create src/test/mocks/server.ts — MSW server setup
 - Create src/test/fixtures/ — test data fixtures for products, orders, users,
 analytics

 6.2 API client tests

 - Create src/lib/__tests__/api-client.test.ts
   - Tests: successful fetch, 401 handling with auto-refresh, refresh failure →
 logout, error wrapping in IApiResponse

 6.3 Auth tests

 - Create src/contexts/auth/__tests__/AuthContext.test.tsx
   - Tests: login flow, logout flow, auto-refresh on mount, redirect on 401
 - Create src/app/api/auth/__tests__/login.test.ts
   - Tests: successful login sets cookies, invalid credentials returns error, rate
  limiting

 6.4 API route proxy tests

 - Create src/app/api/products/__tests__/route.test.ts
   - Tests: GET returns products from backend, POST creates product, auth header
 forwarded, error handling
 - Create src/app/api/orders/__tests__/route.test.ts
   - Tests: GET with status filter, PATCH order status, error handling
 - Create src/app/api/customers/__tests__/route.test.ts
   - Tests: GET returns users, role filtering

 6.5 Component tests

 - Create src/components/orders-table/__tests__/OrdersTable.test.tsx
   - Tests: renders order data, status badge colors, pagination, filtering,
 edit/view actions
 - Create src/components/customers-table/__tests__/CustomersTable.test.tsx
   - Tests: renders user data, role badges, active/inactive badges, sorting
 - Create src/app/apps/products/__tests__/page.test.tsx
   - Tests: product grid renders, loading state, error state, create new product
 flow
 - Create src/app/apps/custom-cakes/__tests__/page.test.tsx
   - Tests: cake list renders, approve flow, reject flow, status badges

 6.6 Page integration tests

 - Create src/app/dashboard/ecommerce/__tests__/page.test.tsx
   - Tests: stats grid shows real data, revenue chart renders, best sellers table,
  handles loading/error
 - Create src/app/apps/orders/__tests__/page.test.tsx
   - Tests: order list, filter by status, edit order status, refund action
 - Create src/app/apps/inventory/__tests__/page.test.tsx
   - Tests: inventory table, low stock highlight, stock adjustment

 6.7 End-to-end smoke test

 - Create src/test/e2e/smoke.test.ts
   - Tests: login → dashboard loads → navigate to products → navigate to orders →
 logout
   - Uses MSW to mock all backend calls

 6.8 Test npm scripts

 - Modify package.json — add scripts:
   - "test": "vitest run"
   - "test:watch": "vitest"
   - "test:coverage": "vitest run --coverage"

 ---
 Verification Plan

 1. Start backend: cd backend && docker-compose up -d db redis && uvicorn
 app.main:app --reload
 2. Seed database: python -m app.seed
 3. Start frontend: npm run dev
 4. Test auth: Login with admin@kabulsweets.com.au / Admin@2024! → should redirect
  to dashboard
 5. Test dashboard: E-commerce dashboard shows real stats from backend analytics
 6. Test products: Create a bakery product with variants, edit it, see it in the
 list
 7. Test orders: View orders, filter by status, update order status
 8. Test users: View user list, filter by role
 9. Test custom cakes: View custom cake submissions (if any exist in seeded data)
 10. Test inventory: View stock levels, perform stock adjustment
 11. Run test suite: npm test — all tests pass
 12. Build check: npm run build — production build succeeds with no errors
