#!/bin/bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-ragento-analytics}"
ZONE="${ZONE:-us-central1-a}"
INSTANCE_NAME="${INSTANCE_NAME:-ragento-app-production}"
REMOTE_DIR="${REMOTE_DIR:-/home/smarak/studio-ragento-ai}"
REMOTE_USER="${REMOTE_USER:-smarak}"
DOMAIN="${DOMAIN:-studio.ragento.ai}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE="/tmp/studio-ragento-$(date +%s).tar.gz"

log() { printf '[studio-deploy] %s\n' "$1"; }

if [ ! -f "${ROOT_DIR}/vertex-cred.json" ]; then
  echo "[ERROR] ${ROOT_DIR}/vertex-cred.json not found"
  exit 1
fi

log "Creating deploy archive"
tar czf "$ARCHIVE" \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.vercel' \
  --exclude='output' \
  --exclude='1  INPUT' \
  --exclude='3  MOODBOARD REFERENCE' \
  --exclude='*.pyc' \
  -C "$ROOT_DIR" \
  server.py config.py models.py main.py requirements.txt run.sh run-prod.sh README.md \
  static src deployment/studio-vm

log "Uploading app archive"
gcloud compute scp "$ARCHIVE" "${INSTANCE_NAME}:/tmp/studio-ragento.tar.gz" \
  --zone="$ZONE" --project="$PROJECT_ID" --tunnel-through-iap

log "Uploading Vertex credentials"
gcloud compute scp "${ROOT_DIR}/vertex-cred.json" "${INSTANCE_NAME}:/tmp/studio-vertex-cred.json" \
  --zone="$ZONE" --project="$PROJECT_ID" --tunnel-through-iap

log "Installing app files and systemd unit"
gcloud compute ssh "$INSTANCE_NAME" \
  --zone="$ZONE" \
  --project="$PROJECT_ID" \
  --tunnel-through-iap \
  --command="
set -euo pipefail
sudo mkdir -p /var/log/ragento
sudo chown ${REMOTE_USER}:${REMOTE_USER} /var/log/ragento
mkdir -p '${REMOTE_DIR}'
tar xzf /tmp/studio-ragento.tar.gz -C '${REMOTE_DIR}'
install -m 600 /tmp/studio-vertex-cred.json '${REMOTE_DIR}/vertex-cred.json'
cat > '${REMOTE_DIR}/.env' <<'EOF'
VERTEX_CREDENTIALS_PATH=${REMOTE_DIR}/vertex-cred.json
VERTEX_PROJECT_ID=silicon-cocoa-476407-n3
VERTEX_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=${REMOTE_DIR}/vertex-cred.json
EOF
python3 -m venv '${REMOTE_DIR}/venv' || true
'${REMOTE_DIR}/venv/bin/pip' install --upgrade pip
'${REMOTE_DIR}/venv/bin/pip' install -r '${REMOTE_DIR}/requirements.txt' gunicorn
sudo cp '${REMOTE_DIR}/deployment/studio-vm/ragento-studio.service' /etc/systemd/system/ragento-studio.service
sudo systemctl daemon-reload
sudo systemctl enable ragento-studio.service
sudo systemctl restart ragento-studio.service
rm -f /tmp/studio-ragento.tar.gz /tmp/studio-vertex-cred.json
"

log "Installing nginx site"
gcloud compute ssh "$INSTANCE_NAME" \
  --zone="$ZONE" \
  --project="$PROJECT_ID" \
  --tunnel-through-iap \
  --command="
set -euo pipefail
if sudo test -f '/etc/letsencrypt/live/${DOMAIN}/fullchain.pem' && sudo test -f '/etc/letsencrypt/live/${DOMAIN}/privkey.pem'; then
sudo tee /etc/nginx/sites-available/${DOMAIN} >/dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}

server {
    listen 8081 default_server;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}
EOF
else
sudo cp '${REMOTE_DIR}/deployment/studio-vm/nginx-studio.conf' /etc/nginx/sites-available/${DOMAIN}
fi
sudo ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/${DOMAIN}
sudo nginx -t
sudo systemctl reload nginx
"

log "Deployment complete. If DNS is already pointed, issue TLS with:"
log "sudo certbot --nginx -d ${DOMAIN}"
rm -f "$ARCHIVE"
