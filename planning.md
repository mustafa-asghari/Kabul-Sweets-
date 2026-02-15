`PHASE 1 — Core Foundation (Infrastructure Setup)
Goal:

Set up a secure, production-ready backend skeleton.

What you build:

FastAPI project structure

PostgreSQL connection

Redis connection

Environment configuration system

Docker setup

Logging system

Health check endpoint

Alembic migrations

Deliverable:

A running backend connected to Postgres and Redis with migrations working.

No business logic yet. Just solid foundation.

🟢 PHASE 2 — Authentication & Role System
Goal:

Secure your system properly before adding features.

What you build:

User model

Password hashing (Argon2 or bcrypt)

JWT authentication

Refresh token system

Role-based access control (admin vs customer)

Admin-only route protection

Login rate limiting (Redis)

Basic audit logging for admin actions

Deliverable:

Secure login system with protected admin endpoints.

Security first.

🟢 PHASE 3 — Product & Inventory System
Goal:

Make products manageable and stock-controlled.

What you build:

Product model

Product variants (cake sizes)

Inventory tracking

Stock adjustment system

Mark out of stock

Limit per order

Product CRUD (admin only)

Image storage integration (S3)

Deliverable:

Admin can create, edit, delete products.
Inventory is tracked and logged.

This is your business engine.

🟢 PHASE 4 — Order System (Without Payment)
Goal:

Create full order lifecycle before integrating Stripe.

What you build:

Order model

Order items

Order status system

Pickup time system

Cake custom message field

Order validation logic

Inventory reservation logic

Admin order view

Order filtering

Deliverable:

Orders can be created and tracked.
Inventory reduces on order confirmation (temporary logic).

Still no real payment.

🟢 PHASE 5 — Stripe Payment Integration
Goal:

Make payments real and secure.

What you build:

Stripe Checkout session creation

Payment intent tracking

Stripe webhook endpoint

Webhook signature verification

Order status change only via webhook

Payment record storage

Failed payment handling

Deliverable:

Orders only become “paid” after Stripe confirms.

This locks in revenue safely.

🟢 PHASE 6 — Background Workers (Celery + Redis)
Goal:

Make system asynchronous and scalable.

What you build:

Celery worker setup

Redis queue configuration

Background email sending

Background SMS sending

Retry logic for failures

Logging of task outcomes

Deliverable:

Emails and SMS are processed in background.
API stays fast.

🟢 PHASE 7 — Cake Order Alert System
Goal:

Instant notification to admin for cake orders.

What you build:

Cake detection logic in paid orders

SMS formatting

Twilio integration

Real-time Redis pub/sub for admin dashboard

Admin cake-only order filter

Deliverable:

Every cake order sends immediate SMS to admin phone.

No missed cake orders.

🟢 PHASE 8 — Analytics Engine
Goal:

Make the backend intelligent.

What you build:

Analytics event tracking system

Event recording endpoints

Revenue tracking aggregation

Best sellers query logic

Low sellers query logic

Daily revenue aggregation job

Popular cake size tracking

Inventory turnover reporting

Deliverable:

Admin dashboard gets real metrics.

Business intelligence unlocked.

🟢 PHASE 9 — AI + RAG System
Goal:

Add intelligent product guidance.

What you build:

Embedding generation for products

Vector database integration

Product + FAQ indexing

AI query endpoint

Retrieval pipeline

Strict prompt design (no hallucinations)

Rate limiting for AI endpoint

AI query logging

Deliverable:

Customers can ask natural-language questions.
AI answers using real product data.

Smart bakery.

🟢 PHASE 10 — Performance & Caching Layer
Goal:

Optimize speed and scalability.

What you build:

Product page caching

Homepage popular items caching

Cache invalidation on product update

Rate limiting for public endpoints

Query optimization

Database indexing strategy

Deliverable:

Fast response times under load.

🟢 PHASE 11 — Advanced Security Hardening
Goal:

Make system production-grade secure.

What you implement:

Admin 2FA

IP throttling

Admin audit logs

CSRF protection (if cookies)

Content Security Policy headers

Strict CORS config

File upload validation

WAF (Cloudflare/AWS)

Secret manager integration

Encrypted backups

Deliverable:

System hardened against:

SQL injection

Brute force attacks

Webhook spoofing

DDoS attempts

Unauthorized admin access

🟢 PHASE 12 — Reliability & Monitoring
Goal:

Make sure nothing silently breaks.

What you build:

Health checks

Structured logging

Sentry error monitoring

Failed task alerts

Database backup automation

Webhook failure alerts

SMS failure fallback

Retry strategies

Deliverable:

System self-monitors and alerts you.

🟢 PHASE 13 — Optimization & Business Enhancements
Goal:

Polish and scale.

What you add:

Deposit payments for cakes

Order scheduling capacity limits

Low stock auto-alerts

Discount codes

Loyalty system foundation

POS sync endpoint

Exportable sales reports

Deliverable:

Enterprise-level backend.


High-impact, low-effort (quick wins)

Abandoned-cart recovery — recapture lost sales.
Backend: track cart events, queue email/SMS reminders via Celery with delay rules and templates.

Automated receipts + tax-friendly PDFs — better UX and accounting.
Backend: generate receipt PDFs (HTML→PDF) and store links in order record.

Basic A/B testing for product pages — increase conversions.
Backend: flag assignment logic, event tracking, store variant results in analytics_events.

Promotions & coupon engine — drives sales & offers control.
Backend: coupon table, validation logic, stacking rules, usage limits.

Customer experience & product discovery

Personalized recommendations — cross-sell and increase AOV.
Backend: use simple collaborative filtering or embed-based similarity; serve with cached recommendations.

Product filters + facets (diet/allergy tags) — reduce returns and confusion.
Backend: ensure metadata JSONB supports tags (halal, gluten-free, nut-free) and index them for fast queries.

Size & yield estimator for cakes — "How many serves?" calculator.
Backend: store yield metadata per variant and expose endpoint to compute servings.


Abandoned-cart recovery

What: Detect carts that never converted and nudge customers via email/SMS to complete checkout.

Backend: store carts + cart_events table; Celery scheduled tasks that run rules (e.g. 1h / 24h after last activity) → send templated email or SMS. Track tries and outcomes in cart_recovery_attempts.

Phase: 6 (Background Workers) + early in Phase 8 (Analytics) for tracking effectiveness.

Notes: Ensure opt-in for marketing (consent). Use idempotency so reminders aren’t sent multiple times. Track opens & clicks.

) Automated receipts + tax-friendly PDFs

What: Generate downloadable/emailed tax-friendly receipt PDFs for every paid order.

Backend: add PDF generation service (HTML → PDF via wkhtmltopdf or headless Chrome), store file on S3, add receipt_url on payments or orders. Celery task to generate & email after webhook confirms payment.

Phase: 6 (Background Workers) immediately after Phase 5 (Payments).

Notes: Include GST/tax breakdown fields in orders. Sign PDFs or timestamp for audit. Retain according to legal retention rules.


4) Promotions & coupon engine

What: Coupons, promo codes, percentage/amount off, usage limits and expiry.

Backend: coupons table (type, amount, constraints), coupon_redemptions log, validation service at checkout, admin CRUD endpoints. Apply coupon in price calculation and persist on order.

Phase: Phase 3–5 (Products → Orders → Payments) — implement before Payments so coupons can affect Stripe amounts.

Notes: Prevent stacking abuses; validate usage atomically (use DB transaction / optimistic lock). Store coupon audit log.


Personalized recommendations

What: Show cross-sells and recommended items tailored per user.

Backend: recommendations service — simple collaborative filtering from analytics_events or embedding similarity. Endpoint /recommendations?user_id= and cache per-user in Redis.

Phase: Phase 8–9 (Analytics → AI/RAG). Start with simple rules (also-bought) then move to embeddings.

Notes: Cold-start for new users, privacy for personalized content, measure CTR and AOV uplift.

Conversational upsell flows

What: AI proposes combos / add-ons during chat (e.g., “Add cookies with that cake for $5”).

Backend: extend AI RAG pipeline with business rules that create suggested cart_action objects and promo codes; endpoint to apply suggestion to cart.

Phase: Phase 9 (AI). Start simple rule-based offers before LLM-driven upsells.

Notes: Avoid aggressive upselling UX. Track acceptance rates.

AI-driven trend detection

What: Automatically surface which items are rising or falling in popularity and why (from reviews/social).

Backend: periodic NLP jobs that analyze analytics_events + reviews, output trend_insights table for admin dashboard. Use embeddings + clustering to surface themes.

Phase: Mid-term (Phase 8–9).

Notes: Define thresholds to avoid noise. Cache generated insights.

Loyalty & referral program

What: Reward repeat customers and new-referred customers with points or vouchers.

Backend: loyalty_accounts, points_ledger, referral codes table, redemption endpoints, admin management. Integrate with checkout so points used reduce Stripe amount.

Phase: Phase 13 (Business Enhancements) or mid-term.

Notes: Prevent fraud; establish expiry rules and reconciliation.



Distributed tracing (OpenTelemetry)

What: Trace requests across API, DB, background tasks to find latency.

Backend: instrument FastAPI, DB client, Celery tasks, and integrate with Jaeger/Tempo.

Phase: Mid-term (Phase 11–12). Start before heavy scaling.

Notes: Avoid logging PII in traces. Sample traces for cost control.

Secrets & key rotation automation

What: Manage and rotate API keys and secrets programmatically.

Backend: use Secrets Manager and CI jobs to rotate keys; implement secret fetch in app via secure SDK.

Phase: Phase 11 (Security Hardening).

Notes: Keep old secrets valid for short overlap during rollouts. Don’t store secrets in env files.

Chargeback & refund workflow

What: Manage refunds and chargeback disputes with logs and operator approval.

Backend: refund_requests state machine, Stripe refund API integration, admin approval endpoints, logs for disputes.

Phase: Phase 11–12 (Security & Reliability).

Notes: Keep evidence archive (order, receipt, communications) to contest chargebacks. this one must be done with the admins approval 



🔹 PHASE 1 — ML-Based Cake Price Prediction (Admin + Custom Cakes)
🎯 Goal

Automatically predict cake price per size when:

Admin adds a cake

Customer submits a custom cake

What To Build
1️⃣ Pricing Model System (ML, not LLM)

Use:


 XGBoost

Model predicts:

Price per size

Margin suggestion

2️⃣ Feature Engineering Layer

Collect structured data:

Diameter

Height

Layers

Ingredients cost

Decoration complexity

Labor hours

Rush order flag

Historical similar cake prices

3️⃣ Admin Cake Creation Flow Upgrade

When admin adds a cake:

Model suggests price per size

Admin can override

System logs predicted vs final price

4️⃣ Custom Cake Pricing

When customer submits custom cake:

Model predicts price

Stored as predicted_price

Admin must approve before customer can pay

5️⃣ Continuous Learning

Weekly:

Retrain model on approved cakes

Store model version

Track accuracy

🔹 PHASE 2 — Serving Size Prediction Model
🎯 Goal

Predict how many people a cake feeds automatically.

What To Build
1️⃣ Serving Estimation Engine

Predict:

Number of servings per size

Based on dimensions + density + shape

Start with:

Mathematical formula

Upgrade later to:

ML regression model

2️⃣ Integration Points

When:

Admin creates cake → suggest serving count

Customer submits custom cake → auto-calculate serves

Admin can override.

🔹 PHASE 3 — LLM for Description Generation
🎯 Goal

Automatically generate:

Short description

Long marketing description

SEO meta description

What To Build
1️⃣ Cake Description AI Service

Input:

Flavor

Ingredients

Decoration style

Event type

Tone (luxury, fun, elegant)

Output:

Marketing-ready text

2️⃣ Admin Workflow

When cake is added:

LLM generates description draft

Admin can edit before publishing

3️⃣ Custom Cake Draft

For custom cakes:

Generate provisional description for internal use

🔹 PHASE 4 — AI Image Processing (Background Removal)
🎯 Goal

Automatically clean cake images before publishing.

What To Build
1️⃣ Image Processing Pipeline

When image uploaded:

Send to background removal service

Remove background

Return transparent PNG

Store cleaned version

2️⃣ Async Processing

This runs in background worker.

3️⃣ Admin Preview

Admin sees:

Original image

Cleaned image

Can choose which to keep

🔹 PHASE 5 — Custom Cake Approval & Payment Flow
🎯 Goal

Admin approves cake → Customer receives secure payment link.

1️⃣ Submission Flow

Customer submits →
Status: PENDING_REVIEW

Send email:

“We received your request”

Order number included

2️⃣ Admin Approval

Admin:

Adjusts price

Confirms serving size

Approves or rejects

If Approved:
Status → APPROVED_AWAITING_PAYMENT

System:

Generate Stripe checkout link

Set expiration time (optional)

Send email:

Final price

Serves count

Payment link

Order number

Instructions

UI:

Mark cake as APPROVED

Show “Awaiting Payment”

3️⃣ Payment

Customer pays →
Stripe webhook →
Status → PAID

System:

Send receipt

Notify kitchen

Move to production queue

4️⃣ If Rejected

Status → REJECTED

Email sent with:

Reason

Optional modification request

🔹 PHASE 6 — Model Feedback & Intelligence Loop
🎯 Goal

Make system smarter over time.

What To Build
1️⃣ Prediction Logging

Store:

Predicted price

Final approved price

Difference

Model version

2️⃣ Accuracy Monitoring

Track:

Average prediction error

Per-size accuracy

Overpricing/underpricing patterns

3️⃣ Periodic Retraining

Automated scheduled job:

Pull new training data

Retrain model

Deploy new version`