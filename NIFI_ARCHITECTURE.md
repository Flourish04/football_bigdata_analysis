# 🎯 NiFi Producer Architecture Summary

## 📋 Overview

This document summarizes the **Apache NiFi** integration as a visual data producer replacing the Python-based producer script.

---

## 🏗️ Architecture Comparison

### **Before (Python Producer):**
```
Football-Data.org API
         ↓
    Python Script (live_events_producer.py)
    - Manual HTTP requests
    - JSON parsing
    - Error handling code
    - Rate limiting logic
    - Retry mechanism
    - Logging
         ↓
    Confluent Cloud Kafka
         ↓
    Spark Consumer
         ↓
    PostgreSQL
```

### **After (NiFi Producer):**
```
Football-Data.org API
         ↓
    Apache NiFi (Visual Flow)
    - InvokeHTTP (built-in)
    - EvaluateJsonPath (visual)
    - RouteOnAttribute (drag-drop)
    - UpdateAttribute (metadata)
    - PublishKafka (configured)
    - Real-time monitoring
    - Data provenance
         ↓
    Confluent Cloud Kafka
         ↓
    Spark Consumer
         ↓
    PostgreSQL
```

---

## ✅ Benefits of NiFi Over Python

| Feature | Python Script | Apache NiFi |
|---------|---------------|-------------|
| **Development** | Code + debug | Drag & drop UI |
| **Visibility** | Logs only | Live flow visualization |
| **Monitoring** | Custom metrics | Built-in dashboards |
| **Error Handling** | Try-catch blocks | Visual error routing |
| **Data Lineage** | Manual tracking | Automatic provenance |
| **Backpressure** | Manual queues | Built-in queue management |
| **Configuration** | Code changes + restart | Update on-the-fly |
| **Debugging** | Print statements | Data inspection UI |
| **Learning Curve** | Python + Kafka APIs | Visual interface |
| **Production Ready** | Custom HA setup | Built-in clustering |

---

## 📊 NiFi Flow Design

### **Processor Pipeline:**

```
┌─────────────────┐
│  InvokeHTTP     │  Poll API every 30 seconds
│                 │  Endpoint: /v4/matches?status=IN_PLAY
│                 │  Header: X-Auth-Token
└────────┬────────┘
         │ Response FlowFile
         ▼
┌─────────────────────┐
│  EvaluateJsonPath   │  Extract JSON fields to attributes
│                     │  match.id, match.status, match.homeTeam, etc.
└────────┬────────────┘
         │ FlowFile with attributes
         ▼
┌─────────────────────┐
│  RouteOnAttribute   │  Filter only IN_PLAY matches
│                     │  Condition: ${match.status:equals('IN_PLAY')}
└────────┬────────────┘
         │ Live matches only
         ▼
┌─────────────────────┐
│  UpdateAttribute    │  Add metadata
│                     │  source=nifi, ingestion.timestamp, etc.
└────────┬────────────┘
         │ Enriched FlowFile
         ▼
┌─────────────────────┐
│  PublishKafka       │  Send to Confluent Cloud
│                     │  Topic: live-match-events
│                     │  Auth: SASL_SSL
│                     │  Compression: gzip
└─────────────────────┘
```

---

## 🔧 Configuration Summary

### **NiFi Container:**
```yaml
services:
  nifi:
    image: apache/nifi:1.25.0
    ports:
      - "8443:8443"  # HTTPS Web UI
    environment:
      # Authentication
      SINGLE_USER_CREDENTIALS_USERNAME: admin
      SINGLE_USER_CREDENTIALS_PASSWORD: adminadmin123456
      
      # JVM Heap
      NIFI_JVM_HEAP_INIT: 2g
      NIFI_JVM_HEAP_MAX: 4g
    
    volumes:
      # Persistent storage for flows
      - nifi_conf:/opt/nifi/nifi-current/conf
      - nifi_database:/opt/nifi/nifi-current/database_repository
      - nifi_flowfile:/opt/nifi/nifi-current/flowfile_repository
      - nifi_content:/opt/nifi/nifi-current/content_repository
      - nifi_provenance:/opt/nifi/nifi-current/provenance_repository
      - nifi_state:/opt/nifi/nifi-current/state
      - nifi_logs:/opt/nifi/nifi-current/logs
```

