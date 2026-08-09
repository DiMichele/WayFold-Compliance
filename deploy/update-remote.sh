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
BUILD_ENV="$APP_DIR/data/engine/.build.env"
if [[ ! -f "$BUILD_ENV" ]]; then
  umask 077
  cat >"$BUILD_ENV" <<EOF
WAYFOLD_BUILD_SHA=${WAYFOLD_BUILD_SHA:-unknown}
WAYFOLD_BUILT_AT=${WAYFOLD_BUILT_AT:-}
WAYFOLD_APP_VERSION=0.1.0
WAYFOLD_SCHEMA_VERSION=1
EOF
fi
chmod 600 "$BUILD_ENV" 2>/dev/null || true
# Prefer env exported by deploy script
if [[ -n "${WAYFOLD_BUILD_SHA:-}" ]]; then
  umask 077
  cat >"$BUILD_ENV" <<EOF
WAYFOLD_BUILD_SHA=$WAYFOLD_BUILD_SHA
WAYFOLD_BUILT_AT=${WAYFOLD_BUILT_AT:-}
WAYFOLD_APP_VERSION=${WAYFOLD_APP_VERSION:-0.1.0}
WAYFOLD_SCHEMA_VERSION=1
EOF
  chmod 600 "$BUILD_ENV"
fi

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

# Ownership for container UIDs — NEVER world-writable (no a+rwx / a+rwX).
# GRC core: uid 1001; engine: match compose user (often 1000/1001).
ENGINE_UID="${WAYFOLD_ENGINE_UID:-1000}"
ENGINE_GID="${WAYFOLD_ENGINE_GID:-1000}"
if ! docker run --rm -v "$APP_DIR/data/db:/code/db" alpine:3.20 \
  sh -c 'chown -R 1001:1001 /code/db && chmod -R u+rwX,g+rwX,o-rwx /code/db'; then
  echo "ERROR: docker chown failed for data/db — refusing world-writable fallback" >&2
  exit 1
fi
if ! docker run --rm -v "$APP_DIR/data/engine:/data/engine" alpine:3.20 \
  sh -c "chown -R ${ENGINE_UID}:${ENGINE_GID} /data/engine && chmod -R u+rwX,g+rwX,o-rwx /data/engine && find /data/engine -type f -name '.auth.env' -exec chmod 600 {} \; && find /data/engine -type d -exec chmod 750 {} \;"; then
  echo "ERROR: docker chown failed for data/engine — refusing world-writable fallback" >&2
  exit 1
fi
chmod 600 "$AUTH_ENV" 2>/dev/null || true
# Verify no world-writable engine/db paths
if find data/engine data/db -perm -0002 2>/dev/null | grep -q .; then
  echo "ERROR: world-writable paths under data/ — abort deploy" >&2
  find data/engine data/db -perm -0002 2>/dev/null | head -20 >&2 || true
  exit 1
fi

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
