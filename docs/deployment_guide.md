# Automatic Question Paper Difficulty Analyzer — Production Deployment & Operational Hardening Guide

---

## 1. Architecture Overview

In production, the platform executes as a containerized multi-tier service:

```
[ Client Browsers / Faculty Portal ]
                  │
                  ▼ (Port 80 / 443 HTTPS)
        [ Nginx Reverse Proxy ]
        • SSL Termination & Security Headers
        • Static Asset Caching & Gzip Compression
        • 25MB Body Size Limit (Exam Papers)
        • Extended 120s Timeouts for ML Inference
        ┌─────────┴─────────┐
        │ /api/             │ /
        ▼                   ▼
 [ FastAPI Backend ]  [ Next.js 16 Frontend ]
 • 4 Uvicorn Workers  • Node.js Standalone
 • PyMuPDF / docx     • React 19 UI
 • ML Engine v1.0.0   • Recharts & Icons
        │
        ▼
 [ Persistent Storage ]
 • SQLite / PostgreSQL
 • /app/backend/uploads
 • /app/backend/reports
```

---

## 2. Prerequisites

- **Docker Engine**: 24.0+
- **Docker Compose**: v2.20+
- **Host Hardware**: Minimum 4GB RAM (8GB recommended), 2+ vCPU cores, 20GB SSD.

---

## 3. Deployment Steps

### Step 1: Configure Environment Secrets

Copy the production environment template:
```bash
cp .env.production.example .env
```

Generate a cryptographically secure 64-character secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Assign this value to `SECRET_KEY` inside `.env`.

### Step 2: Build and Launch Containers

Run Docker Compose in detached mode:
```bash
docker compose up --build -d
```

### Step 3: Verify Container Health

Check service status and healthchecks:
```bash
docker compose ps
```
Both `backend` and `frontend` will display status `healthy`.

Verify backend diagnostic check:
```bash
curl -f http://localhost/api/v1/health
```

Expected response:
```json
{"status":"ok","database":"connected","models":{"blooms":"loaded","difficulty":"loaded"}}
```

---

## 4. Production Security Hardening

1. **Non-Root Runtime**: Both the backend (`appuser:appgroup` UID 1001) and frontend (`nextjs:nodejs` UID 1001) containers execute under dedicated unprivileged system users.
2. **Reverse Proxy Headers**: The Nginx configuration enforces:
   - `X-Frame-Options: DENY` (Clickjacking defense)
   - `X-Content-Type-Options: nosniff` (MIME sniffing defense)
   - `Referrer-Policy: strict-origin-when-cross-origin`
3. **Payload Sanitization**: Direct client uploads exceeding 25MB are intercepted at the Nginx edge before consuming backend compute or memory.
4. **Tenant Isolation**: Database queries enforce `owner_id` constraints across all mutative operations, preventing cross-faculty document inspection.

---

## 5. Automated Disaster Recovery & Backups

### Generating an Immediate Backup

Execute the backup script inside or outside the container:
```bash
python scripts/backup_database.py --db-path ./data/app.db --backup-dir ./data/backups --retention-days 30
```

Each backup produces:
1. `exam_analyzer_db_YYYYMMDD_HHMMSSZ.sqlite.gz`: Gzip-compressed archive.
2. `exam_analyzer_db_YYYYMMDD_HHMMSSZ.sqlite.gz.sha256`: Cryptographic verification hash.

### Scheduling Daily Automated Backups

#### Linux (Cron)
Add to crontab (`crontab -e`):
```cron
0 2 * * * cd /opt/exam-analyzer && /usr/bin/python3 scripts/backup_database.py >> /var/log/exam_analyzer_backup.log 2>&1
```

#### Windows (Task Scheduler)
Create a daily scheduled task executing:
```powershell
powershell -Command "python C:\path\to\scripts\backup_database.py"
```

### Restoring from a Backup

To restore a specific backup with cryptographic SHA-256 validation:
```bash
python scripts/restore_database.py ./data/backups/exam_analyzer_db_20261013_000000Z.sqlite.gz
```
The restoration tool creates a `.pre_restore.bak` snapshot of the active database before completing the restore.
