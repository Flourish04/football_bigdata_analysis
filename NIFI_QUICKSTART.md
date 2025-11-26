# 🚀 Quick Start: NiFi Producer Setup

## 📋 TL;DR - 5 Minutes Setup

```bash
# 1. Start NiFi
docker-compose -f docker-compose.streaming.yml up -d

# 2. Access NiFi Web UI
# URL: https://localhost:8443/nifi
# Username: admin
# Password: adminadmin123456

# 3. Build flow (drag & drop):
#    InvokeHTTP → EvaluateJsonPath → RouteOnAttribute → UpdateAttribute → PublishKafka

# 4. Start Spark consumer
export $(cat .env | xargs)
python src/streaming/live_events_consumer.py

# 5. Done! Monitor at https://localhost:8443/nifi
```

---

## 🎯 What is This?

**Apache NiFi** replaces the Python producer script with a **visual, no-code data flow** for ingesting Football-Data.org API data into Confluent Cloud Kafka.

### Before (Python):
```python
# Code-based producer
python src/streaming/live_events_producer.py
```

### After (NiFi):
```
Visual flow in web UI:
https://localhost:8443/nifi
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMING PIPELINE                            │
└─────────────────────────────────────────────────────────────────┘

Football-Data.org API
         │
         ↓
    Apache NiFi (localhost:8443)
    ┌──────────────────────────┐
    │  [InvokeHTTP]            │  Poll API every 30s
    │         ↓                │
    │  [EvaluateJsonPath]      │  Extract JSON fields
    │         ↓                │
    │  [RouteOnAttribute]      │  Filter IN_PLAY matches
    │         ↓                │
    │  [UpdateAttribute]       │  Add metadata
    │         ↓                │
    │  [PublishKafka]          │  Send to Confluent Cloud
    └──────────────────────────┘
         │ SASL_SSL
         ↓
    Confluent Cloud Kafka
    (pkc-xxxxx.confluent.cloud:9092)
         │
         ↓
    Spark Streaming Consumer
    (src/streaming/live_events_consumer.py)
         │
         ↓
    PostgreSQL
    (streaming.live_events)
```

---

## ✅ Prerequisites

1. **Confluent Cloud Account**:
   - Follow: [`CONFLUENT_CLOUD_SETUP.md`](./CONFLUENT_CLOUD_SETUP.md)
   - Get bootstrap servers, API key, API secret
   - Update `.env` file

2. **Docker & Docker Compose**:
   ```bash
   docker --version  # Should be 20.x+
   docker-compose --version  # Should be 1.29+
   ```

3. **PostgreSQL** (included in docker-compose):
   ```bash
   # Will start automatically with NiFi
   ```

---

## 🚀 Step-by-Step Setup

### **Step 1: Configure Environment**

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add these values (from Confluent Cloud):
```bash
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.ap-southeast-1.aws.confluent.cloud:9092
KAFKA_API_KEY=YOUR_CONFLUENT_API_KEY
KAFKA_API_SECRET=YOUR_CONFLUENT_API_SECRET
KAFKA_TOPIC=live-match-events

FOOTBALL_API_TOKEN=798a49800fe84474bc7858ca06434966
```

### **Step 2: Start Services**

```bash
cd /home/hung/Downloads/bigdata/football_project

# Start NiFi + PostgreSQL
docker-compose -f docker-compose.streaming.yml up -d

# Check status
docker-compose -f docker-compose.streaming.yml ps

# Expected output:
# NAME                IMAGE                     STATUS
# football-nifi       apache/nifi:1.25.0       Up (healthy)
# football-postgres   postgres:14-alpine       Up (healthy)
```

### **Step 3: Wait for NiFi to Start**

NiFi takes ~2 minutes to initialize:

```bash
# Watch logs
docker logs -f football-nifi

# Wait for this message:
# "NiFi has started. The UI is available at the following URLs:"
```

### **Step 4: Access NiFi Web UI**

```
URL: https://localhost:8443/nifi
Username: admin
Password: adminadmin123456
```

**Note**: Accept the self-signed certificate warning in your browser.

### **Step 5: Build NiFi Flow**

Follow the complete guide: **[`NIFI_SETUP_GUIDE.md`](./NIFI_SETUP_GUIDE.md)**

