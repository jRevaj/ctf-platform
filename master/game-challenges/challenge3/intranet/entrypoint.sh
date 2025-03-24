#!/bin/bash

# Setup directories
mkdir -p /var/log/nginx
mkdir -p /var/log/supervisor
mkdir -p /var/run/redis
mkdir -p /var/lib/redis
mkdir -p /var/lib/gogs/data/sessions
mkdir -p /var/lib/gogs/repositories
mkdir -p /var/lib/gogs/log

# Set correct permissions
chown -R ctf-user:ctf-user /var/lib/gogs
chmod -R 755 /var/lib/gogs
chown -R redis:redis /var/lib/redis
chown -R redis:redis /var/run/redis

# Setup log files
touch /var/log/nginx/gogs_access.log
touch /var/log/nginx/gogs_error.log
chown www-data:www-data /var/log/nginx/gogs_access.log
chown www-data:www-data /var/log/nginx/gogs_error.log

# Ensure Redis has the flag
echo "Setting up Redis with flag..."
redis-server /etc/redis/redis.conf --daemonize yes
sleep 2
redis-cli set secret_flag "FLAG_PLACEHOLDER_5"
redis-cli shutdown

# Start supervisor to manage all services
echo "Starting all services with supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf 