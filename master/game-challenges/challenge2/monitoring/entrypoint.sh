#!/bin/bash
set -e

# Start SSH server
service ssh start

# Start Nginx
service nginx start

# Fix Grafana permissions
mkdir -p /var/lib/grafana/plugins
mkdir -p /var/log/grafana
chown -R grafana:grafana /var/lib/grafana
chown -R grafana:grafana /var/log/grafana
chown -R grafana:grafana /etc/grafana

# Create a hidden alert notification with the flag
mkdir -p /var/lib/grafana/alerting
cat > /var/lib/grafana/alerting/notifications.yaml << EOF
apiVersion: 1
items:
  - name: AdminAlert
    type: webhook
    uid: admin_webhook
    org_id: 1
    is_default: false
    settings:
      url: https://monitor.internal.corp/alert
      username: admin
      password: \$\$FLAG_PLACEHOLDER_7\$\$
      httpMethod: POST
EOF
chown grafana:grafana /var/lib/grafana/alerting/notifications.yaml
chmod 640 /var/lib/grafana/alerting/notifications.yaml

# Create a file with obfuscated flag that requires decoding
FLAG=$(echo "FLAG_PLACEHOLDER_7" | base64)
echo "This is a system generated file. Do not modify." > /var/lib/grafana/.env
echo "GRAFANA_SECURITY_KEY=$FLAG" >> /var/lib/grafana/.env
echo "GRAFANA_ADMIN_USER=admin" >> /var/lib/grafana/.env
echo "GRAFANA_ADMIN_PASS=admin" >> /var/lib/grafana/.env
chown grafana:grafana /var/lib/grafana/.env
chmod 600 /var/lib/grafana/.env

# Ensure proper homepath is set
echo "Starting Grafana with proper homepath..."
sudo -u grafana /usr/sbin/grafana-server \
  --homepath=/usr/share/grafana \
  --config=/etc/grafana/grafana.ini \
  --pidfile=/var/run/grafana/grafana-server.pid \
  cfg:default.paths.logs=/var/log/grafana \
  cfg:default.paths.data=/var/lib/grafana \
  cfg:default.paths.plugins=/var/lib/grafana/plugins &

# Start monitoring API
cd /opt/monitoring-api
nohup python3 api.py > /var/log/monitoring-api.log 2>&1 &

echo "All services started. Container is ready."

# Keep container running
exec tail -f /dev/null
