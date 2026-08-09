# Backups — WayFold Compliance

## Scope

| Component | Path (prod) | Included |
|---|---|---|
| Engine data (portfolio, evidence, audit, AI, regulatory, users) | `/home/wayfold/apps/wayfold-compliance/data/engine` | YES |
| GRC core DB | `/home/wayfold/apps/wayfold-compliance/data/db` | YES |
| Auth env / secrets | `data/engine/.auth.env` | NO (mai in backup documentali/versionati) |

## Status (truthful)

| Capability | Status |
|---|---|
| Documented procedure | PASS |
| Host cron daily scheduled | NOT IMPLEMENTED (manual/host ops required) |
| Off-host private encrypted copy | NOT IMPLEMENTED |
| Backup job monitoring (last_success/size/checksum/failure) | NOT IMPLEMENTED |
| Isolated restore drill (production-like) | PARTIAL (local store round-trip tests only) |
| Live destructive restore | NOT EXECUTED (by policy) |

**Do not claim backup PASS for REAL CLIENT DATA until scheduled + off-host + restore drill evidence exist.**

## Frequency / retention (target)

- Frequency: daily (cron host) + pre-deploy snapshot
- Retention: 14 giorni rolling
- Location: host-local `/home/wayfold/backups/wayfold-compliance/` **and** off-host private encrypted copy
- Encryption: at-rest + tarball umask 027

## Backup command (host)

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST=/home/wayfold/backups/wayfold-compliance/$STAMP
mkdir -p "$DEST"
tar -C /home/wayfold/apps/wayfold-compliance/data \
  --exclude='engine/.auth.env' \
  -czf "$DEST/data.tgz" engine db
sha256sum "$DEST/data.tgz" > "$DEST/data.tgz.sha256"
printf '%s\n' "$STAMP" > /home/wayfold/backups/wayfold-compliance/last_success
```

## Restore (isolated — never destructive on live without freeze)

```bash
# 1) Fresh isolated directory / compose project
# 2) Extract
tar -C /path/to/isolated/data -xzf data.tgz
# 3) Start compose
# 4) Verify login → Michele → CTRL-IAM-001 → evidence download → report snapshot
```

## Last restore test

| Field | Value |
|---|---|
| Date | 2026-08-09 |
| Environment | Local isolated tempdir + unit/integration evidence restore paths |
| Result | PARTIAL (engine stores round-trip via tests) |
| Live destructive restore | NOT EXECUTED (by policy) |

## RPO / RTO (indicative, after scheduling)

- RPO: 24h  
- RTO: 2–4h  

## Secrets

Non includere `.auth.env`, session secrets, API keys nei tarball versionati o nella documentazione.
