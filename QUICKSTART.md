# ⚡ Quick Start Guide - Events & Streaming

## 🚀 3-Minute Setup

### **Step 1: Run Full Pipeline (includes Events)**

```bash
# Run complete ETL pipeline
python run_pipeline.py
```

**What happens:**
- Processes 92K players, 1.8M performances (existing)
- ✨ **NEW:** Processes 941K match events from 10K matches
- ✨ **NEW:** Creates player event statistics (goals, assists, shots)
- Loads everything to PostgreSQL
- Takes ~3 minutes

---

### **Step 2: Verify Events Data**

```bash
# Quick test
python test_events_integration.py
```

**OR connect to PostgreSQL:**

```bash
psql -U postgres -d football_analytics
```

```sql
-- Top 10 goal scorers
SELECT player_name, goals_scored, assists_provided, match_appearances
FROM events.player_event_statistics
ORDER BY goals_scored DESC
LIMIT 10;

-- High-scoring matches
SELECT home_team, home_goals, away_goals, away_team, match_date
FROM events.match_info
WHERE total_goals >= 5
ORDER BY total_goals DESC;

-- League statistics
SELECT * FROM events.mvw_league_statistics 
ORDER BY avg_goals_per_match DESC;
```

---

### **Step 3: Real-Time Streaming (Optional)**

#### **Start Infrastructure:**

```bash
# Start Kafka + Zookeeper + PostgreSQL
docker-compose -f docker-compose.streaming.yml up -d

# Check status
docker ps

# View Kafka UI
open http://localhost:8080
```

#### **Start Producer (Terminal 1):**

```bash
python src/streaming/live_events_producer.py
```

Output:
```
📡 Fetched 3 live matches
📤 Sent 3/3 events to Kafka
   🔴 Manchester United 1-0 Chelsea (Minute: 38)
```

#### **Start Consumer (Terminal 2):**

```bash
python src/streaming/live_events_consumer.py
```

Output:
```
📦 Batch 0: Processing 3 events
✅ Batch 0: 3 events written to PostgreSQL
⚽ 3 LIVE matches in this batch
```

#### **Query Live Data:**

```sql
-- Currently live matches
SELECT * FROM streaming.vw_current_live_matches;

-- Recent events
SELECT * FROM streaming.live_events 
WHERE event_timestamp > NOW() - INTERVAL '1 hour'
ORDER BY event_timestamp DESC;
```

---

## 📊 Key Tables

| Schema | Table | Records | Description |
|--------|-------|---------|-------------|
| **events** | match_info | 10,113 | Match general info |
| **events** | match_statistics | 10,113 | Shots, corners, cards |
| **events** | player_event_statistics | 8,421 | Player performance |
| **streaming** | live_events | Dynamic | Real-time updates |

---

## 🔍 Useful Views

```sql
-- Top scorers
SELECT * FROM events.vw_top_scorers LIMIT 10;

-- Player discipline
SELECT * FROM events.vw_player_discipline 
WHERE yellow_cards >= 5;

-- Currently live matches
SELECT * FROM streaming.vw_current_live_matches;
```

---

## 🛠️ Troubleshooting

### **Events not loaded?**

```bash
# Re-run events processing
python src/events_layer.py

# Re-load to PostgreSQL
python schema/load_events_to_postgres.py
```

### **Streaming not working?**

```bash
# Check Kafka running
docker ps | grep kafka

# Restart services
docker-compose -f docker-compose.streaming.yml restart

# Check logs
docker logs football-kafka
docker logs football-producer
```

### **PostgreSQL connection error?**

```bash
# Check PostgreSQL running
docker ps | grep postgres

# Verify connection
psql -U postgres -h localhost -d football_analytics -c "SELECT 1;"
```

---

## 📚 Full Documentation

- **EVENTS_STREAMING_GUIDE.md** - Complete guide (545 lines)
- **INTEGRATION_SUMMARY.md** - Technical details
- **README.md** - Project overview

---

## 🎯 Next Steps

1. ✅ Run pipeline: `python run_pipeline.py`
2. ✅ Query events data (see SQL above)
3. ✅ (Optional) Start streaming for live matches
4. ✅ Build dashboards (Grafana, Metabase, etc.)
5. ✅ Explore analytics (scouting, predictions, etc.)

---

**⚡ That's it! Your Football Analytics platform is ready with 941K events + real-time streaming!**
