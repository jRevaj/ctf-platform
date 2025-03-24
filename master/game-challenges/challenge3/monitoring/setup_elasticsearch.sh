#!/bin/bash

# Wait for Elasticsearch to start
echo "Waiting for Elasticsearch to start..."
until curl -s http://localhost:9200 > /dev/null; do
    sleep 1
done
echo "Elasticsearch is running"

# Create an index with the flag
echo "Creating system-secrets index with flag..."
curl -X PUT "localhost:9200/system-secrets" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  }
}
'

# Add the flag to the index
echo "Adding flag to the index..."
curl -X POST "localhost:9200/system-secrets/_doc" -H 'Content-Type: application/json' -d'
{
  "title": "Elasticsearch Secret",
  "content": "This is a secret document",
  "flag": "FLAG_PLACEHOLDER_11",
  "access_level": "admin",
  "created_at": "2023-01-01T00:00:00Z"
}
'

echo "Elasticsearch setup completed" 