**Quick overview:**
1. **Add InvokeHTTP processor**:
   - Remote URL: `https://api.football-data.org/v4/matches?status=IN_PLAY`
   - Header: `X-Auth-Token: 798a49800fe84474bc7858ca06434966`
   - Schedule: `30 sec`

2. **Add EvaluateJsonPath processor**:
   - Extract: `match.id`, `match.homeTeam`, `match.awayTeam`, etc.

3. **Add RouteOnAttribute processor**:
   - Route: `live_match = ${match.status:equals('IN_PLAY')}`

4. **Add UpdateAttribute processor**:
   - Add: `source=nifi`, `ingestion.timestamp`, etc.

5. **Add PublishKafka processor**:
   - Brokers: `pkc-xxxxx.confluent.cloud:9092`
   - Security: `SASL_SSL`
   - Username: `YOUR_API_KEY`
   - Password: `YOUR_API_SECRET`
   - Topic: `live-match-events`

6. **Connect processors** (drag from one to another)

7. **Start all processors** (click Start button)

### **Step 6: Start Spark Consumer**

Open a new terminal:

```bash
cd /home/hung/Downloads/bigdata/football_project

# Load environment variables
export $(cat .env | xargs)

# Start Spark streaming consumer
python src/streaming/live_events_consumer.py

# You should see:
# ✅ Spark streaming consumer started
# ✅ Reading from Confluent Cloud Kafka
# ✅ Writing to PostgreSQL: streaming.live_events
```

### **Step 7: Verify Data Flow**

#### **In NiFi UI:**
- See numbers on connections (FlowFiles flowing)
- Check processor statistics (In/Out counts)
- Right-click connection → List queue → View FlowFile content

#### **In Confluent Cloud Console:**
```bash
# Login to: https://confluent.cloud/
# Navigate to: Cluster → Topics → live-match-events
# Click: Messages tab
# See: Real-time JSON messages
```

#### **In PostgreSQL:**
```bash
docker exec -it football-postgres psql -U postgres -d football_analytics

-- Check live events
SELECT * FROM streaming.live_events ORDER BY ingestion_time DESC LIMIT 10;

-- Count by competition
SELECT competition_name, COUNT(*) as match_count
FROM streaming.live_events
GROUP BY competition_name;

-- Exit
\q
```

---

## 📊 Monitoring

### **NiFi UI:**
- **Processor Stats**: Tasks/5min, In, Out, Read/Write
- **Connection Queues**: Queued FlowFiles, backpressure
- **Bulletin Board** (🔔): Errors, warnings, info
- **Data Provenance** (📊): Track event lineage

### **Confluent Cloud Console:**
```
https://confluent.cloud/
→ Cluster
→ Topics
→ live-match-events
→ Messages (real-time)
```

### **Spark Consumer Logs:**
```bash
# Monitor consumer output
tail -f logs/spark_consumer.log
```

---

## 🔧 Common Tasks

### **Stop Services:**
```bash
docker-compose -f docker-compose.streaming.yml down
```

### **Restart NiFi:**
```bash
docker-compose -f docker-compose.streaming.yml restart nifi
```

### **View NiFi Logs:**
```bash
docker logs -f football-nifi
```

### **Export NiFi Flow:**
1. Select all processors (Ctrl+A)
2. Right-click → Create template
3. Name: `Football-API-Flow`
4. Click Templates icon → Download

### **Import Flow Template:**
1. Click Upload Template icon (📤)
2. Select XML file
3. Drag Template icon to canvas
4. Select your template

---

## 🐛 Troubleshooting

### **Issue: NiFi won't start**
```bash
# Check port conflict
sudo lsof -i :8443

# View logs
docker logs football-nifi

# Solution: Change port in docker-compose.streaming.yml
ports:
  - "8444:8443"  # Use 8444 instead
```

### **Issue: Can't connect to Confluent Cloud**
```bash
# Verify credentials in .env
cat .env | grep KAFKA

# Test with kafka-console-producer
docker run -it confluentinc/cp-kafka:7.5.0 \
  kafka-console-producer \
  --broker-list $(grep KAFKA_BOOTSTRAP_SERVERS .env | cut -d '=' -f2) \
  --topic live-match-events \
  --producer-property security.protocol=SASL_SSL \
  --producer-property sasl.mechanism=PLAIN \
  --producer-property "sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username='$(grep KAFKA_API_KEY .env | cut -d '=' -f2)' password='$(grep KAFKA_API_SECRET .env | cut -d '=' -f2)';"
```

