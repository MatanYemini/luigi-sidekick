#!/bin/bash
set -e

echo "Starting Luigi Sidekick Services..."

# Build and start all containers
echo "Building containers..."
docker-compose down
docker-compose build

# Start the services
echo "Starting services..."
docker-compose up -d

# Wait for API container to be ready
echo "Waiting for API container to be up..."
sleep 5


echo "All services are now running."
echo "- API: http://localhost:8000"
echo "- MCP Atlassian: http://localhost:9000/sse"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down" 