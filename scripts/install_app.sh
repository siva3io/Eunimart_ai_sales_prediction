#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

set -e

apt-get update

apt-get install python3.6 python3-pip nginx libpq-dev libsm6

rm -rf /etc/systemd/system/ai-sales-prediction.service

# rm -rf /etc/nginx/sites-available/default

# cat >> /etc/nginx/sites-available/default <<EOT
# server {
#     gzip on;
#     gzip_types application/json;
#     gzip_min_length 1000;
#     gzip_proxied no-cache no-store private expired auth;
#     gunzip on;
#     listen 80;
#     location /api/v2/service-name {
#         include proxy_params;
#         proxy_pass http://127.0.0.1:9001;
#         proxy_connect_timeout   3800;
#         proxy_send_timeout      3800;
#         proxy_read_timeout      3800;

#     }
#     location ^~ /health-check {
#        access_log off;
#        return 200;
#        add_header Content-Type text/plain;
#     }
# }
# EOT

cat >> /etc/systemd/system/ai-sales-prediction.service <<EOT
[Unit]
Description=ai sales prediction
After=network.target
StartLimitIntervalSec=0
[Service]
Type=simple
Environment=DEPLOY_ENV=prod
ExecStart=/home/ubuntu/vdezi_ai_sales_prediction/scripts/run_server.sh
RemainAfterExit=no
Restart=on-failure
RestartSec=5s
User=root
Group=www-data


[Install]
WantedBy=multi-user.target
EOT


systemctl daemon-reload
systemctl reload nginx
systemctl enable ai-sales-prediction.service
systemctl start ai-sales-prediction.service
