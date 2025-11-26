# PostgreSQL Analytics Schema

## Overview

This directory contains the PostgreSQL DDL (Data Definition Language) schema for the Football Analytics Data Warehouse. The schema is designed to store and query Gold Layer analytics data produced by the PySpark ETL pipeline.

## Files

- **analytics_schema.sql** - Complete DDL script for creating all analytics tables, views, and indexes

## Schema Structure

### Analytics Schema (`analytics`)

The analytics schema contains 5 main tables and several supporting views:

#### Main Tables

1. **player_form_metrics** (92K rows expected)
   - Aggregated player performance metrics across all seasons
   - Key metrics: goals, assists, appearances, per-90-minute stats
   - Primary Key: `player_id`

2. **market_value_trends** (69K rows expected)
   - Player market value trends and volatility analysis
   - Key metrics: peak value, average value, volatility, latest valuation
   - Primary Key: `player_id`

3. **injury_risk_scores** (30K rows expected)
   - Player injury history and risk assessment
   - Key metrics: total injuries, days missed, severity score, risk level
   - Primary Key: `player_id`

4. **transfer_intelligence** (69K rows expected)
   - Player transfer history and market intelligence
   - Key metrics: total transfers, transfer fees, value trends
   - Primary Key: `player_id`

5. **player_analytics_360** (92K rows expected)
   - Comprehensive 360-degree player analytics (master table)
   - Combines profile + all analytics metrics
   - Includes composite scores (0-100 scale) and rankings
   - Primary Key: `player_id`

#### Views

1. **vw_top_players** - Top 100 players by overall score
2. **vw_high_value_low_risk_players** - High-value players (>10M EUR) with low injury risk
3. **vw_transfer_opportunities** - Players with positive transfer trends

#### Materialized Views

1. **mvw_position_statistics** - Aggregated statistics by player position
2. **mvw_age_group_analysis** - Player statistics grouped by age ranges

## Installation

### Prerequisites

- PostgreSQL 12+ installed
- Database created: `football_analytics` (or your preferred name)
- User with CREATE privileges

### Step 1: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE football_analytics;

# Connect to the new database
\c football_analytics
```

### Step 2: Run Schema Script

```bash
# From project root directory
psql -U postgres -d football_analytics -f schema/analytics_schema.sql
```

Or from within psql:

```sql
\i schema/analytics_schema.sql
```

### Step 3: Verify Installation

```sql
-- List all tables in analytics schema
\dt analytics.*

-- Check table structures
\d+ analytics.player_analytics_360

-- Verify indexes
\di analytics.*

-- Check views
\dv analytics.*

-- Check materialized views
\dm analytics.*
```

## Usage Examples

### Query Top Players

```sql
-- Top 10 players by overall score
SELECT 
    player_name,
    age,
    player_main_position,
    overall_player_score,
    peak_market_value,
    total_goals,
    injury_risk_level
FROM analytics.vw_top_players
LIMIT 10;
```

### Find Transfer Opportunities

```sql
-- Young talents with low injury risk
SELECT *
FROM analytics.vw_transfer_opportunities
WHERE age < 25
ORDER BY overall_player_score DESC
LIMIT 20;
```

### Position Analysis

```sql
-- Average stats by position
SELECT *
FROM analytics.mvw_position_statistics
ORDER BY avg_overall_score DESC;
```

### High Scorers with Low Injury Risk

```sql
-- Reliable goal scorers
SELECT 
    pa.player_name,
    pa.age,
    pa.player_main_position,
    fm.total_goals,
    fm.goals_per_90min,
    irs.injury_risk_level,
    mv.peak_market_value
FROM analytics.player_analytics_360 pa
JOIN analytics.player_form_metrics fm ON pa.player_id = fm.player_id
JOIN analytics.injury_risk_scores irs ON pa.player_id = irs.player_id
JOIN analytics.market_value_trends mv ON pa.player_id = mv.player_id
WHERE 
    fm.total_goals > 50
    AND irs.injury_risk_level = 'LOW'
ORDER BY fm.goals_per_90min DESC
LIMIT 20;
```

## Data Loading

### Using PySpark (Recommended)

The Gold Layer ETL pipeline includes a method to write directly to PostgreSQL:

```python
from gold_layer import GoldLayer

gold = GoldLayer(
    spark=spark,
    silver_path="/tmp/football_datalake/silver",
    gold_path="/tmp/football_datalake/gold",
    postgres_url="jdbc:postgresql://localhost:5432/football_analytics"
)

# Write specific table
df = gold.calculate_player_form_metrics()
gold.write_to_postgres(df, "player_form_metrics")

# Or process all tables
gold.process_all_tables()
```

### Using psql COPY (For CSV files)

```sql
-- If you have CSV exports from Spark
\COPY analytics.player_form_metrics FROM 'player_form_metrics.csv' WITH (FORMAT csv, HEADER true);
```

### Using pg_bulkload (For large datasets)

```bash
# Install pg_bulkload extension
# Then bulk load Parquet exports converted to CSV
pg_bulkload -i load_config.ctl
```

## Maintenance

### Refresh Materialized Views

```sql
-- Refresh all materialized views
SELECT analytics.refresh_all_materialized_views();

