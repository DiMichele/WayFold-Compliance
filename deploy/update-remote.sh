#!/usr/bin/env bash
# Run on VPS as wayfold — pull/sync already done; start/reload stack.
set -euo pipefail

APP_DIR="${APP_DIR:-/home/wayfold/apps/wayfold-compliance}"
export WAYFOLD_COMPLIANCE_ROOT="$APP_DIR"
COMPOSE=(docker compose --project-directory "$APP_DIR" -f "$APP_DIR/deploy/docker-compose.prod.yml")

cd "$APP_DIR"
mkdir -p data/db data/engine
# Clean mistaken bind targets from earlier path-resolution bugs
rm -rf deploy/data 2>/dev/null || true

# Consultant login credentials (not in git). Created once; persisted on volume.
AUTH_ENV="$APP_DIR/data/engine/.auth.env"
AUTH_NOTE="$APP_DIR/data/engine/.consultant-credentials"
if [[ ! -f "$AUTH_ENV" ]]; then
  echo "==> Creating consultant auth credentials (first deploy)"
  USER_EMAIL="${WAYFOLD_AUTH_USER:-consultant@wayfold.xyz}"
  PASS="$(openssl rand -base64 18 | tr -d '=+/' | cut -c1-20)"
  SECRET="$(openssl rand -hex 32)"
  umask 077
  cat >"$AUTH_ENV" <<EOF
WAYFOLD_AUTH_USER=$USER_EMAIL
WAYFOLD_AUTH_PASSWORD=$PASS
WAYFOLD_SESSION_SECRET=$SECRET
EOF
  cat >"$AUTH_NOTE" <<EOF
WayFold Compliance — consultant login
URL: https://compliance.wayfold.xyz/login
User: $USER_EMAIL
Password: $PASS
Generated: $(date -u +%Y-%m-%dT%H:%MZ)
EOF
  chmod 600 "$AUTH_ENV" "$AUTH_NOTE"
  echo "==> Credentials written to data/engine/.consultant-credentials (server-only)"
fi
# Compose requires env_file to exist
touch "$AUTH_ENV"
chmod 600 "$AUTH_ENV" 2>/dev/null || true

# One-shot clean slate: touch data/.wipe_db before deploy to reset GRC + engine stores
if [[ -f data/.wipe_db ]]; then
  echo "==> Wiping GRC DB + engine stores (clean workspace)"
  # Stop stack first if present so sqlite files are released
  "${COMPOSE[@]}" down --remove-orphans 2>/dev/null || true
  for c in wayfold-compliance-backend wayfold-compliance-frontend wayfold-compliance-huey \
           wayfold-compliance-engine wayfold-compliance-qdrant; do
    docker rm -f "$c" 2>/dev/null || true
  done
  # Files may be owned by uid 1001 — wipe via root container
  docker run --rm \
    -v "$APP_DIR/data:/data" alpine:3.20 \
    sh -c 'rm -rf /data/db/* /data/engine/*; mkdir -p /data/db /data/engine; printf "%s\n" "{\"programs\": []}" > /data/engine/portfolio_registry.json'
  rm -f data/.wipe_db
fi

# GRC core images expect uid 1001 for db volume (no passwordless sudo on VPS:
# use a one-shot root container to chown the bind mount).
if ! docker run --rm -v "$APP_DIR/data/db:/code/db" alpine:3.20 \
  sh -c 'chown -R 1001:1001 /code/db && chmod -R u+rwX,g+rwX /code/db'; then
  echo "WARN: docker chown failed; trying chmod a+rwx on data/db" >&2
  chmod -R a+rwx data/db || true
fi
chmod -R a+rwX data/engine 2>/dev/null || true

echo "==> Pull + up Compliance stack"
# Tear down previous project names (compose file dir was used as project name before)
docker compose -f "$APP_DIR/deploy/docker-compose.prod.yml" --project-directory "$APP_DIR/deploy" down --remove-orphans 2>/dev/null || true
"${COMPOSE[@]}" down --remove-orphans 2>/dev/null || true
for c in wayfold-compliance-backend wayfold-compliance-frontend wayfold-compliance-huey \
         wayfold-compliance-engine wayfold-compliance-qdrant; do
  docker rm -f "$c" 2>/dev/null || true
done
"${COMPOSE[@]}" pull
# Recreate only when config/image changed; avoid full library re-seed every deploy
"${COMPOSE[@]}" up -d --remove-orphans

echo "==> Wait for backend health"
for i in $(seq 1 60); do
  # Host must be in ALLOWED_HOSTS (127.0.0.1 alone is rejected by Django)
  if curl -fsS -H 'Host: localhost' http://127.0.0.1:18000/api/health/ >/dev/null 2>&1; then
    echo "backend healthy"
    break
  fi
  # Compose may already mark the service healthy before our host-header curl succeeds
  status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' wayfold-compliance-backend 2>/dev/null || true)"
  if [[ "$status" == "healthy" ]]; then
    echo "backend healthy (docker healthcheck)"
    break
  fi
  sleep 5
  if [[ "$i" -eq 60 ]]; then
    echo "backend health timeout" >&2
    "${COMPOSE[@]}" ps >&2 || true
    docker logs wayfold-compliance-backend 2>&1 | tail -40 >&2 || true
    exit 1
  fi
done

echo "==> Seed product-review demo dataset (safe, demo-only)"
# Installs WF_REVIEW_DEMO_2026 into writable engine data volume. Idempotent.
docker exec wayfold-compliance-engine \
  python -m engine.seed_review_demo --data-dir /var/lib/wayfold-compliance \
  || echo "WARN: review demo seed failed (engine may still be starting)"

echo "==> Stack status"
"${COMPOSE[@]}" ps
echo "Deploy app layer OK. Ensure nginx+cert for compliance.wayfold.xyz are installed."
