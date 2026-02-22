#!/bin/sh
set -e

CERT_PATH="/etc/letsencrypt/live/coact-ai.com/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/coact-ai.com/privkey.pem"
NGINX_CONF="/etc/nginx/conf.d/default.conf"

if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
    echo "SSL certificates not found. Using HTTP-only config..."
    cp /etc/nginx/nginx.http.conf "$NGINX_CONF"
    
    echo "HTTPS disabled. HTTP-only config active."
else
    echo "SSL certificates found. HTTPS enabled."
fi

exec nginx -g "daemon off;"
