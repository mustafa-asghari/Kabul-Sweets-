# Fixing Notification Issues on Railway

You confirmed that email notifications work when running the test script (`python scripts/check_notifications.py`), but fail when approving an order in the application.

This happens because the test script sends the email **directly** (synchronously), while the application uses **Celery background tasks** (asynchronously) to send emails.

Currently, on Railway, your deployment likely only runs the **Web Service** (the API). The **Worker Service** (which processes background tasks like sending emails) is missing.

Here are two ways to fix this.

## Option 1: Deploy a Separate Worker Service (Recommended)

This is the proper way to handle background tasks for a production application.

1.  **Go to your Railway Dashboard**.
2.  **Add a New Service**: Click "New" -> "GitHub Repo" -> Select `Kabul-Sweets` again.
3.  **Configure the New Service**:
    *   Rename it to `celery-worker`.
    *   Go to **Settings** -> **Build & Deploy**.
    *   Change the **Start Command** to:
        ```bash
        celery -A app.celery_app:celery_app worker --loglevel=INFO --concurrency=4
        ```
    *   Ensure the **Variables** are set correctly. You can copy them from your main API service (especially `DATABASE_URL`, `REDIS_URL`, `MAILGUN_API_KEY`, etc.).
4.  **Deploy**: Once deployed, this worker will pick up tasks from Redis and execute them (sending emails).

## Option 2: Run Tasks Synchronously (Quick Fix)

If you don't want to pay for or manage a second service on Railway, you can tell the application to execute tasks immediately within the web request, instead of sending them to a worker.

**Note:** utilize this only if you have low traffic. Heavy tasks (like image processing) will slow down your API responses.

1.  **Go to your Railway Dashboard.**
2.  Select your existing API service.
3.  Go to **Variables**.
4.  Add or update the variable:
    ```
    CELERY_TASK_ALWAYS_EAGER=True
    ```
5.  **Redeploy**.

With this setting, when the API calls `.delay()`, the function will execute immediately in the same process, bypassing the need for a separate worker. This mimics the behavior of the test script.

## Option 3: Processfile Deployment

I have added a `Procfile` to the `backend/` directory. If Railway detects this, it might automatically offer to deploy the worker process if you configure your service type correctly. However, manually adding the second service (Option 1) is usually more reliable on Railway.