### **Key Processors:**

1. **InvokeHTTP:**
   - URL: `https://api.football-data.org/v4/matches?status=IN_PLAY`
   - Schedule: `30 sec`
   - Header: `X-Auth-Token: 798a49800fe84474bc7858ca06434966`

2. **PublishKafka:**
   - Brokers: `pkc-xxxxx.ap-southeast-1.aws.confluent.cloud:9092`
   - Security: `SASL_SSL` with API Key/Secret
   - Topic: `live-match-events`
   - Compression: `gzip`

---

## 🚀 Quick Start

### **Step 1: Start NiFi**
```bash
cd /home/hung/Downloads/bigdata/football_project

# Start services
docker-compose -f docker-compose.streaming.yml up -d

# Wait ~2 minutes for NiFi to start
docker logs -f football-nifi
```

### **Step 2: Access Web UI**
```
URL: https://localhost:8443/nifi
Username: admin
Password: adminadmin123456
```

### **Step 3: Build Flow**
Follow detailed guide: [`NIFI_SETUP_GUIDE.md`](./NIFI_SETUP_GUIDE.md)

1. Add InvokeHTTP processor
2. Add EvaluateJsonPath processor
3. Add RouteOnAttribute processor
4. Add UpdateAttribute processor
5. Add PublishKafka processor
6. Connect processors
7. Configure each processor
8. Start flow

### **Step 4: Monitor**
- **NiFi UI:** See real-time data flow
- **Confluent Console:** https://confluent.cloud/
- **PostgreSQL:** Check `streaming.live_events` table

---

## 📈 Monitoring & Management

### **NiFi UI Features:**

1. **Real-time Statistics:**
   - Tasks executed (5 min)
   - FlowFiles in/out
   - Data throughput
   - Average processing time

2. **Data Provenance:**
   - Track each event from source to destination
   - View data lineage graph
   - Inspect content at each step

3. **Bulletin Board:**
   - Error messages
   - Warnings
   - Info logs
   - Filter by processor/severity

4. **Connection Queues:**
   - View queued FlowFiles
   - Inspect data content
   - Check backpressure

### **Confluent Cloud Console:**
```
https://confluent.cloud/
→ Cluster
→ Topics
→ live-match-events
→ Messages tab
```

See real-time messages published by NiFi.

---

## 🔍 Troubleshooting

### **Common Issues:**

1. **NiFi won't start:**
   ```bash
   # Check logs
   docker logs football-nifi
   
   # Port conflict? Change port
   ports:
     - "8444:8443"  # Change 8443 to 8444
   ```

2. **Can't connect to Confluent Cloud:**
   - Verify API Key/Secret in PublishKafka processor
   - Check SSL Context Service is enabled
   - Test with `kafka-console-producer` first

3. **No data flowing:**
   - Check if matches are IN_PLAY (API returns empty during off-hours)
   - Test with `status=SCHEDULED` to see all matches
   - Verify API token is valid

4. **High memory usage:**
   ```yaml
   # Increase JVM heap
   environment:
     NIFI_JVM_HEAP_INIT: 4g
     NIFI_JVM_HEAP_MAX: 8g
   ```

---

## 🎯 Advantages of This Setup

### **1. Visual Development:**
- No coding required for producer logic
- Drag-and-drop interface
- See data flow in real-time
- Easy to modify without code changes

### **2. Production Features:**
- **Built-in monitoring:** See metrics instantly
- **Data provenance:** Track every event
- **Error handling:** Automatic retry & failure routing
- **Backpressure:** Automatic queue management
- **Clustering:** Multi-node HA out-of-the-box

### **3. Operational Efficiency:**
- **No deployments:** Update flow without restart
- **Zero downtime:** Start/stop processors individually
- **Easy debugging:** Inspect data at each step
- **Built-in scheduler:** CRON expressions supported

