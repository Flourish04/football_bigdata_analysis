#!/bin/bash

# ============================================================================
# Football Analytics Platform - Stop All Services
# ============================================================================

echo "🛑 Stopping Football Analytics Platform..."
echo ""

# Stop all services
docker-compose -f docker-compose.streaming.yml down

echo ""
echo "✅ All services stopped!"
echo ""
echo "To restart: ./start-services.sh"
echo ""
