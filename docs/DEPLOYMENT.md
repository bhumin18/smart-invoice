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
```

Configure allowed frontend origins in `backend/config.yaml` or with your host-specific environment setup.

## Backend: Render/Railway/VPS

Backend start command:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Health check:

```text
/api/health
```

For Render/Railway, set the service root to `backend` or use the Dockerfile in `backend/Dockerfile`.

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

## Security Checklist

- Rotate any token accidentally printed in logs or terminal output.
- Use HTTPS.
- Disable open registration unless you want public signups.
- Configure SMTP with an app password, not your real mailbox password.
- Keep `backend/database` and `backend/outputs` out of Git.
