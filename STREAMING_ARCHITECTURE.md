# ⚡ Football Live Score Streaming Architecture

## 📊 Kiến trúc tổng quan

```
Football-Data.org API
        ↓
Apache NiFi (Visual Producer)
- InvokeHTTP
- EvaluateJsonPath
- RouteOnAttribute
- PublishKafka
        ↓
Confluent Cloud Kafka
(Managed Service)
        ↓
Spark Structured Streaming (Consumer)
        ↓
┌───────────────────────────┐
│  Real-time Processing     │
│  - Match events           │
│  - Live scores            │
│  - Player statistics      │
│  - Team performance       │
└───────────────────────────┘
        ↓
    ┌───────┴───────┐
    ↓               ↓
PostgreSQL      Parquet
(Hot data)      (Cold storage)
    ↓
Dashboard/Analytics
```

## 🎯 Architecture Components

### **1. Apache NiFi (Producer)**
- **Role**: Visual data ingestion from Football-Data.org API
- **URL**: https://localhost:8443/nifi
- **Features**:
  - Drag-and-drop flow design
  - Real-time monitoring
  - Data provenance tracking
  - Built-in error handling
  - SASL/SSL authentication to Confluent Cloud

### **2. Confluent Cloud Kafka**
- **Role**: Managed Kafka cluster for event streaming
- **URL**: https://confluent.cloud/
- **Features**:
  - Fully managed (no Zookeeper/broker setup)
  - Auto-scaling
  - Built-in monitoring
  - High availability
  - $400 FREE credits (~1000+ months usage)

### **3. Spark Structured Streaming (Consumer)**
- **Role**: Process Kafka events and write to PostgreSQL
- **Script**: `src/streaming/live_events_consumer.py`
- **Features**:
  - Real-time stream processing
  - SASL/SSL Kafka authentication
  - Automatic checkpoint recovery
  - Schema validation

### **4. PostgreSQL**
- **Role**: Store streaming data
- **Schema**: `streaming.live_events`
- **Features**:
  - ACID compliance
  - Indexed for fast queries
  - Views for analytics

## 🔌 Nguồn dữ liệu đề xuất

### 1. **API-Football (RapidAPI)** ⭐ Khuyên dùng
- **URL**: https://www.api-football.com/
- **Features**: 
  - Live scores real-time
  - Match events (goals, cards, substitutions)
  - Player statistics during match
  - Line-ups and formations
  - 100 requests/day (Free tier)
- **Websocket**: Có hỗ trợ
- **Pricing**: Free tier + Paid plans

### 2. **Football-Data.org**
- **URL**: https://www.football-data.org/
- **Features**:
  - Live scores
  - Match statistics
  - 10 requests/minute (Free)
- **Format**: REST API
- **Pricing**: Free tier available

### 3. **LiveScore API** (Unofficial)
- **URL**: https://github.com/Dmitrii-I/livescore-api
- **Features**: Free, unofficial scraping
- **Note**: Không ổn định lắm

### 4. **TheSportsDB API** 
- **URL**: https://www.thesportsdb.com/api.php
- **Features**: Free, live scores
- **Limitation**: Delay ~1-2 minutes

### 5. **SofaScore API** (Unofficial)
- Real-time data
- Phải reverse-engineer
- Risk: Có thể bị block

## 🏗️ Kiến trúc chi tiết

### **Phase 1: Data Ingestion Layer**

```python
# Kafka Producer - API Polling
┌─────────────────────────────────┐
│  API Football Client            │
│  ├── Poll every 30-60 seconds   │
│  ├── Get live matches           │
│  ├── Get match events           │
│  └── Get player stats           │
└─────────────────────────────────┘
            ↓
┌─────────────────────────────────┐
│  Kafka Topics                   │
│  ├── live-matches              │
│  ├── match-events              │
│  ├── player-live-stats         │
│  └── team-live-stats           │
└─────────────────────────────────┘
```

### **Phase 2: Stream Processing**

