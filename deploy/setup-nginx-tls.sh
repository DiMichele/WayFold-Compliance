#!/usr/bin/env bash
# Run as root (or sudo) on VPS — nginx site + Let's Encrypt for compliance.wayfold.xyz
set -euo pipefail

APP_DIR="${APP_DIR:-/home/wayfold/apps/wayfold-compliance}"
SITE_SRC="$APP_DIR/deploy/nginx-compliance.conf"
SITE_AVAIL=/etc/nginx/sites-available/compliance
SITE_ENABLED=/etc/nginx/sites-enabled/compliance
DOMAIN=compliance.wayfold.xyz

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

cp "$SITE_SRC" "$SITE_AVAIL"

# First-time: temporary HTTP-only server so certbot can obtain cert
if [[ ! -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ]]; then
  cat > "$SITE_AVAIL" <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name compliance.wayfold.xyz;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / {
        proxy_pass http://127.0.0.1:13000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
  ln -sfn "$SITE_AVAIL" "$SITE_ENABLED"
  nginx -t
  systemctl reload nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect
fi

# Install full HTTPS config
cp "$SITE_SRC" "$SITE_AVAIL"
ln -sfn "$SITE_AVAIL" "$SITE_ENABLED"
nginx -t
systemctl reload nginx
echo "TLS OK: https://$DOMAIN"
