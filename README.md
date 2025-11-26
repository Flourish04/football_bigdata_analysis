# ⚽ Football Analytics Data Platform

A production-grade **Big Data ETL pipeline** for football (soccer) analytics with **941K match events**, **92K players**, and **real-time streaming** capabilities. Features **Apache NiFi** visual producer, **Confluent Cloud Kafka**, **Spark Streaming**, and **Apache Superset** dashboards.

## 🚀 Quick Start

### **Batch Processing Pipeline:**
```bash
# Run full ETL pipeline (Bronze → Silver → Gold → Events → PostgreSQL)
python run_pipeline.py
```

**Pipeline Runtime:** ~3 minutes  
**Total Records Processed:** 6.5M+ records (including 941K events)

### **Real-Time Streaming Pipeline (Local Setup):**
```bash
# 1. Start NiFi (local installation)
cd /opt/nifi/nifi-*
./bin/nifi.sh start

# 2. Start Superset (local installation)
source superset_env/bin/activate
superset run -p 8088 --with-threads

# 3. Access NiFi Web UI: http://localhost:8080/nifi
#    Build NiFi flow (see NIFI_SETUP_GUIDE.md)

# 4. Start Spark consumer (new terminal)
cd /home/hung/Downloads/bigdata/football_project
export $(cat .env | xargs)
python src/streaming/live_events_consumer.py

# 5. Access Superset Dashboard: http://localhost:8088 (admin/admin)
#    Create dashboards (see SUPERSET_SETUP.md)
```

**See `LOCAL_SETUP.md` for complete local installation guide (no Docker)**

## 📊 Key Features

- **Medallion Architecture**: Bronze (raw) → Silver (cleaned) → Gold (analytics)
- **Match Events Layer**: 941K events from 10K matches (goals, shots, cards, corners) ⚽ **NEW**
- **Real-Time Streaming**: Kafka + Spark Streaming for live match updates 🔴 **NEW**
- **5 Gold Analytics Tables**: 403K records with comprehensive player metrics
- **PostgreSQL Integration**: 18 tables, 6.5M records, 50+ optimized indexes
- **Views & Materialized Views**: 8 views + 3 materialized views for fast analytics
- **Data Quality Validation**: 8 automated quality checks
- **Single Command Execution**: Complete pipeline in one Python script

## 🏗️ Architecture

```mermaid
CSV Data (11 files, 5.6M records) + Events Data (941K events, 10K matches)
    ↓
Bronze Layer (Parquet) - Raw ingestion
    ↓
Events Layer (Parquet) - Match events processing ⚽ NEW
    ↓
Silver Layer (Parquet) - Data cleaning & standardization
    ↓
Gold Layer (Parquet) - Analytics aggregations
    ↓
PostgreSQL Database - SQL analytics ready (Bronze/Silver/Gold/Events schemas)
    ↓
Views & Materialized Views - Optimized queries
    ↓
Real-Time Streaming: API → Kafka → Spark → PostgreSQL (streaming schema) 🔴 NEW
```

## 📦 Data Tables Summary

### **Gold Layer (Player Analytics)**
| Table | Records | Description |
|-------|---------|-------------|
| `player_analytics_360` | 92,671 | Comprehensive 360° player profiles |
| `player_form_metrics` | 88,375 | Performance statistics (goals, assists, per-90min rates) |
| `market_value_trends` | 69,441 | Market value trends & volatility analysis |
| `injury_risk_scores` | 34,561 | Injury history & risk assessment |
| `transfer_intelligence` | 117,944 | Transfer history & market intelligence |

### **Events Layer (Match Analytics)** ⚽ **NEW**
| Table | Records | Description |
|-------|---------|-------------|
| `match_info` | 10,113 | General match information (teams, scores, dates) |
| `match_statistics` | 10,113 | Aggregated match stats (shots, corners, cards) |
| `player_event_statistics` | 8,421 | Player performance from events (goals, assists, shots) |

### **Streaming Layer (Real-Time)** � **NEW**
| Table | Records | Description |
|-------|---------|-------------|
| `live_events` | Dynamic | Real-time match updates from Kafka stream |

## �🔍 Views & Analytics

### Regular Views (8 total)
- `vw_top_players` - Top 100 players by overall score
- `vw_high_value_low_risk_players` - High-value players with low injury risk
- `vw_transfer_opportunities` - Best transfer targets
- `events.vw_top_scorers` - Top goal scorers from events ⚽
- `events.vw_player_discipline` - Player discipline statistics ⚽
- `events.vw_high_scoring_matches` - Matches with 5+ goals ⚽
- `streaming.vw_current_live_matches` - Currently live matches 🔴
- `streaming.vw_match_score_progression` - Score progression timeline 🔴

### Materialized Views (3 total)
- `mvw_position_statistics` - Aggregated stats by player position
- `mvw_age_group_analysis` - Player statistics by age groups
- `events.mvw_league_statistics` - League-level aggregated statistics ⚽

## 💻 Sample Queries

```sql
-- Top 10 players overall
SELECT player_name, overall_player_score, peak_market_value
FROM analytics.player_analytics_360
ORDER BY overall_player_score DESC
LIMIT 10;

-- High-value low-risk players
SELECT * FROM analytics.vw_high_value_low_risk_players
LIMIT 10;

-- Position statistics
SELECT * FROM analytics.mvw_position_statistics
ORDER BY total_players DESC;
```

