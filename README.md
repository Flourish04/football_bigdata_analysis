# ⚽ Football Analytics Data Platform

A production-grade **Big Data ETL pipeline** for football (soccer) player analytics, implementing the **Medallion Architecture** (Bronze → Silver → Gold) with PySpark and PostgreSQL.

## 🚀 Quick Start

```bash
# Run full ETL pipeline (Bronze → Silver → Gold → PostgreSQL → Validation)
python run_pipeline.py
```

**Pipeline Runtime:** ~2.4 minutes  
**Total Records Processed:** 5.6M+ records

## 📊 Key Features

- **Medallion Architecture**: Bronze (raw) → Silver (cleaned) → Gold (analytics)
- **5 Gold Analytics Tables**: 403K records with comprehensive player metrics
- **PostgreSQL Integration**: 15 tables, 5.9M records, 35+ optimized indexes
- **Views & Materialized Views**: 3 views + 2 materialized views for fast analytics
- **Data Quality Validation**: 8 automated quality checks
- **Single Command Execution**: Complete pipeline in one Python script

## 🏗️ Architecture

```
CSV Data (11 files, 5.6M records)
    ↓
Bronze Layer (Parquet) - Raw ingestion
    ↓
Silver Layer (Parquet) - Data cleaning & standardization
    ↓
Gold Layer (Parquet) - Analytics aggregations
    ↓
PostgreSQL Database - SQL analytics ready
    ↓
Views & Materialized Views - Optimized queries
```

## 📦 Gold Layer Tables

| Table | Records | Description |
|-------|---------|-------------|
| `player_analytics_360` | 92,671 | Comprehensive 360° player profiles |
| `player_form_metrics` | 88,375 | Performance statistics (goals, assists, per-90min rates) |
| `market_value_trends` | 69,441 | Market value trends & volatility analysis |
| `injury_risk_scores` | 34,561 | Injury history & risk assessment |
| `transfer_intelligence` | 117,944 | Transfer history & market intelligence |

## 🔍 Views & Analytics

### Regular Views
- `vw_top_players` - Top 100 players by overall score
- `vw_high_value_low_risk_players` - High-value players with low injury risk
- `vw_transfer_opportunities` - Best transfer targets

### Materialized Views
- `mvw_position_statistics` - Aggregated stats by player position
- `mvw_age_group_analysis` - Player statistics by age groups

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

- **Languages**: Python 3.11+
- **Big Data**: Apache Spark (PySpark 3.5.0)
- **Database**: PostgreSQL 14+
- **Storage**: Parquet (columnar format)
- **Data Volume**: 5.6M+ records, ~400K analytics records

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

- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - Complete system documentation
- [DATA_QUALITY.md](DATA_QUALITY.md) - Data quality rules and validation

## 🎯 Use Cases

1. **Player Scouting**: Identify top performers by position, age, and value
2. **Transfer Analysis**: Find undervalued players with positive trends
3. **Injury Risk Assessment**: Evaluate player health and availability
4. **Market Intelligence**: Track transfer fees and value trends
5. **Performance Analytics**: Compare players across seasons and competitions

## 🔗 Related Projects

- Data Source: [Transfermarkt Football Dataset](https://www.transfermarkt.com/)
- Architecture: Medallion (Lakehouse) Pattern
- Query Engine: PostgreSQL + PySpark

## 📄 License

This project is for educational and analytical purposes.

---

**Made with ⚽ + 🐍 + 🐘**
