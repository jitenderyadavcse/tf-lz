#!/bin/bash

# Build and run MCP Leaves Manager container

set -e

echo "🐳 Building MCP Leaves Manager Docker image..."
docker build -t mcp-leaves-manager:latest .

echo "✅ Build complete!"
echo ""
echo "To run the container:"
echo "  docker run -d --name leaves-manager -p 8000:8000 mcp-leaves-manager:latest"
echo ""
echo "To view logs:"
echo "  docker logs leaves-manager"
echo ""
echo "To stop:"
echo "  docker stop leaves-manager"
echo ""
echo "To remove:"
echo "  docker rm leaves-manager"
