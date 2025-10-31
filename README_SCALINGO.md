# NeroVesuviano Inventory — Scalingo Deploy

**Build date:** 2025-10-31 14:29

## 1) Deploy (no terminal)
1. Go to https://dashboard.scalingo.com → Create App → Python.
2. Upload the **contents** of this ZIP (or drag the entire folder).
3. In **Settings → Environment**, add variables (see `.env.scalingo.example`):
   - SECRET_KEY
   - ADMIN_EMAIL
   - ADMIN_PASSWORD
   - DATABASE_URL (default `sqlite:////data/inventory.db`)
4. Click **Deploy**.
5. Open the app URL and log in:
   - Email: admin@nerovesuviano.it
   - Password: NeroVesuvio.25

## 2) Custom domain
In **Domains → Add Domain** enter `app.nerovesuviano.it` and create the CNAME on Hostinger:
- Type: CNAME
- Name: app
- Target: (the CNAME shown by Scalingo)
- TTL: Auto

HTTPS is automatic.

## 3) Notes
- SQLite on `/data` is OK to start but not durable across restarts. For persistence, add PostgreSQL and set `DATABASE_URL` accordingly.
- Start command uses Gunicorn: `web: gunicorn app:app --workers=1 --threads=8 --timeout=120 --bind 0.0.0.0:$PORT`.