## 🛠️ Tech Stack

### **Batch Processing:**
- **Languages**: Python 3.11+
- **Big Data**: Apache Spark (PySpark 3.5.0)
- **Database**: PostgreSQL 14+
- **Storage**: Parquet (columnar format)
- **Data Volume**: 5.6M+ records, ~400K analytics records

### **Real-Time Streaming:**
- **Producer**: Apache NiFi 1.25.0 (visual data flow)
- **Message Queue**: Confluent Cloud Kafka (managed service)
- **Consumer**: Spark Structured Streaming
- **Visualization**: Apache Superset 3.0.0

### **Infrastructure:**
- **Deployment**: Local installation (no Docker required)
- **NiFi**: Apache NiFi 1.25.0 (local)
- **Superset**: Apache Superset 3.0.0 (local)
- **PostgreSQL**: PostgreSQL 14+ (local)
- **Version Control**: Git
- **Security**: SASL/SSL authentication

## 📁 Project Structure

```
football_project/
├── run_pipeline.py              # Main orchestrator
├── validate_data.py             # Data quality validation
├── src/
│   ├── bronze_layer.py         # CSV → Parquet ingestion
│   ├── silver_layer.py         # Data cleaning & standardization
│   ├── gold_layer.py           # Analytics aggregation
│   └── data_quality_check.py   # Quality checks
├── schema/
│   ├── analytics_schema.sql    # PostgreSQL DDL
│   ├── create_views_only.sql   # Views & materialized views
│   ├── create_views.py         # View creation script
│   ├── load_silver_to_postgres.py
│   └── load_gold_to_postgres.py
├── PROJECT_OVERVIEW.md          # Comprehensive documentation
└── DATA_QUALITY.md              # Data quality rules
```

## 📊 Data Quality

- ✅ **Schema Validation**: Correct data types (INTEGER, BIGINT, DECIMAL)
- ✅ **Range Checks**: Capped per-90min rates, validated score ranges
- ✅ **NULL Validation**: Monitored NULL percentages
- ✅ **Duplicate Detection**: Player-season combination checks
- ✅ **Referential Integrity**: Cross-layer key validation
- ✅ **Record Count Validation**: Expected range checks
- ✅ **Views Validation**: All views contain data
- ✅ **Parquet Validation**: All files readable

## 🔧 Database Connection

```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='football_analytics',
    user='postgres',
    password='your_password'
)
```

## 📈 Pipeline Performance

| Layer | Duration | Records |
|-------|----------|---------|
| Bronze | ~52s | 5,605,055 |
| Silver | ~25s | 5,535,614 |
| Gold | ~11s | 402,992 |
| Load Silver | ~13s | 68,117 (selected tables) |
| Load Gold | ~32s | 402,992 |
| Create Views | ~0.2s | 5 views |
| Validation | ~10s | 8 checks |
| **Total** | **~2.4 min** | **5.9M+ records** |

## 📚 Documentation

### **Core Documentation:**
- [LOCAL_SETUP.md](LOCAL_SETUP.md) - **Local setup guide (no Docker)** ⭐ **START HERE**
- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - Complete system documentation
- [DATA_QUALITY.md](DATA_QUALITY.md) - Data quality rules and validation
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide

### **Streaming Documentation:**
- [NIFI_SETUP_GUIDE.md](NIFI_SETUP_GUIDE.md) - Complete NiFi guide (1000+ lines)
- [NIFI_ARCHITECTURE.md](NIFI_ARCHITECTURE.md) - Architecture & benefits
- [CONFLUENT_CLOUD_SETUP.md](CONFLUENT_CLOUD_SETUP.md) - Kafka setup
- [STREAMING_ARCHITECTURE.md](STREAMING_ARCHITECTURE.md) - System overview

### **Visualization:**
- [SUPERSET_SETUP.md](SUPERSET_SETUP.md) - Apache Superset dashboard setup

### **Legacy (Docker-based):**
- [NIFI_QUICKSTART.md](NIFI_QUICKSTART.md) - Docker setup (optional)
- [docker-compose.streaming.yml](docker-compose.streaming.yml) - Docker config (optional)

## 🎯 Use Cases

### **Batch Analytics:**
1. **Player Scouting**: Identify top performers by position, age, and value
2. **Transfer Analysis**: Find undervalued players with positive trends
3. **Injury Risk Assessment**: Evaluate player health and availability
4. **Market Intelligence**: Track transfer fees and value trends
5. **Performance Analytics**: Compare players across seasons and competitions

### **Real-Time Streaming:**
6. **Live Match Tracking**: Monitor ongoing matches with real-time scores
7. **Event Analysis**: Track goals, shots, cards as they happen
8. **Performance Dashboards**: Superset visualizations updated in real-time
9. **Alerting**: Get notified when specific events occur (goals scored, cards issued)

## 🔗 Related Projects

- Data Source: [Transfermarkt Football Dataset](https://www.transfermarkt.com/)
- Architecture: Medallion (Lakehouse) Pattern
- Query Engine: PostgreSQL + PySpark

## 📄 License

This project is for educational and analytical purposes.

---

**Made with ⚽ + 🐍 + 🐘**
