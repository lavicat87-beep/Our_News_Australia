# Deploy Our News Australia (Render + Crazy Domains)

This guide deploys the Flask app from this repository and connects your Crazy Domains domain.

## 1. Create services on Render

1. Sign in to Render.
2. Create a PostgreSQL database (optional but recommended for production).
3. Create a new Web Service from your GitHub repo:
   - Repo: `lavicat87-beep/Our_News_Australia`
   - Branch: `main`
   - Runtime: `Python`

## 2. Render build/start commands

Use these values in Render Web Service settings:

- Build Command:

```bash
pip install -r requirements.txt
```

- Start Command:

```bash
gunicorn app:app
```

## 3. Environment variables

Add these in Render -> Environment:

- `SECRET_KEY` = a strong random string
- `ADMIN_USERNAME` = your admin username
- `ADMIN_PASSWORD` = your admin password
- `DATABASE_URL` = Render PostgreSQL URL (or your own PostgreSQL URL)

For PostgreSQL URL, this app supports SQLAlchemy format through `DATABASE_URL`.

## 4. Initialize database

This app now auto-bootstraps database tables, starter content, and admin user on first run using your environment variables.

If Shell is available, you can still run this manually:

```bash
flask --app app init-db
```

## 5. Add your custom domain in Render

1. Open your Render Web Service -> Settings -> Custom Domains.
2. Add both:
   - `yourdomain.com`
   - `www.yourdomain.com`
3. Render will show DNS records required.

## 6. Configure DNS in Crazy Domains

In Crazy Domains:

1. Go to Domain -> DNS Management.
2. Add exactly what Render asks for (common setup below):
   - `CNAME` for `www` -> Render target hostname
   - `A` record for `@` -> Render provided IP (or ALIAS/ANAME if instructed)
3. Remove old conflicting records for `@` and `www`.

## 7. Wait for propagation and SSL

- DNS can take from minutes up to 24-48 hours.
- Render auto-issues SSL when DNS is correct.
- Confirm both URLs work:
  - `https://yourdomain.com`
  - `https://www.yourdomain.com`

## 8. Set canonical domain

In Render, choose one canonical domain and redirect the other.
Example: redirect `www` -> root, or root -> `www`.

## 9. Quick troubleshooting

- If site shows 502/503:
  - Check Render logs for startup errors.
  - Verify `gunicorn app:app` start command.
- If database errors:
  - Check `DATABASE_URL` is set and valid.
  - Re-run `flask --app app init-db`.
- If domain not working:
  - Re-check DNS record names/values in Crazy Domains.
  - Confirm no duplicate or conflicting A/CNAME records.

## 10. Optional production polish

- Add monitoring/alerts in Render.
- Set admin password to a strong unique value.
- Use regular database backups.
- Add `robots.txt` and sitemap for SEO.