```python
# Spark Structured Streaming
┌─────────────────────────────────┐
│  Kafka → Spark Stream           │
│  ├── Window aggregations       │
│  ├── State management          │
│  ├── Event-time processing     │
│  └── Watermark handling        │
└─────────────────────────────────┘
            ↓
┌─────────────────────────────────┐
│  Real-time Analytics            │
│  ├── Live scoreboard           │
│  ├── Player performance        │
│  ├── Team momentum             │
│  └── Match predictions         │
└─────────────────────────────────┘
```

### **Phase 3: Storage & Serving**

```python
# Dual Storage Strategy
┌──────────────────┐  ┌──────────────────┐
│  PostgreSQL      │  │  Parquet Files   │
│  (Hot Storage)   │  │  (Cold Storage)  │
│  - Last 7 days   │  │  - Historical    │
│  - Active matches│  │  - Batch analysis│
└──────────────────┘  └──────────────────┘
         ↓                      ↓
    ┌────────────────────────────┐
    │   Query Layer / Dashboard  │
    └────────────────────────────┘
```

## 📋 Kafka Topics Schema

### 1. Topic: `live-matches`
```json
{
  "match_id": "12345",
  "timestamp": "2025-11-26T15:30:00Z",
  "competition": "Premier League",
  "home_team": "Arsenal",
  "away_team": "Chelsea",
  "home_score": 2,
  "away_score": 1,
  "status": "LIVE",
  "minute": 67,
  "added_time": null
}
```

### 2. Topic: `match-events`
```json
{
  "match_id": "12345",
  "timestamp": "2025-11-26T15:42:15Z",
  "event_type": "GOAL",
  "minute": 67,
  "team": "Arsenal",
  "player_id": "98765",
  "player_name": "Bukayo Saka",
  "assist_player_id": "12340",
  "description": "Right footed shot from the centre"
}
```

### 3. Topic: `player-live-stats`
```json
{
  "match_id": "12345",
  "player_id": "98765",
  "timestamp": "2025-11-26T15:45:00Z",
  "shots": 3,
  "shots_on_target": 2,
  "goals": 1,
  "assists": 0,
  "passes_completed": 45,
  "pass_accuracy": 87.5,
  "tackles": 2,
  "interceptions": 1
}
```

## 🔄 Luồng thực thi (Execution Flow)

### **Step 1: Setup Kafka**
```bash
# Start Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Start Kafka
bin/kafka-server-start.sh config/server.properties

# Create topics
bin/kafka-topics.sh --create --topic live-matches --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic match-events --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic player-live-stats --bootstrap-server localhost:9092
```

### **Step 2: Start Kafka Producer**
```bash
# API → Kafka
python src/streaming/kafka_producer_live_matches.py
```

### **Step 3: Start Spark Streaming**
```bash
# Kafka → Spark → PostgreSQL/Parquet
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  src/streaming/spark_streaming_consumer.py
```

### **Step 4: Start Dashboard**
```bash
# Real-time visualization
streamlit run src/streaming/live_dashboard.py
```

## 🛠️ Tech Stack

### Core Components
- **Apache Kafka**: Message broker
- **Spark Structured Streaming**: Stream processing
- **PostgreSQL**: Hot storage (real-time queries)
- **Parquet**: Cold storage (historical analysis)

### Additional Tools
- **Apache Superset**: Real-time dashboards with auto-refresh
- **Grafana**: Monitoring metrics (optional)
- **Local Installation**: All services run locally (no Docker required)

## 📊 Streaming Analytics Use Cases

### 1. **Live Scoreboard**
- Real-time scores across all matches
- Auto-refresh every 30 seconds
- Event notifications (goals, cards)

### 2. **Player Performance Tracking**
- Live xG (expected goals)
- Pass completion rates
- Heat maps during match

### 3. **Team Momentum Analysis**
- Shot frequency windows (5-min intervals)
- Possession trends
- Pressure indicators

### 4. **Match Predictions**
- Win probability updates
- Goal prediction based on xG
- Statistical trends

