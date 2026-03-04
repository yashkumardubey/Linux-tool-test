###############################################################################
#  PatchMaster Frontend — Shared Location Blocks
#  Included by both HTTP and HTTPS server blocks in default.conf
###############################################################################

root /usr/share/nginx/html;
index index.html;

# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy $csp_header always;

# Gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;

# Cache static assets aggressively
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}

# Proxy API requests to backend
location /api/ {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
    proxy_connect_timeout 10s;

    # Limit request body
    client_max_body_size 10m;
}

# Proxy agent .deb download
location /download/ {
    proxy_pass http://backend:8000/static/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

# Prometheus metrics (internal)
location /metrics {
    proxy_pass http://backend:8000/metrics;
    proxy_set_header Host $host;
}

# Serve React app for all other routes (SPA fallback)
location / {
    try_files $uri $uri/ /index.html;

    # Don't cache index.html
    location = /index.html {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }
}

# Block access to hidden files
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}
