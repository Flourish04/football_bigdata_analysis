# ⚽ Football Analytics Data Platform

A **Big Data ETL pipeline** for football analytics with **5.6M records**, **92K players**, and **real-time streaming** from Kafka to PostgreSQL.

---

## ⚙️ Setup

### **Environment Configuration**
```bash
# 1. Copy sample environment file
cp .env.sample .env

# 2. Edit .env and fill in your credentials:
#    - POSTGRES_PASSWORD (your PostgreSQL password)
#    - KAFKA_API_KEY (from Confluent Cloud)
#    - KAFKA_API_SECRET (from Confluent Cloud)
#    - FOOTBALL_API_TOKEN (from football-data.org)

# 3. Verify configuration
cat .env  # Check that all credentials are set
```

**⚠️ Important:** 
- `.env` contains your actual credentials (gitignored)
- `.env.sample` is the template (can be committed to Git)
- Never commit `.env` to version control

---

## 🚀 Quick Start## 🚀 Quick Start



### **1. Batch Processing Pipeline:**### **Batch Processing Pipeline:**

```bash```bash

# Run full ETL: Bronze → Silver → Gold → PostgreSQL# Run full ETL pipeline (Bronze → Silver → Gold → Events → PostgreSQL)

python run_pipeline.pypython run_pipeline.py

``````

**Runtime:** ~3 minutes | **Records:** 5.6M+

**Pipeline Runtime:** ~3 minutes  

### **2. Streaming Pipeline (Real-Time):****Total Records Processed:** 6.5M+ records (including 941K events)

```bash

# Stream live matches from Kafka → Postgres### **Real-Time Streaming Pipeline (Local Setup):**

python src/streaming/spark_streaming_upsert.py```bash

# Press Ctrl+C to stop gracefully# 1. Start NiFi (local installation)

```cd /opt/nifi/nifi-*

./bin/nifi.sh start

## 📊 Architecture

# 2. Start Superset (local installation)

```source superset_env/bin/activate

┌─────────────────────────────────────────────────────────────────┐superset run -p 8088 --with-threads

│                    BATCH PROCESSING                              │

├─────────────────────────────────────────────────────────────────┤# 3. Access NiFi Web UI: http://localhost:8080/nifi

│  CSV (11 files)  →  Bronze  →  Silver  →  Gold  →  PostgreSQL   │#    Build NiFi flow (see NIFI_SETUP_GUIDE.md)

│    5.6M records      Parquet    Cleaned    Analytics   SQL Ready │

└─────────────────────────────────────────────────────────────────┘# 4. Start Spark consumer (new terminal)

cd /home/hung/Downloads/bigdata/football_project

┌─────────────────────────────────────────────────────────────────┐export $(cat .env | xargs)

│                    STREAMING PIPELINE                            │python src/streaming/live_events_consumer.py

├─────────────────────────────────────────────────────────────────┤

│  Kafka (Confluent)  →  Spark Streaming  →  PostgreSQL           │# 5. Access Superset Dashboard: http://localhost:8088 (admin/admin)

│    live-match-events    Bronze → Silver     HYBRID Schema       │#    Create dashboards (see SUPERSET_SETUP.md)

└─────────────────────────────────────────────────────────────────┘```

```

**See `LOCAL_SETUP.md` for complete local installation guide (no Docker)**

## 📦 Data Summary

## 📊 Key Features

### **Batch - Gold Layer (Analytics)**

| Table | Records | Description |- **Medallion Architecture**: Bronze (raw) → Silver (cleaned) → Gold (analytics)

|-------|---------|-------------|- **Match Events Layer**: 941K events from 10K matches (goals, shots, cards, corners) ⚽ **NEW**

| `player_analytics_360` | 92,671 | 360° player profiles |- **Real-Time Streaming**: Kafka + Spark Streaming for live match updates 🔴 **NEW**

| `player_form_metrics` | 88,375 | Goals, assists, per-90min rates |- **5 Gold Analytics Tables**: 403K records with comprehensive player metrics

| `market_value_trends` | 69,441 | Market value analysis |- **PostgreSQL Integration**: 18 tables, 6.5M records, 50+ optimized indexes

| `injury_risk_scores` | 34,561 | Injury risk assessment |- **Views & Materialized Views**: 8 views + 3 materialized views for fast analytics

| `transfer_intelligence` | 117,944 | Transfer history |- **Data Quality Validation**: 8 automated quality checks

- **Single Command Execution**: Complete pipeline in one Python script

### **Streaming - Live Matches**

| Table | Description |## 🏗️ Architecture

|-------|-------------|

| `football_matches` | Real-time match updates (HYBRID schema) |```mermaid

CSV Data (11 files, 5.6M records) + Events Data (941K events, 10K matches)

## 🛠️ Tech Stack    ↓

Bronze Layer (Parquet) - Raw ingestion

| Component | Technology |    ↓

|-----------|------------|Events Layer (Parquet) - Match events processing ⚽ NEW

| **Processing** | Apache Spark 4.0, PySpark |    ↓

| **Database** | PostgreSQL 14+ |Silver Layer (Parquet) - Data cleaning & standardization

| **Streaming** | Confluent Cloud Kafka |    ↓

| **Storage** | Parquet (columnar) |Gold Layer (Parquet) - Analytics aggregations

| **Language** | Python 3.11+ |    ↓

PostgreSQL Database - SQL analytics ready (Bronze/Silver/Gold/Events schemas)

## 📁 Project Structure    ↓

Views & Materialized Views - Optimized queries

```    ↓

football_project/Real-Time Streaming: API → Kafka → Spark → PostgreSQL (streaming schema) 🔴 NEW

