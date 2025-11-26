# ⚽ FOOTBALL DATA ANALYTICS - PROJECT OVERVIEW

**Date:** November 26, 2025  
**Architecture:** Hybrid (Parquet Data Lake + PostgreSQL Warehouse)  
**Data Volume:** 5.9M+ records | 935 MB PostgreSQL | 800 MB Parquet

---

## 📋 TABLE OF CONTENTS
1. [System Architecture](#-system-architecture)
2. [Quick Start](#-quick-start)
3. [Database Connection](#-database-connection)
4. [Data Validation](#-data-validation)
5. [Project Structure](#-project-structure)
6. [ETL Pipeline](#-etl-pipeline)
7. [Query Examples](#-query-examples)

---

## 🏗️ SYSTEM ARCHITECTURE

### **Hybrid Data Platform**

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                             │
│  11 CSV Files (Transfermarkt) → 5.6M records → 800 MB          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BRONZE LAYER (Raw Data)                       │
│  Location: /tmp/football_datalake/bronze/                       │
│  Format: Parquet | 11 tables | 5,605,055 records               │
│  - player_profiles, player_performances, player_market_value    │
│  - transfer_history, player_injuries, team_details, etc.        │
└────────────────┬────────────────────────────────────────────────┘
                 │ Data Cleaning & Validation
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SILVER LAYER (Clean Data)                       │
│  Location: /tmp/football_datalake/silver/                       │
│  Format: Parquet | 10 tables | 5,535,614 records               │
│  Loaded to PostgreSQL: silver_layer.* (10 tables, 5.5M rows)   │
└────────────────┬────────────────────────────────────────────────┘
                 │ Aggregations & Analytics
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                 GOLD LAYER (Analytics Ready)                     │
│  Location: /tmp/football_datalake/gold/                         │
│  Format: Parquet | 5 tables | 402,992 records                  │
│  Loaded to PostgreSQL: analytics.* (5 tables, 403K rows)       │
│  - player_analytics_360: Comprehensive player profiles          │
│  - player_form_metrics: Performance statistics                  │
│  - market_value_trends: Market analysis                         │
│  - injury_risk_scores: Health analytics                         │
│  - transfer_intelligence: Transfer market insights              │
└─────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              DUAL CONSUMPTION LAYER                              │
│                                                                  │
│  ┌─────────────────────────┐  ┌──────────────────────────┐    │
│  │  PostgreSQL Warehouse   │  │  Parquet Data Lake       │    │
│  │  localhost:5432         │  │  /tmp/football_datalake/ │    │
│  │  935 MB | 15 tables     │  │  800 MB | 26 tables      │    │
│  │  Use for: SQL queries   │  │  Use for: Spark ML       │    │
│  │  BI tools, dashboards   │  │  Big data processing     │    │
│  └─────────────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### **Why Hybrid Architecture?**

| Aspect | PostgreSQL Warehouse | Parquet Data Lake |
|--------|---------------------|-------------------|
| **Best For** | < 100K rows, SQL queries | > 1M rows, ML, analytics |
| **Speed** | 2-110ms (indexed) | Parallel processing |
| **Tools** | BI tools, Python, SQL | Spark, PySpark, ML |
| **Cost** | Higher (always running) | Lower (storage only) |
| **Use Cases** | Dashboards, reports | Data science, ML models |

**Strategy:** Use both systems based on query pattern!

---

## 🚀 QUICK START

### **1. Run Full ETL Pipeline**
```bash
cd /home/hung/Downloads/bigdata/football_project
python src/test_full_pipeline.py
```

**Output:**
- Bronze: 5.6M records
- Silver: 5.5M records  
- Gold: 403K records
- Duration: ~2-3 minutes

### **2. Query PostgreSQL**
```bash
PGPASSWORD=your_password psql -h localhost -U postgres -d football_analytics

-- Top 10 players
SELECT player_name, overall_player_score, peak_market_value
FROM analytics.player_analytics_360
ORDER BY overall_player_score DESC
LIMIT 10;

-- Use pre-built views
SELECT * FROM analytics.vw_top_players LIMIT 10;
SELECT * FROM analytics.vw_high_value_low_risk_players LIMIT 10;
SELECT * FROM analytics.mvw_position_statistics;
```

### **3. Query Parquet with Spark**
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName('FootballAnalysis').getOrCreate()

# Read Silver data
df = spark.read.parquet('/tmp/football_datalake/silver/player_performances')
df.filter("season_name = '2024'").groupBy('player_id').agg({'goals': 'sum'}).show()

spark.stop()
```

### **4. Validate Data Quality**
```bash
python validate_data.py
```

---

## 🔌 DATABASE CONNECTION

### **PostgreSQL Connection**
```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='football_analytics',
    user='postgres',
    password='your_password'
)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM analytics.player_analytics_360")
print(f"Players: {cursor.fetchone()[0]:,}")
conn.close()
```

### **Spark Connection**
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName('FootballAnalytics') \
    .config('spark.jars', './jars/postgresql-42.7.1.jar') \
    .getOrCreate()

# Read from PostgreSQL
df = spark.read \
    .format('jdbc') \
    .option('url', 'jdbc:postgresql://localhost:5432/football_analytics') \
    .option('dbtable', 'analytics.player_analytics_360') \
    .option('user', 'postgres') \
    .option('password', 'your_password') \
    .option('driver', 'org.postgresql.Driver') \
    .load()

df.show(5)
```

---

## ✅ DATA VALIDATION

### **Quick Health Check**
```sql
-- PostgreSQL
-- 1. Row counts
SELECT 
    'Silver' AS layer, 
    schemaname, 
    tablename, 
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'silver_layer'
UNION ALL
SELECT 
    'Gold' AS layer,
    schemaname, 
    tablename, 
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'analytics';

-- 2. Data quality checks
SELECT 
    'Unrealistic rates' AS check_name,
    COUNT(*) AS issues
FROM analytics.player_form_metrics
WHERE goals_per_90min > 3.0 OR assists_per_90min > 3.0
UNION ALL
SELECT 
    'NULL player names',
    COUNT(*)
FROM analytics.player_analytics_360
WHERE player_name IS NULL
UNION ALL
SELECT 
    'Negative market values',
    COUNT(*)
FROM analytics.market_value_trends
WHERE peak_market_value < 0;
```

**Expected Results:** All checks should return 0 issues

### **Data Quality Standards**

| Metric | Type | Precision | Valid Range |
|--------|------|-----------|-------------|
| goals_per_90min | NUMERIC(10,4) | 4 decimals | 0.0000 - 3.0000 |
| performance_score | NUMERIC(10,2) | 2 decimals | 0.00 - 100.00 |
| peak_market_value | BIGINT | No decimals | 0 - 500000000 |
| height | INTEGER | No decimals | 150 - 220 |
| age | INTEGER | No decimals | 14 - 80 |

---

## 📁 PROJECT STRUCTURE

```
football_project/
│
├── src/                          # ETL Pipeline Source Code
│   ├── bronze_layer.py          # Raw data ingestion (CSV → Parquet)
│   ├── silver_layer.py          # Data cleaning & transformation
│   ├── gold_layer.py            # Analytics aggregations
│   ├── data_cleaning.py         # Cleaning utilities
│   ├── data_quality_check.py    # Validation functions
│   └── test_full_pipeline.py    # Full ETL orchestration
│
├── schema/                       # Database Schema & Loading Scripts
│   ├── analytics_schema.sql     # Gold layer PostgreSQL schema
│   ├── load_silver_to_postgres.py  # Load Silver Parquet → PostgreSQL
│   ├── load_gold_to_postgres.py    # Load Gold Parquet → PostgreSQL
│   ├── create_silver_indexes.sql   # Performance indexes (35+)
│   └── README.md                # Schema documentation
│
├── football-datasets/            # Raw CSV Data (800 MB)
│   └── datalake/transfermarkt/  # 11 CSV files
│       ├── player_profiles/
│       ├── player_performances/
│       ├── player_market_value/
│       └── ... (8 more tables)
│
├── jars/                         # JDBC Drivers
│   └── postgresql-42.7.1.jar
│
├── validate_data.py              # Data validation script
├── docker-compose.yml            # PostgreSQL + pgAdmin setup
├── requirements.txt              # Python dependencies
└── PROJECT_OVERVIEW.md          # This file
```

---

## 🔄 ETL PIPELINE

### **Pipeline Flow**

```
CSV Files → Bronze Layer → Silver Layer → Gold Layer → PostgreSQL
            (Raw Data)   (Clean Data)   (Analytics)    (Warehouse)
```

### **1. Bronze Layer** (`src/bronze_layer.py`)
**Purpose:** Ingest raw CSV files to Parquet (no transformations)

**Process:**
- Read 11 CSV files from `football-datasets/`
- Minimal schema inference
- Write to `/tmp/football_datalake/bronze/`
- Duration: ~30 seconds

**Output:** 11 Parquet tables, 5,605,055 records

### **2. Silver Layer** (`src/silver_layer.py`)
**Purpose:** Clean, validate, deduplicate data

**Process:**
- Read Bronze Parquet files
- Apply cleaning rules:
  - Remove duplicates
  - Handle NULL values
  - Standardize date formats
  - Validate data types
  - Fix encoding issues
- Write to `/tmp/football_datalake/silver/`
- Duration: ~45 seconds

**Output:** 10 Parquet tables, 5,535,614 records

**Key Cleaning Rules:**
- Player names: Remove invalid characters, handle NULLs
- Dates: Convert to timestamp, handle legacy formats
- Numbers: Cast to proper types, handle negative values
- Duplicates: Keep latest record based on timestamp

### **3. Gold Layer** (`src/gold_layer.py`)
**Purpose:** Create analytics-ready aggregations

**Process:**
- Read Silver Parquet files
- Apply business logic:
  - Aggregate by player
  - Calculate metrics (per-90min rates, scores)
  - Join multiple tables
  - Create 360° player profiles
- Write to `/tmp/football_datalake/gold/`
- Duration: ~20 seconds

**Output:** 5 Parquet tables, 402,992 records

**Gold Tables:**

1. **player_analytics_360** (92,671 records)
   - Comprehensive player profiles
   - Combines performance, market, injury, transfer data
   - Scores: performance_score, market_score, health_score
   - Overall ranking with percentiles

2. **player_form_metrics** (88,375 records)
   - Season-by-season performance
   - Goals/assists per 90min (capped at 3.0)
   - Total appearances, yellow/red cards
   - Best season statistics

3. **market_value_trends** (69,441 records)
   - Peak/lowest/average market values
   - Value volatility analysis
   - Latest valuation timestamps

4. **injury_risk_scores** (34,561 records)
   - Total injuries and days missed
   - Average days/games per injury
   - Injury severity score (0-10)
   - Risk level: LOW/MEDIUM/HIGH

5. **transfer_intelligence** (117,944 records)
   - Total transfers and fees
   - Average/highest transfer fees
   - Transfer frequency score
   - Value trend: PROFIT/LOSS

### **4. PostgreSQL Load** (`schema/load_*_to_postgres.py`)
**Purpose:** Load Parquet to PostgreSQL for SQL queries

**Process:**
- Create schemas: `silver_layer`, `analytics`
- Read Parquet files with Spark
- Write to PostgreSQL with JDBC
- Create 35+ indexes for performance
- Duration: ~60 seconds (Silver) + ~30 seconds (Gold)

**Output:** 15 PostgreSQL tables, 5,938,606 records

### **5. Views & Materialized Views** (`schema/create_views.py`)
**Purpose:** Create optimized query views for common analytics

**Process:**
- Execute `schema/create_views_only.sql`
- Create 3 regular views for common queries
- Create 2 materialized views for aggregations
- Refresh materialized views with data
- Duration: ~1 second

**Views Created:**
1. **vw_top_players** (100 rows)
   - Top 100 players by overall score
   - Quick access to elite players

2. **vw_high_value_low_risk_players** (1,322 rows)
   - High-value players (>10M EUR)
   - Low injury risk, aged 20-30
   - Ideal transfer targets

3. **vw_transfer_opportunities** (1,754 rows)
   - Players with positive transfer trends
   - Strong performance + manageable risk
   - Age 20-28, profit-making transfers

**Materialized Views:**
1. **mvw_position_statistics** (18 rows)
   - Aggregated stats by player position
   - Average scores, values, goals per position

2. **mvw_age_group_analysis** (5 rows)
   - Player statistics grouped by age ranges
   - U21, 21-25, 26-30, 31-35, 35+

**Refresh Function:**
- `refresh_all_materialized_views()` to update MVs

---

## 📊 QUERY EXAMPLES

### **PostgreSQL Queries**

#### **1. Top 10 Players Overall**
```sql
SELECT 
    player_rank,
    player_name,
    player_main_position,
    overall_player_score,
    performance_score,
    market_score,
    health_score,
    peak_market_value,
    total_goals
FROM analytics.player_analytics_360
ORDER BY overall_player_score DESC
LIMIT 10;
```

#### **2. Best Attackers by Goals/90min**
```sql
SELECT 
    p.player_name,
    f.goals_per_90min,
    f.assists_per_90min,
    f.total_goals,
    f.total_appearances,
    p.peak_market_value
FROM analytics.player_form_metrics f
JOIN analytics.player_analytics_360 p USING (player_id)
WHERE f.goals_per_90min >= 0.5
  AND f.total_appearances >= 50
ORDER BY f.goals_per_90min DESC
LIMIT 20;
```

#### **3. Injury-Prone High-Value Players**
```sql
SELECT 
    p.player_name,
    p.peak_market_value,
    i.total_injuries,
    i.total_days_missed,
    i.injury_severity_score,
    i.injury_risk_level
FROM analytics.player_analytics_360 p
JOIN analytics.injury_risk_scores i USING (player_id)
WHERE p.peak_market_value > 50000000
  AND i.injury_risk_level = 'HIGH'
ORDER BY p.peak_market_value DESC;
```

#### **4. Transfer Market Analysis**
```sql
SELECT 
    p.player_name,
    p.player_main_position,
    t.total_transfers,
    t.total_transfer_fees,
    t.highest_transfer_fee,
    t.transfer_value_trend,
    p.peak_market_value
FROM analytics.player_analytics_360 p
JOIN analytics.transfer_intelligence t USING (player_id)
WHERE t.total_transfer_fees > 100000000
ORDER BY t.total_transfer_fees DESC
LIMIT 15;
```

#### **5. Market Value vs Performance**
```sql
SELECT 
    CASE 
        WHEN peak_market_value >= 100000000 THEN '100M+'
        WHEN peak_market_value >= 50000000 THEN '50-100M'
        WHEN peak_market_value >= 20000000 THEN '20-50M'
        ELSE '<20M'
    END AS value_tier,
    COUNT(*) AS players,
    AVG(performance_score) AS avg_performance,
    AVG(goals_per_90min) AS avg_goals_90,
    AVG(assists_per_90min) AS avg_assists_90
FROM analytics.player_analytics_360
WHERE goals_per_90min IS NOT NULL
GROUP BY value_tier
ORDER BY 
    CASE value_tier
        WHEN '100M+' THEN 1
        WHEN '50-100M' THEN 2
        WHEN '20-50M' THEN 3
        ELSE 4
    END;
```

### **Spark/Parquet Queries**

#### **1. Season Analysis**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum, avg, count

spark = SparkSession.builder.appName('SeasonAnalysis').getOrCreate()

df = spark.read.parquet('/tmp/football_datalake/silver/player_performances')

# Top scorers by season
season_stats = df.groupBy('season_name') \
    .agg(
        count('*').alias('matches'),
        sum('goals').alias('total_goals'),
        avg('goals').alias('avg_goals')
    ) \
    .orderBy('season_name', ascending=False)

season_stats.show(10)
spark.stop()
```

#### **2. Team Performance**
```python
from pyspark.sql.functions import col, desc

spark = SparkSession.builder.appName('TeamAnalysis').getOrCreate()

perf = spark.read.parquet('/tmp/football_datalake/silver/player_performances')
teams = spark.read.parquet('/tmp/football_datalake/silver/team_details')

# Join and aggregate
team_stats = perf.join(teams, perf.club_id == teams.team_id) \
    .groupBy('team_name') \
    .agg(
        sum('goals').alias('total_goals'),
        count('*').alias('matches')
    ) \
    .orderBy(desc('total_goals'))

team_stats.show(20)
spark.stop()
```

---

## 🔧 MAINTENANCE

### **Refresh Data**
```bash
# Full pipeline refresh
python src/test_full_pipeline.py

# Specific layer only
python -c "
from src.bronze_layer import BronzeLayer
bronze = BronzeLayer()
bronze.process_all_datasets()
"
```

### **Rebuild Indexes**
```bash
PGPASSWORD=your_password psql -h localhost -U postgres -d football_analytics \
  -f schema/create_silver_indexes.sql
```

### **Database Size Check**
```sql
SELECT 
    pg_size_pretty(pg_database_size('football_analytics')) AS total_size,
    (SELECT COUNT(*) FROM information_schema.tables 
     WHERE table_schema IN ('silver_layer', 'analytics')) AS total_tables;
```

### **Parquet Size Check**
```bash
du -sh /tmp/football_datalake/bronze/
du -sh /tmp/football_datalake/silver/
du -sh /tmp/football_datalake/gold/
```

---

## 📈 PERFORMANCE METRICS

| Operation | Duration | Records | Throughput |
|-----------|----------|---------|------------|
| CSV → Bronze | 30s | 5.6M | 187K records/s |
| Bronze → Silver | 45s | 5.5M | 123K records/s |
| Silver → Gold | 20s | 403K | 20K records/s |
| Parquet → PostgreSQL | 90s | 5.9M | 66K records/s |
| **Total Pipeline** | **3 min** | **5.9M** | **33K records/s** |

### **Query Performance (with indexes)**
- Simple lookup (player_id): 2-5 ms
- Aggregation (<100K rows): 10-50 ms  
- Join query: 20-100 ms
- Full table scan (5M rows): 1-3 seconds

---

## 🎯 USE CASES

### **1. Player Scouting**
```sql
-- Find undervalued high-performers
SELECT player_name, overall_player_score, peak_market_value
FROM analytics.player_analytics_360
WHERE performance_score >= 90
  AND peak_market_value < 30000000
  AND injury_risk_level = 'LOW'
ORDER BY performance_score DESC;
```

### **2. Transfer Strategy**
```sql
-- Players with good resale value
SELECT p.player_name, t.total_transfer_fees, t.transfer_value_trend
FROM analytics.transfer_intelligence t
JOIN analytics.player_analytics_360 p USING (player_id)
WHERE t.transfer_value_trend = 'PROFIT'
  AND p.age BETWEEN 20 AND 27
ORDER BY t.total_transfer_fees DESC;
```

### **3. Risk Analysis**
```sql
-- High-value injury-prone players
SELECT player_name, peak_market_value, injury_severity_score
FROM analytics.player_analytics_360
WHERE peak_market_value > 80000000
  AND injury_risk_level IN ('MEDIUM', 'HIGH')
ORDER BY peak_market_value DESC;
```

---

## 📞 SUPPORT & REFERENCES

- **Data Location:** `/tmp/football_datalake/`
- **Database:** `localhost:5432/football_analytics`
- **User:** `postgres`
- **Password:** Use `.env` file (see `.env.example`)
- **Schema Docs:** `schema/README.md`
- **Data Quality:** `DATA_QUALITY.md`

---

**Last Updated:** November 26, 2025  
**Status:** ✅ Production Ready  
**Total Records:** 5,938,606  
**Database Size:** 935 MB  
**Parquet Size:** 800 MB
