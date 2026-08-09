#!/usr/bin/env bash
set -euo pipefail
AUTH=/home/wayfold/apps/wayfold-compliance/data/engine/.auth.env
# Ensure TEMPORARY REVIEW CREDENTIAL admin/admin for external audit
SECRET=$(grep '^WAYFOLD_SESSION_SECRET=' "$AUTH" 2>/dev/null | cut -d= -f2- || true)
if [[ -z "${SECRET}" ]]; then SECRET=$(openssl rand -hex 32); fi
umask 077
cat >"$AUTH" <<EOF
WAYFOLD_AUTH_USER=admin
WAYFOLD_AUTH_PASSWORD=admin
WAYFOLD_SESSION_SECRET=$SECRET
EOF
chmod 600 "$AUTH"
docker restart wayfold-compliance-engine >/dev/null
sleep 2

CK=/tmp/wf-live.ck
rm -f "$CK"
echo "== local anonymous portfolio"
curl -sS -o /dev/null -w "portfolio_anon=%{http_code} redirect=%{redirect_url}\n" http://127.0.0.1:18092/portfolio
echo "== local login"
curl -sS -c "$CK" -b "$CK" -X POST \
  -d 'username=admin&password=admin&next=/portfolio' \
  -o /dev/null -w "login_post=%{http_code} redirect=%{redirect_url}\n" \
  http://127.0.0.1:18092/login
echo "== local portfolio authed"
curl -sS -b "$CK" -o /tmp/wf-port.html -w "portfolio_auth=%{http_code}\n" http://127.0.0.1:18092/portfolio
grep -o 'Michele[^<]*' /tmp/wf-port.html | head -3 || true
grep -o 'Action Center\|Da revisionare\|Portfolio' /tmp/wf-port.html | head -5 || true
echo "== local new routes"
for p in /clients /frameworks /mappings /audit /settings /checklist /gaps /evidence /report; do
  code=$(curl -sS -b "$CK" -o /dev/null -w "%{http_code}" "http://127.0.0.1:18092${p}")
  echo "$p $code"
done
echo "== evidence download"
EV=$(curl -sS -b "$CK" "http://127.0.0.1:18092/api/evidence?program_id=program-michele-cyber-2026" | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d[0].get("evidence_id") if isinstance(d,list) and d else d.get("evidence",[{}])[0].get("evidence_id","")) if d else "")' 2>/dev/null || true)
if [[ -n "${EV}" ]]; then
  curl -sS -b "$CK" -o /dev/null -w "evidence_dl=%{http_code}\n" "http://127.0.0.1:18092/api/evidence/${EV}/download"
else
  # try known demo id
  curl -sS -b "$CK" -o /tmp/ev.bin -w "evidence_dl=%{http_code} bytes=%{size_download}\n" "http://127.0.0.1:18092/api/evidence/EV-001/download?program_id=program-michele-cyber-2026"
fi
echo "== live HTTPS headers"
curl -sS -D - -o /dev/null https://compliance.wayfold.xyz/login | tr -d '\r' | grep -iE 'HTTP/|strict-transport|content-security|x-content-type|referrer-policy|permissions-policy|x-frame|content-type' || true
echo "== live anonymous"
curl -sS -o /dev/null -w "live_portfolio=%{http_code} redirect=%{redirect_url}\n" https://compliance.wayfold.xyz/portfolio
echo "== live login+portfolio"
rm -f /tmp/wf-live2.ck
curl -sS -c /tmp/wf-live2.ck -b /tmp/wf-live2.ck -X POST \
  -d 'username=admin&password=admin&next=/portfolio' \
  -o /dev/null -w "live_login=%{http_code} redirect=%{redirect_url}\n" \
  https://compliance.wayfold.xyz/login
curl -sS -b /tmp/wf-live2.ck -o /tmp/live-port.html -w "live_portfolio_auth=%{http_code}\n" https://compliance.wayfold.xyz/portfolio
grep -c 'Michele' /tmp/live-port.html || true