### **4. Enterprise Ready:**
- **Security:** LDAP, Kerberos, SSL/TLS
- **Compliance:** Full audit trail
- **Scalability:** Horizontal scaling
- **High Availability:** Multi-node clustering

---

## 📚 Documentation

### **Complete Guides:**

1. **[NIFI_SETUP_GUIDE.md](./NIFI_SETUP_GUIDE.md)** - Complete step-by-step setup (1000+ lines)
   - NiFi installation
   - Flow design
   - Processor configuration
   - Confluent Cloud integration
   - Monitoring & troubleshooting

2. **[CONFLUENT_CLOUD_SETUP.md](./CONFLUENT_CLOUD_SETUP.md)** - Confluent Cloud setup
   - Account creation
   - Cluster setup
   - Topic creation
   - API key generation

3. **[STREAMING_ARCHITECTURE.md](./STREAMING_ARCHITECTURE.md)** - Architecture overview
   - System design
   - Component roles
   - Data flow

---

## 🔄 Migration from Python

### **What Changed:**

**Removed:**
- ❌ `src/streaming/live_events_producer.py` (not needed)
- ❌ Python Kafka producer code
- ❌ Manual HTTP request handling
- ❌ JSON parsing logic
- ❌ Error handling code
- ❌ Rate limiting implementation

**Added:**
- ✅ NiFi Docker service in `docker-compose.streaming.yml`
- ✅ NiFi visual flow (drag-and-drop)
- ✅ Real-time monitoring UI
- ✅ Data provenance tracking
- ✅ Built-in error handling

**Unchanged:**
- ✅ Confluent Cloud Kafka setup
- ✅ Spark streaming consumer (`live_events_consumer.py`)
- ✅ PostgreSQL schema
- ✅ Data format & topic structure

### **How to Use:**

**Old way (Python):**
```bash
export $(cat .env | xargs)
python src/streaming/live_events_producer.py
```

**New way (NiFi):**
```bash
docker-compose -f docker-compose.streaming.yml up -d
# Access UI: https://localhost:8443/nifi
# Build flow visually
# Start processors
```

---

## 💡 Best Practices

### **1. Flow Design:**
- Keep processors simple with single responsibility
- Use descriptive processor names
- Add comments/labels for complex logic
- Group related processors into Process Groups

### **2. Error Handling:**
- Always configure failure relationships
- Route failures to PutFile for debugging
- Setup email alerts for critical failures
- Monitor Bulletin Board regularly

### **3. Performance:**
- Use compression (gzip) for Kafka
- Adjust concurrent tasks based on load
- Monitor queue sizes
- Increase back pressure thresholds if needed

### **4. Security:**
- Use environment variables for credentials
- Enable SSL for all connections
- Rotate API keys regularly
- Setup LDAP/AD authentication for teams

### **5. Maintenance:**
- Export flow templates regularly
- Document custom processors
- Setup monitoring alerts
- Keep NiFi version updated

---

## 🎉 Summary

**What You Built:**
- ✅ Apache NiFi visual producer for Football-Data.org API
- ✅ Confluent Cloud Kafka integration with SASL/SSL
- ✅ Real-time data ingestion with monitoring
- ✅ Production-ready streaming pipeline

**Key Benefits:**
- 🎨 Visual flow design (no coding)
- 📊 Real-time monitoring & metrics
- 🔍 Data provenance & lineage
- 🛡️ Built-in error handling
- ⚡ Production-ready features

**Access Points:**
- NiFi UI: https://localhost:8443/nifi
- Confluent: https://confluent.cloud/
- PostgreSQL: localhost:5432/football_analytics

**Next Steps:**
1. Start NiFi: `docker-compose -f docker-compose.streaming.yml up -d`
2. Build flow: Follow `NIFI_SETUP_GUIDE.md`
3. Start consumer: `python src/streaming/live_events_consumer.py`
4. Monitor: NiFi UI + Confluent Console

---

**Ready to stream with NiFi! 🚀**
