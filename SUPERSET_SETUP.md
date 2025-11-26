# 📊 Apache Superset Dashboard Setup Guide

## 🎯 Overview

**Apache Superset** is a modern, enterprise-ready business intelligence web application used for data exploration and visualization.

This guide shows how to setup Superset to visualize football analytics data from PostgreSQL.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   VISUALIZATION STACK                            │
└─────────────────────────────────────────────────────────────────┘

PostgreSQL Database
├── Bronze Layer (raw data)
├── Silver Layer (cleaned data)
├── Gold Layer (analytics)
├── Events Layer (match events)
└── Streaming Layer (live data)
         ↓
    Apache Superset
    (http://localhost:8088)
         ↓
    Interactive Dashboards
    - Team Performance
    - Player Statistics
    - Match Analysis
    - League Comparisons
    - Live Match Tracking
```

---

## 🚀 Quick Start

### **Step 1: Start Superset**

```bash
cd /home/hung/Downloads/bigdata/football_project

# Start all services (NiFi, PostgreSQL, Superset)
docker-compose -f docker-compose.streaming.yml up -d

# Wait ~2 minutes for Superset to initialize
docker logs -f football-superset
```

### **Step 2: Access Superset Web UI**

```
URL: http://localhost:8088
Username: admin
Password: admin
```

### **Step 3: Connect to PostgreSQL Database**

1. **Click Settings (⚙️) → Database Connections**
2. **Click "+ DATABASE"**
3. **Select PostgreSQL**
4. **Configure connection:**
   ```
   Display Name: Football Analytics
   SQLAlchemy URI: postgresql://postgres:9281746356@postgres:5432/football_analytics
   ```
5. **Test Connection** → Should show "Connection looks good!"
6. **Click Connect**

---

## 📊 Creating Your First Dashboard

### **Step 1: Create Dataset**

1. **Go to Datasets → "+ DATASET"**
2. **Select:**
   - Database: `Football Analytics`
   - Schema: `gold`
   - Table: `team_season_stats`
3. **Click "Add Dataset and Create Chart"**

### **Step 2: Create Chart**

**Example: Top Scoring Teams**

1. **Chart Type:** Bar Chart
2. **Configuration:**
   ```
   Time Column: None
   Metrics: 
     - SUM(goals_scored)
   Group by:
     - team_name
   Sort by:
     - SUM(goals_scored) DESC
   Row limit: 10
   ```
3. **Click "Update Chart"**
4. **Click "Save" → Enter chart name: "Top 10 Scoring Teams"**

### **Step 3: Create Dashboard**

1. **Go to Dashboards → "+ DASHBOARD"**
2. **Name:** "Football Analytics Overview"
3. **Drag charts from left panel to canvas**
4. **Resize and arrange charts**
5. **Click "Save"**

---

## 🎨 Dashboard Ideas

### **1. Team Performance Dashboard**

**Charts:**
- **Bar Chart:** Goals Scored by Team
- **Line Chart:** Goals Trend Over Seasons
- **Pie Chart:** Win/Draw/Loss Distribution
- **Table:** Team Season Statistics

**Dataset:** `gold.team_season_stats`

**Metrics:**
- `goals_scored`
- `goals_conceded`
- `clean_sheets`
- `yellow_cards`
- `red_cards`

---

### **2. Player Statistics Dashboard**

**Charts:**
- **Bar Chart:** Top Goal Scorers
- **Scatter Plot:** Goals vs Assists
- **Bubble Chart:** Players by Position (size = market value)
- **Heat Map:** Player Performance by Age

**Dataset:** `silver.players`

**Metrics:**
- Player name, position, age
- Goals, assists, minutes played
- Market value

---

### **3. Match Analysis Dashboard**

**Charts:**
- **Time Series:** Goals per Match Over Time
- **Box Plot:** Score Distribution by Competition
- **Sankey Diagram:** Goal Flow (Home vs Away)
- **Funnel Chart:** Match Status Distribution

**Dataset:** `events.match_statistics`

**Metrics:**
- `total_shots`
- `shots_on_target`
- `corners`
- `fouls`
- `possession`

---

### **4. Live Match Tracking**

**Charts:**
- **Big Number:** Current Live Matches Count
- **Table:** Live Match Details (auto-refresh)
- **Timeline:** Match Events (goals, cards)
- **Gauge:** Match Progress (minutes played)

**Dataset:** `streaming.live_events`

**Features:**
- **Auto Refresh:** Set to 30 seconds
- **Filters:** Competition, team, status

---

## 🔧 Advanced Configuration

### **Custom SQL Queries**

Create custom datasets with SQL:

1. **Go to SQL Lab**
2. **Select Database:** Football Analytics
3. **Write query:**

```sql
-- Top scorers with team info
SELECT 
    p.player_name,
    p.age,
    p.position,
    t.team_name,
    pes.total_goals,
    pes.total_assists,
    pes.shots_accuracy
FROM events.player_event_statistics pes
JOIN silver.players p ON pes.player_id = p.player_id
JOIN silver.teams t ON p.current_team_id = t.team_id
WHERE pes.total_goals > 0
ORDER BY pes.total_goals DESC
LIMIT 20;
```

4. **Click "Save" → "Save as Dataset"**
5. **Use in charts**

---

### **Calculated Columns**

Add calculated fields to datasets:

1. **Go to Datasets → Select dataset → Edit**
2. **Click "Calculated Columns" tab**
3. **Add column:**

```sql
-- Goals per game ratio
CASE 
  WHEN matches_played > 0 
  THEN CAST(goals_scored AS FLOAT) / matches_played 
  ELSE 0 
END
```

4. **Save as:** `goals_per_game`

---

### **Filters & Parameters**

Add interactive filters:

1. **In Dashboard Edit mode**
2. **Add "Filter Box" chart**
3. **Configure filters:**
   - Season dropdown
   - Competition dropdown
   - Date range picker
   - Team search

4. **Apply to all charts in dashboard**

---

## 📈 Pre-built Queries

### **Query 1: Team Performance Summary**

```sql
SELECT 
    t.team_name,
    tss.season,
    tss.matches_played,
    tss.goals_scored,
    tss.goals_conceded,
    tss.clean_sheets,
    ROUND(CAST(tss.goals_scored AS FLOAT) / NULLIF(tss.matches_played, 0), 2) as goals_per_game,
    ROUND(CAST(tss.clean_sheets AS FLOAT) / NULLIF(tss.matches_played, 0) * 100, 2) as clean_sheet_pct
FROM gold.team_season_stats tss
JOIN silver.teams t ON tss.team_id = t.team_id
WHERE tss.season IN ('2023/2024', '2022/2023')
ORDER BY tss.season DESC, tss.goals_scored DESC;
```

---

### **Query 2: Top Players by Position**

```sql
WITH player_stats AS (
    SELECT 
        p.player_name,
        p.position,
        p.age,
        t.team_name,
        pes.total_goals,
        pes.total_assists,
        pes.shots_accuracy,
        ROW_NUMBER() OVER (PARTITION BY p.position ORDER BY pes.total_goals DESC) as rank
    FROM events.player_event_statistics pes
    JOIN silver.players p ON pes.player_id = p.player_id
    JOIN silver.teams t ON p.current_team_id = t.team_id
)
SELECT * FROM player_stats WHERE rank <= 5;
```

---

### **Query 3: Match Statistics Analysis**

```sql
SELECT 
    mi.competition_name,
    mi.home_team,
    mi.away_team,
    mi.home_score,
    mi.away_score,
    ms.total_shots_home,
    ms.total_shots_away,
    ms.shots_on_target_home,
    ms.shots_on_target_away,
    ms.possession_home,
    ms.possession_away,
    ROUND(CAST(ms.shots_on_target_home AS FLOAT) / NULLIF(ms.total_shots_home, 0) * 100, 2) as shot_accuracy_home,
    ROUND(CAST(ms.shots_on_target_away AS FLOAT) / NULLIF(ms.total_shots_away, 0) * 100, 2) as shot_accuracy_away
FROM events.match_info mi
JOIN events.match_statistics ms ON mi.id_odsp = ms.id_odsp
WHERE mi.home_score IS NOT NULL
ORDER BY mi.date_match DESC
LIMIT 100;
```

---

### **Query 4: Live Matches Overview**

```sql
SELECT 
    match_id,
    competition_name,
    home_team,
    away_team,
    home_score,
    away_score,
    match_status,
    matchday,
    DATE_TRUNC('minute', ingestion_time) as last_update,
    EXTRACT(EPOCH FROM (NOW() - ingestion_time))/60 as minutes_since_update
FROM streaming.live_events
WHERE match_status = 'IN_PLAY'
ORDER BY ingestion_time DESC;
```

---

## 🎨 Chart Types & Use Cases

| Chart Type | Best For | Example |
|------------|----------|---------|
| **Bar Chart** | Comparing categories | Top scorers, team rankings |
| **Line Chart** | Trends over time | Goals per season, performance trend |
| **Pie Chart** | Proportions | Win/loss ratio, position distribution |
| **Scatter Plot** | Correlations | Goals vs assists, age vs performance |
| **Heat Map** | Patterns in matrix | Player stats by age/position |
| **Table** | Detailed data | Full player stats, match results |
| **Big Number** | KPIs | Total goals, active players count |
| **Gauge** | Progress metrics | Match completion, target achievement |
| **Bubble Chart** | Multi-dimensional | Teams by goals/conceded/market value |
| **Sankey** | Flow analysis | Goal sources, player transfers |

---

## 🔒 Security & Access Control

### **Create Read-Only User**

```sql
-- In PostgreSQL
CREATE ROLE superset_viewer WITH LOGIN PASSWORD 'viewer123';
GRANT CONNECT ON DATABASE football_analytics TO superset_viewer;
GRANT USAGE ON SCHEMA gold, silver, events, streaming TO superset_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA gold, silver, events, streaming TO superset_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold, silver, events, streaming 
GRANT SELECT ON TABLES TO superset_viewer;
```

### **Update Superset Connection**

```
SQLAlchemy URI: postgresql://superset_viewer:viewer123@postgres:5432/football_analytics
```

---

## 🎯 Performance Optimization

### **1. Create Materialized Views**

```sql
-- Fast dashboard loading
CREATE MATERIALIZED VIEW gold.mv_dashboard_summary AS
SELECT 
    t.team_name,
    tss.season,
    tss.goals_scored,
    tss.goals_conceded,
    tss.matches_played
FROM gold.team_season_stats tss
JOIN silver.teams t ON tss.team_id = t.team_id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW gold.mv_dashboard_summary;
```

### **2. Enable Query Caching**

In Superset:
1. **Settings → Database → Edit**
2. **Enable "Cache timeout"**: 3600 seconds (1 hour)
3. **Enable "Allow run async"**

### **3. Create Indexes**

```sql
-- Speed up common queries
CREATE INDEX idx_team_season ON gold.team_season_stats(team_id, season);
CREATE INDEX idx_player_goals ON events.player_event_statistics(total_goals DESC);
CREATE INDEX idx_match_date ON events.match_info(date_match);
```

---

## 📱 Embedding Dashboards

### **Public Dashboard Link**

1. **Open Dashboard**
2. **Click Share (📤) → Copy permalink**
3. **Embed in webpage:**

```html
<iframe 
  src="http://localhost:8088/superset/dashboard/1/?standalone=true"
  width="100%" 
  height="600"
  frameborder="0">
</iframe>
```

### **Export Dashboard**

1. **Dashboard → More (⋮) → Export to ZIP**
2. **Share with team**
3. **Import on another Superset instance**

---

## 🐛 Troubleshooting

### **Issue: Can't connect to PostgreSQL**

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check connection from Superset container
docker exec -it football-superset bash
apt-get update && apt-get install -y postgresql-client
psql -h postgres -U postgres -d football_analytics -c "SELECT 1;"
```

**Solution:** Verify `DATABASE_HOST=postgres` in docker-compose.yml

---

### **Issue: Slow Dashboard Loading**

**Solutions:**
1. Enable query caching (Settings → Database)
2. Create materialized views for complex queries
3. Add indexes on frequently queried columns
4. Limit row counts in charts (use filters)
5. Use "Run async" for long queries

---

### **Issue: Charts Not Updating with New Data**

**Solutions:**
1. **Clear cache:** Settings → Clear cache
2. **Reduce cache timeout** in database settings
3. **Force refresh:** Click refresh icon in dashboard

---

## 📚 Useful Resources

- **Superset Documentation:** https://superset.apache.org/docs/intro
- **Chart Gallery:** https://superset.apache.org/docs/using-superset/exploring-data
- **SQL Lab Guide:** https://superset.apache.org/docs/using-superset/sql-lab

---

## 🎓 Next Steps

1. ✅ **Connect to database** (PostgreSQL)
2. ✅ **Create datasets** from gold/silver/events schemas
3. ✅ **Build charts** (start with bar/line charts)
4. ✅ **Create dashboards** (team performance, player stats)
5. ✅ **Add filters** for interactivity
6. ✅ **Schedule email reports** (Settings → Alerts & Reports)
7. ✅ **Share with team** (export dashboard ZIP)

---

## 💡 Tips & Best Practices

### **Dashboard Design:**
- ✅ Keep dashboards focused (one topic per dashboard)
- ✅ Use consistent color schemes
- ✅ Add clear titles and descriptions
- ✅ Provide context with annotations
- ✅ Use filters for user interactivity

### **Performance:**
- ✅ Limit row counts (use Top N filters)
- ✅ Enable caching for frequently viewed dashboards
- ✅ Use materialized views for complex aggregations
- ✅ Schedule heavy queries to run async

### **Data Quality:**
- ✅ Validate data in SQL Lab before creating charts
- ✅ Handle NULL values in calculations
- ✅ Add data quality checks in queries
- ✅ Document assumptions and calculations

---

## 🎉 Summary

**You now have:**
- ✅ Apache Superset running on http://localhost:8088
- ✅ Connected to Football Analytics PostgreSQL database
- ✅ Access to all data layers (Bronze/Silver/Gold/Events/Streaming)
- ✅ Pre-built SQL queries for common analyses
- ✅ Chart type recommendations
- ✅ Performance optimization tips

**Access URLs:**
- Superset UI: http://localhost:8088 (admin/admin)
- PostgreSQL: localhost:5432/football_analytics
- NiFi UI: https://localhost:8443/nifi

**Start creating beautiful dashboards! 📊**
