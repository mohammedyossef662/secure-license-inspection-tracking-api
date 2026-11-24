# Deploy 24/7 on Oracle Cloud Always Free

This guide runs the full application online, permanently:

- **Caddy** terminates HTTPS and obtains a free Let's Encrypt certificate.
- **FastAPI** runs in the Docker image and serves the web console at `/`.
- **MySQL 8** stores the data in a persistent Docker volume.
- Everything is `restart: unless-stopped`, so it comes back after reboots.

It uses Oracle Cloud's **Always Free** ARM VM, so the monthly cost is **$0**
within the Always Free limits. A card is required for identity verification.

---

## 1. Create the Always Free VM

1. Sign in to <https://cloud.oracle.com/> and choose a home region.
2. Open **Compute → Instances → Create instance**.
3. Use these settings:
   - **Name:** `license-inspection`
   - **Image:** Canonical Ubuntu 24.04 (or 22.04)
   - **Shape:** `VM.Standard.A1.Flex` (Ampere ARM)
   - **OCPUs / memory:** `1 OCPU / 6 GB` minimum (up to 4/24 GB is Always Free)
   - **Networking:** assign a **public IPv4 address**
   - **SSH keys:** upload your public key (or let Oracle generate one)
4. Create the instance and note its **public IP address**.

> If ARM capacity is unavailable, retry later or use a different availability
> domain. The `VM.Standard.E2.1.Micro` AMD shape is also Always Free, but 1 GB
> of RAM is tight for MySQL; prefer the ARM shape.

### Open ports 80 and 443

In the OCI console:

1. **Networking → Virtual Cloud Networks →** your VCN **→ Security Lists →**
   Default Security List.
2. Add **Ingress Rules**:
   - Source `0.0.0.0/0`, protocol **TCP**, destination port **80**
   - Source `0.0.0.0/0`, protocol **TCP**, destination port **443**

Port 22 is normally open already. If you use a Network Security Group instead,
add the same rules there.

---

## 2. Open the ports inside Ubuntu

Oracle's Ubuntu images ship with an iptables rule that blocks HTTP/HTTPS even
after the cloud firewall is opened. SSH in:

```bash
ssh -i /path/to/your-key ubuntu@YOUR_PUBLIC_IP
```

Then allow 80/443 **before** the REJECT rule:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

If `netfilter-persistent` is missing:

```bash
sudo apt-get update
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

Verify:

```bash
sudo iptables -L INPUT -n --line-numbers
```

---

## 3. Install Docker and get the code

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
docker --version

sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/mohammedyossef662/secure-license-inspection-tracking-api.git
cd secure-license-inspection-tracking-api
```

---

## 4. Configure production secrets

```bash
cp .env.production.example .env.production
openssl rand -hex 32          # copy the output into SECRET_KEY
nano .env.production
```

Set at least:

| Variable | Value |
|---|---|
| `SITE_ADDRESS` | `YOUR_PUBLIC_IP.sslip.io` (or `api.yourdomain.com`) |
| `SECRET_KEY` | output of `openssl rand -hex 32` |
| `MYSQL_ROOT_PASSWORD` | a strong unique password |
| `MYSQL_PASSWORD` | a strong unique password |
| `SEED_ADMIN_PASSWORD` | a strong admin password |
| `SEED_INSPECTOR_PASSWORD` | a strong inspector password |
| `SEED_VIEWER_PASSWORD` | a strong viewer password |

`SITE_ADDRESS` is a **hostname only** — no `https://`, no trailing slash.
If you do not own a domain, `sslip.io` gives you a public hostname that points
at your IP, for example:

```text
SITE_ADDRESS=license.203.0.113.10.sslip.io
```

Caddy will obtain a real TLS certificate for it automatically.

> `.env.production` is git-ignored. If a password contains `$`, write it as
> `$$` because Docker Compose interpolates `$` in env files.

---

## 5. Start the stack

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api
```

The first build takes a few minutes. When the API is healthy, Caddy obtains the
certificate (usually within 30 seconds). Open:

```text
https://YOUR_SITE_ADDRESS
```

Sign in with `admin` and the `SEED_ADMIN_PASSWORD` you configured.

### Disable seeding after the first boot

The seed is idempotent, but you should not re-create demo users after deleting
them. Edit `.env.production`:

```text
SEED_ON_START=false
```

Then apply:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

Change the admin password in **My profile** after the first sign-in.

---

## 6. Operations

### Check health

```bash
curl -fsS https://YOUR_SITE_ADDRESS/health
```

Expected:

```json
{"status":"ok","database":"ok","version":"0.1.0"}
```

### Logs

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f caddy
```

### Update the app

```bash
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

### Back up MySQL

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
  > backup-$(date +%F).sql
```

### Restore MySQL

```bash
cat backup-2026-11-24.sql | \
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
```

### Restart / stop

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml restart
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

`down` keeps the MySQL and Caddy volumes. Use `down -v` only if you intend to
delete the database and certificates.

---

## 7. Troubleshooting

| Symptom | Check |
|---|---|
| `502 Bad Gateway` | `docker compose ... logs api` — usually migrations or a bad `DATABASE_URL`. |
| Caddy cannot get a certificate | DNS must resolve to the VM IP; ports 80/443 must be open in both the OCI security list and Ubuntu iptables. |
| `ALLOWED_HOSTS must be restricted` | `SITE_ADDRESS` is unset or still `*` in `.env.production`. |
| Login fails after restart | JWT revocation is in memory; sign in again. |
| Port 3306 not reachable | Correct — the database is private to the Compose network. |
| Out of disk | `docker system prune -f` and check `df -h`. |

---

## 8. Security checklist

- [ ] `SITE_ADDRESS` is the real public hostname, not `*`.
- [ ] `SECRET_KEY` is 32+ random hex characters.
- [ ] MySQL root and app passwords are unique and strong.
- [ ] Seeded passwords were changed after the first login.
- [ ] `SEED_ON_START=false` after seeding.
- [ ] Only ports 22, 80 and 443 are open in OCI and Ubuntu.
- [ ] OCI budget alert configured (Always Free resources only).
- [ ] Backups copied off the VM regularly.
- [ ] OS updates applied: `sudo apt-get update && sudo apt-get upgrade -y`.

---

## 9. Why not GitHub Pages?

GitHub Pages serves static files only. It can host the `docs/` preview, but it
cannot run Python, MySQL, migrations, or the API. This VM runs the real
application and the same web console, with working sign-in and data.
