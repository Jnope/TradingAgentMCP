#!/bin/bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-trading-agents-mcp}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"

echo "=========================================="
echo "  Building TradingAgents MCP Docker Image"
echo "  Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Dockerfile: ${DOCKERFILE}"
echo "=========================================="

docker build \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  -f "${DOCKERFILE}" \
  .

echo ""
echo "Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "Run with:"
echo "  docker compose -f docker/docker-compose.yml up -d"
echo ""
echo "Test with:"
echo '  curl -X POST http://localhost:19876/mcp/v1/tools/agent_status \'
echo '    -H "Content-Type: application/json" \'
echo '    -d "{}"'