-- Or refresh individually
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mvw_position_statistics;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mvw_age_group_analysis;
```

### Check Table Sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'analytics'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Row Counts

```sql
SELECT 
    'player_form_metrics' as table_name, COUNT(*) as row_count FROM analytics.player_form_metrics
UNION ALL
SELECT 'market_value_trends', COUNT(*) FROM analytics.market_value_trends
UNION ALL
SELECT 'injury_risk_scores', COUNT(*) FROM analytics.injury_risk_scores
UNION ALL
SELECT 'transfer_intelligence', COUNT(*) FROM analytics.transfer_intelligence
UNION ALL
SELECT 'player_analytics_360', COUNT(*) FROM analytics.player_analytics_360;
```

### Vacuum and Analyze

```sql
-- After loading data
VACUUM ANALYZE analytics.player_form_metrics;
VACUUM ANALYZE analytics.market_value_trends;
VACUUM ANALYZE analytics.injury_risk_scores;
VACUUM ANALYZE analytics.transfer_intelligence;
VACUUM ANALYZE analytics.player_analytics_360;
```

## Performance Tuning

### Recommended Settings

For optimal performance with ~5.6M source records (92K Gold records):

```sql
-- In postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 16MB

-- Enable parallel query execution
max_parallel_workers_per_gather = 4
```

### Index Strategy

The schema includes optimized indexes for:
- Primary key lookups (player_id)
- Sorting by scores/metrics (DESC indexes)
- Filtering by categories (injury_risk_level, position)
- Date-based queries (latest_valuation_timestamp, last_transfer_date)

### Query Optimization Tips

1. **Use views for complex joins** - Pre-defined views are optimized
2. **Filter early** - Apply WHERE clauses before JOINs when possible
3. **Use EXPLAIN ANALYZE** - Check query plans for slow queries
4. **Partition large tables** - Consider partitioning if data grows beyond 10M rows

## Backup and Restore

### Backup Schema and Data

```bash
# Backup entire analytics schema
pg_dump -U postgres -d football_analytics -n analytics -F c -f analytics_backup.dump

# Backup schema only (no data)
pg_dump -U postgres -d football_analytics -n analytics -s -f analytics_schema_backup.sql
```

### Restore

```bash
# Restore from custom format
pg_restore -U postgres -d football_analytics -c analytics_backup.dump

# Restore from SQL format
psql -U postgres -d football_analytics -f analytics_schema_backup.sql
```

## Troubleshooting

### Connection Issues

```bash
# Test PostgreSQL connection
psql -U postgres -h localhost -p 5432 -d football_analytics

# Check if PostgreSQL is running
systemctl status postgresql
```

### Permission Issues

```sql
-- Grant necessary permissions
GRANT USAGE ON SCHEMA analytics TO your_user;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO your_user;
GRANT SELECT ON ALL VIEWS IN SCHEMA analytics TO your_user;
```

### Slow Queries

```sql
-- Enable query logging
SET log_min_duration_statement = 1000; -- Log queries > 1s

-- Check slow queries
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

## Integration with ETL Pipeline

### Pipeline Flow

```
Bronze Layer (Parquet)
    ↓
Silver Layer (Parquet, cleaned)
    ↓
Gold Layer (Parquet, analytics) → PostgreSQL (analytics schema)
    ↓
BI Tools / Applications
```

### Loading from Gold Layer

After running the Gold Layer ETL:

```bash
# 1. Run Bronze Layer
python src/bronze_layer.py

# 2. Run Silver Layer
python src/silver_layer.py

# 3. Run Gold Layer (creates Parquet files)
python src/gold_layer.py

# 4. Load into PostgreSQL (configure in gold_layer.py)
# Option 1: Automatic via gold_layer.py write_to_postgres()
# Option 2: Manual export/import via CSV
# Option 3: Use external ETL tool (Apache Airflow, dbt, etc.)
```

## Data Dictionary

See inline comments in `analytics_schema.sql` for detailed column descriptions and constraints.

Key field descriptions:

- **player_id**: Unique identifier for each player (BIGINT)
- **overall_player_score**: Composite score 0-100 combining performance, market, health
- **injury_risk_level**: Categorized as LOW (<= 2), MEDIUM (2-5), HIGH (> 5)
- **transfer_value_trend**: PROFIT if fees > avg value, else LOSS
- **goals_per_90min**: Goals scored per 90 minutes played
- **value_volatility**: Difference between peak and lowest market value

## Future Enhancements

Potential schema improvements:

1. **Time-series partitioning** - Partition by season_year for historical analysis
2. **Additional indexes** - Based on actual query patterns
3. **Stored procedures** - For complex business logic
4. **Triggers** - For data validation and audit logging
5. **Additional materialized views** - For common aggregations

## Support

For issues or questions:
- Check ETL pipeline logs: `/tmp/football_etl.log`
- Review PostgreSQL logs: `/var/log/postgresql/`
- Consult project README: `../README.md`

## License

This schema is part of the Football Analytics project. See main project LICENSE for details.
