# Deploy on a PaaS (Railway / Render)

This guide runs the full application — FastAPI, the web console, MySQL and
automatic HTTPS — on a Platform-as-a-Service provider, with no server
administration.

The application **requires MySQL 8** in production (`app/core/config.py`), so
PostgreSQL-only free tiers cannot run it unchanged. Both options below provide
or connect to MySQL.

| | Railway (recommended) | Render |
|---|---|---|
| Cost | Hobby plan, ~$5/month | $7/month (`starter`) for 24/7 |
| MySQL | One-click MySQL service in the same project | **Not provided** — external MySQL needed |
| HTTPS | Automatic | Automatic |
| Always on | Yes | Only on paid plans (free sleeps ~15 min) |
| Setup time | ~10 minutes | ~20 minutes + database |
| Config in repo | `railway.toml` | `render.yaml` |

> For a **$0 always-on** deployment, use the Oracle Cloud VM instead:
> [`08-oracle-cloud-deployment.md`](08-oracle-cloud-deployment.md).

---

## 1. Railway (recommended)

### 1.1 Create the account

1. Go to <https://railway.com> and choose **Login with GitHub**.
2. Authorize Railway. The Hobby plan is $5/month of usage (a one-time trial
   credit is usually offered).

### 1.2 Create the project

1. **New Project → Deploy from GitHub repo**.
2. Grant Railway access to the repository if asked, then select
   `secure-license-inspection-tracking-api`.
3. Railway detects `railway.toml` and builds the `Dockerfile`.
4. The first deployment will probably stop with
   `ALLOWED_HOSTS must be restricted` — that is expected. Continue with the
   next steps, then redeploy.

### 1.3 Add MySQL

1. Open the project canvas and choose **+ New → Database → MySQL**.
2. Wait until the MySQL service is **Active**.
3. Keep the default service name `MySQL`. If you rename it, update the
   `${{MySQL.*}}` references below to match.

### 1.4 Generate the public domain

1. Open the **API service** (not MySQL).
2. **Settings → Networking → Public Networking → Generate Domain**.
3. Copy the domain, for example
   `license-inspection-api-production-1a2b.up.railway.app`.

The app rejects requests whose `Host` header is not in `ALLOWED_HOSTS`, so the
domain must exist before the app can start successfully.

### 1.5 Set the environment variables

Open the **API service → Variables → Raw Editor** and paste (replace the
password placeholders):

```text
ENVIRONMENT=production
SECRET_KEY=PASTE_OUTPUT_OF_openssl_rand_hex_32
DATABASE_URL=mysql+pymysql://${{MySQL.MYSQLUSER}}:${{MySQL.MYSQLPASSWORD}}@${{MySQL.MYSQLHOST}}:${{MySQL.MYSQLPORT}}/${{MySQL.MYSQLDATABASE}}
ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}
ALLOWED_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}}
ENABLE_HSTS=true
TRUST_PROXY_HEADERS=true
DOCS_ENABLED=false
ACCESS_TOKEN_EXPIRE_MINUTES=30
SEED_ON_START=true
SEED_ADMIN_PASSWORD=CHANGE_ME_ADMIN
SEED_INSPECTOR_PASSWORD=CHANGE_ME_INSPECTOR
SEED_VIEWER_PASSWORD=CHANGE_ME_VIEWER
```

Notes:

- Generate `SECRET_KEY` with `openssl rand -hex 32` (Git Bash / WSL / Linux).
- `${{...}}` is Railway's reference syntax. Keep it exactly as written.
- **Do not set `PORT`.** Railway injects it and `entrypoint.sh` uses it.
- If `${{RAILWAY_PUBLIC_DOMAIN}}` resolves to an empty value, paste the literal
  domain from step 1.4 instead.
- If a MySQL password contains `@`, `:` or `/`, percent-encode it.

### 1.6 Deploy and verify

1. **Deployments → Redeploy** (or push any commit).
2. Watch the logs. A healthy boot looks like:

   ```text
   Waiting for the database...
   Database is ready.
   Applying database migrations...
   Seeding demo data...
   Starting Regulatory License & Inspection Tracking API...
   Uvicorn running on http://0.0.0.0:<PORT>
   ```

3. Open:

   ```text
   https://YOUR_DOMAIN/health
   ```

   Expected: `{"status":"ok","database":"ok","version":"0.1.0"}`

4. Open `https://YOUR_DOMAIN`, sign in as `admin` with
   `SEED_ADMIN_PASSWORD`, then change the password in **My profile**.

