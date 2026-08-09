# Deployment — WayFold Compliance

## Live

```text
https://compliance.wayfold.xyz/
```

## Deploy (Windows → VPS)

```powershell
cd apps/wayfold-compliance
powershell -ExecutionPolicy Bypass -File deploy/deploy-compliance.ps1
```

Script: sync codice su host `wayfold@167.233.121.159`, path `/home/wayfold/apps/wayfold-compliance`, poi `deploy/update-remote.sh`.

## Compose

`deploy/docker-compose.prod.yml`

- GRC core (substrate) su `127.0.0.1:18000`
- Engine prodotto su `127.0.0.1:18092`
- Nginx TLS: `deploy/nginx-compliance.conf`

## Env critici (volume, non git)

`data/engine/.auth.env`:

- `WAYFOLD_AUTH_USER` / `WAYFOLD_AUTH_PASSWORD`
- `WAYFOLD_SESSION_SECRET`
- `WAYFOLD_OPEN_ACCESS=0`
- `WAYFOLD_ALLOW_QS_AUTH=0`
- `WAYFOLD_SEED_DEMO=0`
- `WAYFOLD_DATA_DIR=/var/lib/wayfold-compliance`

## Demo dataset

```bash
docker exec wayfold-compliance-engine \
  python -m engine.seed_review_demo --data-dir /var/lib/wayfold-compliance
```

Marker: `WF_REVIEW_DEMO_2026`
