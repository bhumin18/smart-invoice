# Deployment Guide

This project can run locally with Docker or be split into a hosted Flask API and a hosted React frontend.

## Required Production Settings

Set these values before exposing the app publicly:

```text
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=<long-random-secret>
ADMIN_PASSWORD=<strong-password>
AUTH_ALLOW_REGISTRATION=false
CORS_ALLOW_ALL=false
MAX_UPLOAD_MB=10
LOGIN_MAX_ATTEMPTS=5
LOGIN_LOCK_MINUTES=15
RATE_LIMIT_MAX_REQUESTS=30
```

Configure allowed frontend origins in `backend/config.yaml` or with your host-specific environment setup.

## Backend: Render/Railway/VPS

Backend start command:

```bash
cd backend
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:$PORT
```

Health check:

```text
/api/health
```

For Render/Railway, set the service root to `backend` or use the Dockerfile in `backend/Dockerfile`.
`render.yaml` is included as a starter backend service definition.

## Frontend: Vercel/Netlify

Frontend build command:

```bash
cd frontend/gst-gem-main
npm ci
npm run build
```

Set:

```text
VITE_API_BASE=https://your-backend-domain.com/api
```

Starter `vercel.json` and `netlify.toml` files are included in `frontend/gst-gem-main/`.

## Docker

```bash
docker compose up --build
```

Backend: `http://localhost:5000`

Frontend: `http://localhost:3000`

## Database

SQLite is the active adapter today. Keep the SQLite database on persistent disk if deployed.

For hosted multi-user production, migrate the repository layer to SQLAlchemy/PostgreSQL using:

```text
backend/database/sqlalchemy_adapter.py
backend/database/MIGRATION.md
```

## Scheduler

The backend includes an APScheduler hook for recurring invoices and payment reminders.
Enable it only on one backend instance:

```text
SCHEDULER_ENABLED=true
SCHEDULER_DAILY_HOUR=9
SCHEDULER_DAILY_MINUTE=0
```

For multi-instance production deployments, move scheduled jobs to a single worker
process or a managed cron service so jobs do not run twice.

## File Storage

Local upload storage is the default and works for a single server with persistent disk.
For hosted production, configure S3/R2-compatible storage values and serve files through
signed URLs:

```text
storage.provider=s3
storage.s3_bucket=<bucket>
storage.s3_endpoint_url=<optional-r2-endpoint>
```

## Security Checklist

- Rotate any token accidentally printed in logs or terminal output.
- Use HTTPS.
- Disable open registration unless you want public signups.
- Configure SMTP with an app password, not your real mailbox password.
- Keep `backend/database` and `backend/outputs` out of Git.
