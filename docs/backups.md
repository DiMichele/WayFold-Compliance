# Backups — WayFold Compliance

## Scope

| Component | Path (prod) | Included |
|---|---|---|
| Engine data (portfolio, evidence, audit, AI, regulatory, users) | `/home/wayfold/apps/wayfold-compliance/data/engine` | YES |
| GRC core DB | `/home/wayfold/apps/wayfold-compliance/data/db` | YES |
| Auth env / secrets | `data/engine/.auth.env` | NO (mai in backup documentali/versionati) |

## Frequency / retention (indicativi)

- Frequency: daily (cron host) + pre-deploy snapshot consigliato
- Retention: 14 giorni rolling
- Location: host-local `/home/wayfold/backups/wayfold-compliance/` (o object storage privato)
- Encryption: at-rest via volume/host disk encryption; backup tarball con umask 027

## Backup command (host)

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST=/home/wayfold/backups/wayfold-compliance/$STAMP
mkdir -p "$DEST"
tar -C /home/wayfold/apps/wayfold-compliance/data \
  --exclude='engine/.auth.env' \
  -czf "$DEST/data.tgz" engine db
```

## Restore (isolated — never destructive on live without freeze)

```bash
# 1) Fresh isolated directory / compose project
# 2) Extract
tar -C /path/to/isolated/data -xzf data.tgz
# 3) Start compose
# 4) Verify login → Michele → CTRL-IAM-001 → evidence download
```

## Last restore test

| Field | Value |
|---|---|
| Date | 2026-08-09 |
| Environment | Local isolated tempdir + unit/integration evidence restore paths |
| Result | PASS (engine stores round-trip via tests) |
| Live destructive restore | NOT EXECUTED (by policy) |

## RPO / RTO

- RPO indicativo: 24h (daily backup)
- RTO indicativo: 2–4h (restore + seed verification + smoke)

## Secrets

Non includere `.auth.env`, session secrets, API keys nei tarball versionati o nella documentazione.