### **Issue: No data in NiFi flow**
- **Check API**: No live matches right now? Normal during off-hours
- **Test with SCHEDULED**: Change InvokeHTTP URL to `status=SCHEDULED`
- **Check rate limit**: API allows 10 requests/minute

### **Issue: High memory usage**
```yaml
# Edit docker-compose.streaming.yml
environment:
  NIFI_JVM_HEAP_INIT: 4g  # Increase from 2g
  NIFI_JVM_HEAP_MAX: 8g   # Increase from 4g
```

---

## 📚 Documentation

### **Complete Guides:**
1. **[`NIFI_SETUP_GUIDE.md`](./NIFI_SETUP_GUIDE.md)** - Detailed NiFi setup (1000+ lines)
2. **[`NIFI_ARCHITECTURE.md`](./NIFI_ARCHITECTURE.md)** - Architecture overview
3. **[`CONFLUENT_CLOUD_SETUP.md`](./CONFLUENT_CLOUD_SETUP.md)** - Confluent Cloud setup
4. **[`STREAMING_ARCHITECTURE.md`](./STREAMING_ARCHITECTURE.md)** - System design

### **Quick References:**
- NiFi UI: https://localhost:8443/nifi
- Confluent Console: https://confluent.cloud/
- NiFi Documentation: https://nifi.apache.org/docs.html
- Football-Data API: https://www.football-data.org/documentation/api

---

## 🎯 Advantages of NiFi

| Feature | Python Script | Apache NiFi |
|---------|---------------|-------------|
| **Development** | Write code | Drag & drop |
| **Monitoring** | Logs only | Real-time UI |
| **Debugging** | Print statements | Inspect data visually |
| **Configuration** | Code changes + restart | Update on-the-fly |
| **Error Handling** | Try-catch blocks | Visual routing |
| **Learning Curve** | Python + Kafka APIs | Visual interface |
| **Data Lineage** | Manual tracking | Built-in provenance |
| **Production** | Custom setup | Built-in HA/clustering |

---

## 🎓 Next Steps

### **Learning:**
1. ✅ Complete NiFi flow setup
2. ✅ Explore NiFi processors (200+ built-in)
3. ✅ Learn Jolt transformations
4. ✅ Setup alerting (PutEmail processor)

### **Production:**
1. ✅ Export flow template
2. ✅ Setup monitoring alerts
3. ✅ Configure error handling
4. ✅ Enable NiFi clustering (multi-node)
5. ✅ Setup LDAP authentication

### **Advanced:**
1. ✅ Multiple topics (route by match status)
2. ✅ Custom processors (Java)
3. ✅ Schema Registry integration
4. ✅ Data quality checks in flow

---

## 💡 Tips & Best Practices

### **Flow Design:**
- ✅ Use descriptive processor names
- ✅ Add labels/comments for complex logic
- ✅ Group related processors
- ✅ Keep processors simple (single responsibility)

### **Performance:**
- ✅ Use compression (gzip)
- ✅ Adjust concurrent tasks based on load
- ✅ Monitor queue sizes
- ✅ Increase back pressure thresholds

### **Security:**
- ✅ Use environment variables for credentials
- ✅ Enable SSL for all connections
- ✅ Rotate API keys regularly
- ✅ Setup LDAP/AD for teams

### **Maintenance:**
- ✅ Export flow templates regularly
- ✅ Document custom processors
- ✅ Setup monitoring alerts
- ✅ Keep NiFi version updated

---

## 🎉 Summary

**You've built:**
- ✅ Apache NiFi visual producer
- ✅ Confluent Cloud Kafka integration
- ✅ Real-time streaming pipeline
- ✅ PostgreSQL data storage

**Key benefits:**
- 🎨 Visual flow design (no coding)
- 📊 Real-time monitoring
- 🔍 Data provenance
- 🛡️ Built-in error handling
- ⚡ Production-ready

**Access URLs:**
- NiFi: https://localhost:8443/nifi (admin/adminadmin123456)
- Confluent: https://confluent.cloud/
- PostgreSQL: localhost:5432/football_analytics

---

**Ready to stream! 🚀**

For detailed setup, see: [`NIFI_SETUP_GUIDE.md`](./NIFI_SETUP_GUIDE.md)