├── run_pipeline.py                    # Batch pipeline orchestrator```

├── validate_data.py                   # Data quality validation

├── src/## 📦 Data Tables Summary

│   ├── bronze_layer.py               # CSV → Parquet

│   ├── silver_layer.py               # Data cleaning### **Gold Layer (Player Analytics)**

│   ├── gold_layer.py                 # Analytics aggregation| Table | Records | Description |

│   ├── data_quality_check.py         # Quality checks|-------|---------|-------------|

│   └── streaming/| `player_analytics_360` | 92,671 | Comprehensive 360° player profiles |

│       └── spark_streaming_upsert.py # Kafka → Postgres streaming| `player_form_metrics` | 88,375 | Performance statistics (goals, assists, per-90min rates) |

├── schema/| `market_value_trends` | 69,441 | Market value trends & volatility analysis |

│   ├── analytics_schema.sql          # Gold layer DDL| `injury_risk_scores` | 34,561 | Injury history & risk assessment |

│   ├── create_football_matches_hybrid.sql  # Streaming schema| `transfer_intelligence` | 117,944 | Transfer history & market intelligence |

│   ├── load_silver_to_postgres.py    # Silver loader

│   └── load_gold_to_postgres.py      # Gold loader### **Events Layer (Match Analytics)** ⚽ **NEW**

├── football-datasets/                 # Source data (Transfermarkt)| Table | Records | Description |

└── jars/|-------|---------|-------------|

    └── postgresql-42.7.1.jar         # JDBC driver| `match_info` | 10,113 | General match information (teams, scores, dates) |

```| `match_statistics` | 10,113 | Aggregated match stats (shots, corners, cards) |

| `player_event_statistics` | 8,421 | Player performance from events (goals, assists, shots) |

## 💻 Sample Queries

### **Streaming Layer (Real-Time)** � **NEW**

```sql| Table | Records | Description |

-- Top 10 players by overall score|-------|---------|-------------|

SELECT player_name, overall_player_score, peak_market_value| `live_events` | Dynamic | Real-time match updates from Kafka stream |

FROM analytics.player_analytics_360

ORDER BY overall_player_score DESC## �🔍 Views & Analytics

LIMIT 10;

### Regular Views (8 total)

-- Live matches from streaming- `vw_top_players` - Top 100 players by overall score

SELECT competition_name, home_team_name, away_team_name, - `vw_high_value_low_risk_players` - High-value players with low injury risk

       ft_home_goals || '-' || ft_away_goals as score, status- `vw_transfer_opportunities` - Best transfer targets

FROM football_matches- `events.vw_top_scorers` - Top goal scorers from events ⚽

WHERE status = 'IN_PLAY';- `events.vw_player_discipline` - Player discipline statistics ⚽

- `events.vw_high_scoring_matches` - Matches with 5+ goals ⚽

-- High-value low-risk players- `streaming.vw_current_live_matches` - Currently live matches 🔴

SELECT * FROM analytics.vw_high_value_low_risk_players LIMIT 10;- `streaming.vw_match_score_progression` - Score progression timeline 🔴

```

### Materialized Views (3 total)

## 📈 Pipeline Performance- `mvw_position_statistics` - Aggregated stats by player position

- `mvw_age_group_analysis` - Player statistics by age groups

| Layer | Duration | Records |- `events.mvw_league_statistics` - League-level aggregated statistics ⚽

|-------|----------|---------|

| Bronze | ~52s | 5,605,055 |## 💻 Sample Queries

| Silver | ~25s | 5,535,614 |

| Gold | ~11s | 402,992 |```sql

| Load to Postgres | ~45s | 471,109 |-- Top 10 players overall

| **Total** | **~2.5 min** | **5.6M+** |SELECT player_name, overall_player_score, peak_market_value

FROM analytics.player_analytics_360

## 🔧 ConfigurationORDER BY overall_player_score DESC

LIMIT 10;

### Database Connection

```python-- High-value low-risk players

host = 'localhost'SELECT * FROM analytics.vw_high_value_low_risk_players

database = 'football_analytics'LIMIT 10;

user = 'postgres'

password = 'your_password'-- Position statistics

port = 5432SELECT * FROM analytics.mvw_position_statistics

```ORDER BY total_players DESC;

```

### Kafka (Confluent Cloud)

```python## 🛠️ Tech Stack

bootstrap_servers = 'pkc-xxx.aws.confluent.cloud:9092'

topic = 'live-match-events'### **Batch Processing:**

# Credentials in environment variables- **Languages**: Python 3.11+

```- **Big Data**: Apache Spark (PySpark 3.5.0)

- **Database**: PostgreSQL 14+

## 📚 Documentation- **Storage**: Parquet (columnar format)

- **Data Volume**: 5.6M+ records, ~400K analytics records

| File | Description |

|------|-------------|### **Real-Time Streaming:**

| `CONFLUENT_CLOUD_SETUP.md` | Kafka streaming setup |- **Producer**: Apache NiFi 1.25.0 (visual data flow)

| `STREAMING_ARCHITECTURE.md` | Streaming system design |- **Message Queue**: Confluent Cloud Kafka (managed service)

| `PROJECT_OVERVIEW.md` | Complete documentation |- **Consumer**: Spark Structured Streaming

| `DATA_QUALITY.md` | Data quality rules |- **Visualization**: Apache Superset 3.0.0



---### **Infrastructure:**

- **Deployment**: Local installation (no Docker required)

**Made with ⚽ + 🐍 + 🐘**- **NiFi**: Apache NiFi 1.25.0 (local)

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