### 1.7 Lock down seeding

In **Variables**, change:

```text
SEED_ON_START=false
```

Redeploy. The seed is idempotent, but it must not re-create demo users after
you delete them.

### 1.8 Custom domain (optional)

1. **Settings → Networking → Custom Domain**, add e.g. `api.example.com`.
2. Create the shown `CNAME` record at your DNS provider.
3. Add the hostname to the variables, keeping the Railway domain as well:

   ```text
   ALLOWED_HOSTS=api.example.com,${{RAILWAY_PUBLIC_DOMAIN}}
   ALLOWED_ORIGINS=https://api.example.com,https://${{RAILWAY_PUBLIC_DOMAIN}}
   ```

4. Redeploy.

### 1.9 Backups

1. MySQL service → **Settings → Networking → TCP Proxy** (enable it).
2. Copy `MYSQL_PUBLIC_URL` from the MySQL service variables.
3. From your machine, with a MySQL client installed:

   ```bash
   mysqldump -h PROXY_HOST -P PROXY_PORT -u root -p DATABASE_NAME > backup-$(date +%F).sql
   ```

Disable the TCP proxy again after the backup — it exposes the database to the
internet.

### 1.10 Updates

Every push to `main` redeploys automatically. The entrypoint re-runs
`alembic upgrade head` on each boot, so schema changes apply themselves.

---

## 2. Render (alternative)

Render runs the Docker image well, but **has no managed MySQL**. You must bring
an external MySQL 8 or MySQL-compatible database (for example a Railway MySQL
service with TCP proxy, a cheap managed MySQL, or TiDB Cloud Serverless — note
TiDB requires TLS parameters in `DATABASE_URL`).

1. Push this repository to GitHub (already done).
2. In <https://dashboard.render.com>: **New → Blueprint**, connect the repo.
3. Render reads `render.yaml` and asks for the `sync: false` values:
   - `DATABASE_URL` — `mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE`
   - `ALLOWED_HOSTS` — the service hostname, e.g.
     `license-inspection-api.onrender.com` (shown after creation)
   - `ALLOWED_ORIGINS` — `https://license-inspection-api.onrender.com`
   - `SEED_ON_START` — `true` for the first deploy
   - `SEED_ADMIN_PASSWORD`, `SEED_INSPECTOR_PASSWORD`, `SEED_VIEWER_PASSWORD`
4. Apply the blueprint and wait for the deploy.
5. Check `https://YOUR_SERVICE.onrender.com/health`.
6. Set `SEED_ON_START=false` in the dashboard and redeploy.
7. `plan: starter` keeps the service awake. On the **free** plan it sleeps after
   about 15 minutes without traffic, so it is not a 24/7 deployment.

If you prefer Render's free plan, keep a paid external MySQL and accept the
sleep, or switch to Railway.

---

## 3. Production checklist

- [ ] `ENVIRONMENT=production`
- [ ] `DATABASE_URL` starts with `mysql+pymysql://`
- [ ] `SECRET_KEY` is 32+ random hex characters
- [ ] `ALLOWED_HOSTS` is the real public hostname (not `*`)
- [ ] `ALLOWED_ORIGINS` is `https://` + the real hostname
- [ ] `SEED_ON_START=false` after the first boot
- [ ] Seeded passwords changed after the first sign-in
- [ ] Database backups enabled and copied off the provider
- [ ] Billing alert configured

---

## 4. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ALLOWED_HOSTS must be restricted` | Generate the public domain, then set `ALLOWED_HOSTS` to it and redeploy. |
| `production requires a MySQL DATABASE_URL` | `DATABASE_URL` is missing or does not start with `mysql+pymysql://`. |
| `400 Invalid host header` | The request host is not in `ALLOWED_HOSTS`; add the custom domain too. |
| `Can't connect to MySQL server` | MySQL is not in the same Railway project, or `${{MySQL.*}}` names are wrong. |
| `Access denied for user` | Wrong password, or the password needs percent-encoding. |
| App restarts forever, seed error | `SEED_ON_START=true` but a `SEED_*_PASSWORD` is empty. |
| Login fails, no users | Seeding never ran; set `SEED_ON_START=true` with passwords once. |
| Render service slow after idle | Free plan sleeps; upgrade to `starter`. |

---

## 5. Why not a static host?

GitHub Pages, Vercel, Netlify and Cloudflare Pages serve static files only.
They cannot run FastAPI, Alembic migrations or MySQL. This application serves
its console from the API itself, so it needs a container host.