### 5. **Fantasy Football Updates**
- Live point calculations
- Player rankings during matches
- Transfer recommendations

## 🔐 API Authentication Example

### API-Football Setup
```python
import os
from dotenv import load_dotenv

load_dotenv()

API_CONFIG = {
    'host': 'api-football-v1.p.rapidapi.com',
    'key': os.getenv('RAPID_API_KEY'),
    'base_url': 'https://api-football-v1.p.rapidapi.com/v3'
}

headers = {
    'X-RapidAPI-Key': API_CONFIG['key'],
    'X-RapidAPI-Host': API_CONFIG['host']
}
```

## 📈 Performance Considerations

### Polling Strategy
- **High-priority matches**: Poll every 30s
- **Regular matches**: Poll every 60s
- **Pre-match/Post-match**: Poll every 5 minutes

### Spark Streaming Tuning
```python
spark.conf.set("spark.streaming.kafka.maxRatePerPartition", 1000)
spark.conf.set("spark.streaming.backpressure.enabled", True)
spark.conf.set("spark.sql.streaming.metricsEnabled", True)
```

### Data Retention
- **Hot storage (PostgreSQL)**: 7 days
- **Cold storage (Parquet)**: Unlimited
- **Kafka retention**: 24 hours

## 🎯 Implementation Phases

### **Phase 1: POC (1-2 weeks)**
- ✅ Setup Kafka locally
- ✅ Implement simple producer (1 API)
- ✅ Basic Spark consumer
- ✅ Write to console/file

### **Phase 2: MVP (2-3 weeks)**
- ✅ Multiple Kafka topics
- ✅ Structured Streaming with windows
- ✅ PostgreSQL integration
- ✅ Basic dashboard

### **Phase 3: Production (3-4 weeks)**
- ✅ Error handling & monitoring
- ✅ State management & checkpointing
- ✅ Auto-scaling
- ✅ Advanced analytics
- ✅ Real-time alerts

## 💰 Cost Estimation (Monthly)

### Free Tier Setup
- API-Football Free: $0 (100 req/day)
- Kafka (Self-hosted): $0
- Spark (Local): $0
- PostgreSQL (Local): $0
- **Total**: $0/month

### Production Setup
- API-Football Pro: $30-100/month
- AWS MSK (Kafka): $300/month
- EMR (Spark): $500/month
- RDS PostgreSQL: $200/month
- **Total**: ~$1,030-1,100/month

## 🔗 Integration with Existing Pipeline

```python
# Kết hợp Batch + Streaming
┌─────────────────────────────┐
│   Batch Layer (Existing)    │
│   - Historical data         │
│   - Daily aggregations      │
│   - Bronze → Silver → Gold  │
└─────────────────────────────┘
            ↓
┌─────────────────────────────┐
│   Speed Layer (NEW)         │
│   - Real-time data          │
│   - Live aggregations       │
│   - Kafka → Spark Stream    │
└─────────────────────────────┘
            ↓
┌─────────────────────────────┐
│   Serving Layer             │
│   - Merge batch + stream    │
│   - Unified query interface │
│   - Lambda Architecture     │
└─────────────────────────────┘
```

## 📚 Next Steps

1. **Choose API provider** → Recommend API-Football
2. **Setup Kafka** → Docker Compose
3. **Implement producer** → Python + Kafka-Python
4. **Build Spark consumer** → Structured Streaming
5. **Create dashboard** → Streamlit
6. **Test with sample data** → Mock API responses
7. **Deploy to production** → AWS/Azure

## 🔧 Development Environment

```yaml
# docker-compose.yml for streaming stack
version: '3.8'
services:
  # Using Confluent Cloud for managed Kafka (no local Kafka/Zookeeper needed)
  postgres:
    image: postgres:14
  nifi:
    image: apache/nifi:1.25.0
  superset:
    # Installed locally via pip (see LOCAL_SETUP.md)
```

---

**Ready to implement?** 🚀
