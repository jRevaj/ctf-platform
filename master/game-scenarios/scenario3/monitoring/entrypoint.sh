#!/bin/bash

# Start SSH service
service ssh start
echo "SSH service started"

# Create necessary directories for Nagios
mkdir -p /usr/local/nagios/var/rw
chown -R nagios:nagios /usr/local/nagios/var/rw
chmod -R 775 /usr/local/nagios/var/rw

# Start Apache
service apache2 start
echo "Apache service started"

# Start Nagios
/usr/local/nagios/bin/nagios /usr/local/nagios/etc/nagios.cfg &
echo "Nagios service started"

# Start Elasticsearch as ctf-user
su - ctf-user -c "cd /usr/local/elasticsearch && ./bin/elasticsearch -d"
echo "Elasticsearch service started"

# Wait for Elasticsearch to be ready
sleep 10

# Set up Elasticsearch with flag
/setup_elasticsearch.sh

# Keep container running
echo "All services started. Container is now running..."
tail -f /dev/null 