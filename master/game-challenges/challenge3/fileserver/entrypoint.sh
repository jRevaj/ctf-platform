#!/bin/bash
set -e

# Start SSH server
service ssh start

# Start Apache for file serving
service apache2 start

# Fix elasticsearch folder permissions
chown -R elasticsearch:elasticsearch /var/lib/elasticsearch
chown -R elasticsearch:elasticsearch /etc/elasticsearch
chown -R elasticsearch:elasticsearch /var/log/elasticsearch

# Start Elasticsearch service (with reduced verbosity)
echo "Starting Elasticsearch..."
service elasticsearch start

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to start..."
until curl -s "http://localhost:9200/_cluster/health?wait_for_status=yellow" > /dev/null; do
    echo "Waiting for Elasticsearch to become available..."
    sleep 5
done

# Create index and add documents
echo "Elasticsearch is ready. Creating system-secrets index..."
curl -X PUT "localhost:9200/system-secrets?pretty" -H "Content-Type: application/json" -d'
{
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "description": { "type": "text" },
      "secret_data": { "type": "text" }
    }
  }
}'

sleep 2

# Add sample documents to index
echo "Adding documents to system-secrets index..."
curl -X POST "localhost:9200/system-secrets/_doc?pretty" -H "Content-Type: application/json" -d'
{
  "id": "sys123",
  "description": "System Configuration",
  "secret_data": "Regular system config"
}'

curl -X POST "localhost:9200/system-secrets/_doc?pretty" -H "Content-Type: application/json" -d'
{
  "id": "flag456",
  "description": "Hidden flag information",
  "secret_data": "FLAG_PLACEHOLDER_11"
}'

curl -X POST "localhost:9200/system-secrets/_doc?pretty" -H "Content-Type: application/json" -d'
{
  "id": "sys789",
  "description": "Network Configuration",
  "secret_data": "Regular network settings"
}'

# Remove access to this entrypoint file
echo "Removing access to this entrypoint file..."
chmod 700 /entrypoint.sh
chown root:root /entrypoint.sh

echo "All services started. Container is ready."

# Keep container running
exec tail -f /dev/null 