#!/bin/bash

# ============================================================================
# Football Analytics Platform - Start All Services
# ============================================================================

set -e  # Exit on error

echo "🚀 Starting Football Analytics Platform..."
echo ""

# ============================================================================
# Step 1: Start Docker Services
# ============================================================================
echo "📦 Starting Docker services (NiFi, PostgreSQL, Superset)..."
docker-compose -f docker-compose.streaming.yml up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# ============================================================================
# Step 2: Check Service Status
# ============================================================================
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.streaming.yml ps

# ============================================================================
# Step 3: Display Access URLs
# ============================================================================
echo ""
echo "✅ Services started successfully!"
echo ""
echo "============================================================================"
echo "📍 ACCESS URLS"
echo "============================================================================"
echo ""
echo "🔵 Apache NiFi (Data Producer):"
echo "   URL: https://localhost:8443/nifi"
echo "   Username: admin"
echo "   Password: adminadmin123456"
echo "   Status: Starting (wait ~2 minutes)"
echo ""
echo "📊 Apache Superset (Dashboards):"
echo "   URL: http://localhost:8088"
echo "   Username: admin"
echo "   Password: admin"
echo "   Status: Starting (wait ~2 minutes)"
echo ""
echo "🐘 PostgreSQL Database:"
echo "   Host: localhost:5432"
echo "   Database: football_analytics"
echo "   Username: postgres"
echo "   Password: 9281746356"
echo ""
echo "☁️ Confluent Cloud Kafka:"
echo "   URL: https://confluent.cloud/"
echo "   Note: Configure .env with your credentials"
echo ""
echo "============================================================================"
echo "📚 NEXT STEPS"
echo "============================================================================"
echo ""
echo "1️⃣  Setup Confluent Cloud (if not done):"
echo "    → See: CONFLUENT_CLOUD_SETUP.md"
echo ""
echo "2️⃣  Configure Environment:"
echo "    → cp .env.example .env"
echo "    → nano .env  # Add your Confluent Cloud credentials"
echo ""
echo "3️⃣  Build NiFi Flow (Visual UI):"
echo "    → Open: https://localhost:8443/nifi"
echo "    → Follow: NIFI_QUICKSTART.md"
echo ""
echo "4️⃣  Start Spark Consumer:"
echo "    → export \$(cat .env | xargs)"
echo "    → python src/streaming/live_events_consumer.py"
echo ""
echo "5️⃣  Create Superset Dashboards:"
echo "    → Open: http://localhost:8088"
echo "    → Follow: SUPERSET_SETUP.md"
echo ""
echo "6️⃣  Run Batch ETL Pipeline:"
echo "    → python run_pipeline.py"
echo ""
echo "============================================================================"
echo "📖 DOCUMENTATION"
echo "============================================================================"
echo ""
echo "Quick Start:"
echo "  • README.md - Main documentation"
echo "  • QUICKSTART.md - 3-minute setup"
echo "  • NIFI_QUICKSTART.md - NiFi setup (5 minutes)"
echo ""
echo "Detailed Guides:"
echo "  • NIFI_SETUP_GUIDE.md - Complete NiFi guide"
echo "  • CONFLUENT_CLOUD_SETUP.md - Kafka setup"
echo "  • SUPERSET_SETUP.md - Dashboard guide"
echo "  • PROJECT_OVERVIEW.md - Full documentation"
echo ""
echo "============================================================================"
echo ""
echo "🎉 All services started! Wait ~2 minutes for NiFi & Superset to initialize."
echo ""
