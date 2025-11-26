# 🚀 Apache NiFi Producer Setup Guide

## 📋 Overview

This guide shows how to use **Apache NiFi** as a visual data producer to ingest live football match data from **Football-Data.org API** and publish to **Confluent Cloud Kafka**.

### Architecture
```
Football-Data.org API
         ↓
    Apache NiFi (Visual Flow)
    - InvokeHTTP (API polling)
    - EvaluateJsonPath (extract data)
    - RouteOnAttribute (filter live matches)
    - UpdateAttribute (enrich metadata)
    - PublishKafka (to Confluent Cloud)
         ↓
    Confluent Cloud Kafka
    - Topic: live-match-events
    - Auth: SASL_SSL
         ↓
    Spark Streaming Consumer
         ↓
    PostgreSQL
    - streaming.live_events
```

---

## 🎯 Why Apache NiFi?

### **Advantages over Python Producer:**

| Feature | Python Script | Apache NiFi |
|---------|---------------|-------------|
| **Visual Design** | ❌ Code-based | ✅ Drag-and-drop UI |
| **Real-time Monitoring** | ❌ Logs only | ✅ Live flow visualization |
| **Data Lineage** | ❌ Manual tracking | ✅ Built-in provenance |
| **Error Handling** | ❌ Try-catch blocks | ✅ Automatic retry/routing |
| **Backpressure** | ❌ Manual implementation | ✅ Built-in queue management |
| **Dynamic Config** | ❌ Restart needed | ✅ Update on-the-fly |
| **Debugging** | ❌ Print statements | ✅ Data inspection at each step |
| **Schedule/Cron** | ❌ External scheduler | ✅ Built-in timers |

---

## 🛠️ Step 1: Start NiFi

### **1.1 Start Services**

**Note**: This guide shows Docker setup. For local installation (recommended), see `LOCAL_SETUP.md`.

```bash
cd /home/hung/Downloads/bigdata/football_project

# Option 1: Local installation (recommended)
# See LOCAL_SETUP.md for NiFi, PostgreSQL, Superset local setup

# Option 2: Docker (legacy)
docker-compose -f docker-compose.streaming.yml up -d

# Check status
docker-compose -f docker-compose.streaming.yml ps

# Expected output:
# NAME                IMAGE                     STATUS
# football-nifi       apache/nifi:1.25.0       Up (healthy)
# football-postgres   postgres:14-alpine       Up (healthy)
```

### **1.2 Wait for NiFi to Start**
NiFi takes ~2 minutes to start. Monitor logs:
```bash
docker logs -f football-nifi

# Wait for this message:
# "NiFi has started. The UI is available at the following URLs:"
```

### **1.3 Access NiFi Web UI**
```
URL: https://localhost:8443/nifi
Username: admin
Password: adminadmin123456
```

**Note:** Accept the self-signed certificate warning in your browser.

---

## 🔧 Step 2: Configure Confluent Cloud Connection

### **2.1 Get Confluent Cloud Credentials**

From your `.env` file:
```bash
cat .env

# You need these values:
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.ap-southeast-1.aws.confluent.cloud:9092
KAFKA_API_KEY=YOUR_API_KEY
KAFKA_API_SECRET=YOUR_API_SECRET
KAFKA_TOPIC=live-match-events
```

If not set up yet, follow: [`CONFLUENT_CLOUD_SETUP.md`](./CONFLUENT_CLOUD_SETUP.md)

### **2.2 Create Controller Services**

#### **A. SSL Context Service**

1. Click **Configure** (gear icon) in NiFi UI
2. Go to **Controller Services** tab
3. Click **+** to add new service
4. Search and add: **StandardRestrictedSSLContextService**
5. Configure:
   ```
   Name: Confluent-Cloud-SSL
   Truststore Filename: (leave empty - uses system certs)
   Truststore Type: JKS
   SSL Protocol: TLS
   ```
6. Click **Apply**, then **Enable** (⚡)

#### **B. Record Writer (JSON)**

1. Add new service: **JsonRecordSetWriter**
2. Configure:
   ```
   Name: JSON-Writer
   Schema Write Strategy: Do Not Write Schema
   Pretty Print JSON: false
   Suppress Null Values: Never Suppress
   ```
3. Enable the service

---

## 🎨 Step 3: Build NiFi Flow

### **3.1 Add Processors to Canvas**

Drag these processors from the toolbar to the canvas:

1. **InvokeHTTP** - Poll Football-Data.org API
2. **EvaluateJsonPath** - Extract match data
3. **RouteOnAttribute** - Filter only live matches
4. **UpdateAttribute** - Add metadata (timestamp, source)
5. **PublishKafkaRecord_2_6** - Send to Confluent Cloud

### **3.2 Configure Each Processor**

#### **Processor 1: InvokeHTTP**

**Purpose:** Poll live matches from Football-Data.org API every 30 seconds

**Configuration:**
```
PROPERTIES:
  HTTP Method: GET
  Remote URL: https://api.football-data.org/v4/matches?status=IN_PLAY
  
  Connection Timeout: 30 sec
  Read Timeout: 30 sec
  
  Send Message Body: false
  
  Attributes to Send: (empty)
  
  Custom Headers:
    X-Auth-Token = 798a49800fe84474bc7858ca06434966
  
  Content-Type: application/json

SCHEDULING:
  Scheduling Strategy: Timer driven
  Run Schedule: 30 sec
  Concurrent Tasks: 1

AUTOMATICALLY TERMINATE RELATIONSHIPS:
  ✓ Failure
  ✓ Retry
  ✓ No Retry
  
LEAVE UNCHECKED:
  Response (connect to next processor)
```

**Auto-terminate Failure:** This prevents failed API calls from blocking the flow.

---

#### **Processor 2: EvaluateJsonPath**

**Purpose:** Extract match fields from API response

**Configuration:**
```
PROPERTIES:
  Destination: flowfile-attribute
  
  Return Type: auto-detect
  
  Path Not Found Behavior: ignore
  
  Null Value Representation: empty string
  
  Custom Properties (click + to add each):
    match.id = $.matches[*].id
    match.status = $.matches[*].status
    match.homeTeam = $.matches[*].homeTeam.name
    match.awayTeam = $.matches[*].awayTeam.name
    match.homeScore = $.matches[*].score.fullTime.home
    match.awayScore = $.matches[*].score.fullTime.away
    match.competition = $.matches[*].competition.name
    match.matchday = $.matches[*].matchday
    match.utcDate = $.matches[*].utcDate
    match.stage = $.matches[*].stage
    match.json = $

AUTOMATICALLY TERMINATE RELATIONSHIPS:
  ✓ failure
  ✓ unmatched
  
LEAVE UNCHECKED:
  matched (connect to next processor)
```

---

#### **Processor 3: RouteOnAttribute**

**Purpose:** Filter only matches with status = "IN_PLAY"

**Configuration:**
```
PROPERTIES:
  Routing Strategy: Route to Property name
  
  Custom Properties:
    live_match = ${match.status:equals('IN_PLAY')}

AUTOMATICALLY TERMINATE RELATIONSHIPS:
  ✓ unmatched
  
LEAVE UNCHECKED:
  live_match (connect to next processor)
```

---

#### **Processor 4: UpdateAttribute**

**Purpose:** Add metadata for tracking and debugging

**Configuration:**
```
PROPERTIES:
  Delete Attributes Expression: (empty)
  
  Custom Properties (click + to add):
    kafka.topic = live-match-events
    source = football-data-org-api
    ingestion.timestamp = ${now():format('yyyy-MM-dd HH:mm:ss')}
    producer = nifi
    data.type = live-match-event
    record.count = 1

AUTOMATICALLY TERMINATE RELATIONSHIPS:
  (none - all should connect to next processor)
```

---

#### **Processor 5: PublishKafkaRecord_2_6**

**Purpose:** Publish to Confluent Cloud Kafka with SASL/SSL authentication

**Configuration:**
```
PROPERTIES:
  Kafka Brokers: pkc-xxxxx.ap-southeast-1.aws.confluent.cloud:9092
  Topic Name: live-match-events
  
  Delivery Guarantee: Guarantee Single Node Delivery
  
  Record Reader: JsonTreeReader (create new - see below)
  Record Writer: JSON-Writer (select from Controller Services)
  
  Use Transactions: false
  
  Attributes to Send as Headers: (empty)
  
  Message Key Field: match.id
  
  Partitioner class: DefaultPartitioner
  
  Compression Type: gzip

SECURITY PROPERTIES:
  Security Protocol: SASL_SSL
  
  SASL Mechanism: PLAIN
  
  Username: <YOUR_KAFKA_API_KEY>
  
  Password: <YOUR_KAFKA_API_SECRET>
  
  SSL Context Service: Confluent-Cloud-SSL (select from dropdown)

SCHEDULING:
  Concurrent Tasks: 1
  Run Duration: 0 ms

AUTOMATICALLY TERMINATE RELATIONSHIPS:
  ✓ success
  ✓ failure
```

**Create JsonTreeReader:**
1. Click **Create new service** in Record Reader dropdown
2. Select **JsonTreeReader**
3. Configure:
   ```
   Name: JSON-Reader
   Schema Access Strategy: Infer Schema
   ```
4. Enable the service

---

### **3.3 Connect Processors**

Create connections by dragging from one processor to another:

```
InvokeHTTP (Response)
    ↓
EvaluateJsonPath (matched)
    ↓
RouteOnAttribute (live_match)
    ↓
UpdateAttribute
    ↓
PublishKafkaRecord_2_6
```

**For each connection:**
- Default settings are fine
- FlowFile Expiration: 0 sec
- Back Pressure Object Threshold: 10000
- Back Pressure Data Size Threshold: 1 GB

---

## ▶️ Step 4: Start the Flow

### **4.1 Start All Processors**

1. **Select all processors:**
   - Click and drag to select all processors
   - Or use `Ctrl+A` (Windows/Linux) / `Cmd+A` (Mac)

2. **Start selected:**
   - Click **Start** button (▶️) in the Operate panel
   - Or right-click → **Start**

### **4.2 Verify Data Flow**

Monitor the connections - you should see:
- **Numbers on connections** indicating FlowFiles flowing
- **Green indicators** on processors showing activity
- **Statistics** showing:
  - In: Number of FlowFiles received
  - Out: Number of FlowFiles sent
  - Tasks Duration: Processing time

### **4.3 Inspect Data**

**Option 1: View Data Provenance**
1. Right-click any connection → **List queue**
2. Click **Info** icon (ℹ️) on a FlowFile
3. Go to **CONTENT** tab to see JSON data

**Option 2: View in Confluent Cloud**
1. Login to https://confluent.cloud/
2. Navigate to: Cluster → Topics → **live-match-events**
3. Click **Messages** tab
4. See real-time messages!

---

## 📊 Step 5: Monitoring & Management

### **5.1 NiFi Monitoring**

#### **Processor Statistics:**
Each processor shows:
- **Tasks (5 min):** Number of executions in last 5 minutes
- **In:** FlowFiles received
- **Out:** FlowFiles sent
- **Read/Write:** Data throughput
- **Tasks/Time:** Average execution time

#### **Connection Queues:**
- **Queued:** Number of FlowFiles waiting
- **Size:** Data size in queue
- **Backpressure:** Visual indicator when queue is full

#### **Bulletin Board:**
- Click **Bulletin Board** icon (🔔) in toolbar
- Shows errors, warnings, and info messages
- Filter by processor or severity

### **5.2 Data Provenance**

Track data lineage:
1. Click **Data Provenance** icon (📊) in toolbar
2. View events:
   - **RECEIVE:** Data arrived from API
   - **FORK:** Data split into multiple FlowFiles
   - **ROUTE:** Data routed based on attributes
   - **SEND:** Data sent to Kafka
3. Click **View Details** to see full lineage graph

### **5.3 Performance Tuning**

#### **Adjust Polling Interval:**
InvokeHTTP → Configure → Scheduling → Run Schedule:
- `30 sec` - Normal (12 requests/hour)
- `60 sec` - Light load (6 requests/hour)
- `10 sec` - Aggressive (36 requests/hour - watch rate limits!)

#### **Concurrent Tasks:**
For high throughput:
- InvokeHTTP: Keep at 1 (avoid overwhelming API)
- EvaluateJsonPath: Can increase to 2-3
- PublishKafka: Can increase to 2-3

#### **Back Pressure:**
If connections fill up:
1. Right-click connection → Configure
2. Increase:
   - Back Pressure Object Threshold: 10000 → 50000
   - Back Pressure Data Size Threshold: 1 GB → 5 GB

---

## 🔍 Step 6: Troubleshooting

### **Issue 1: NiFi Won't Start**

**Symptoms:**
```bash
docker logs football-nifi
# Error: Address already in use
```

**Solution:**
```bash
# Check if port 8443 is in use
sudo lsof -i :8443

# Kill the process or change NiFi port
docker-compose -f docker-compose.streaming.yml down
# Edit docker-compose.streaming.yml, change 8443:8443 to 8444:8443
docker-compose -f docker-compose.streaming.yml up -d
```

---

### **Issue 2: Can't Connect to Confluent Cloud**

**Symptoms:**
PublishKafka processor shows error:
```
Failed to send FlowFile to Kafka
Connection refused
```

**Solution:**
1. **Verify credentials:**
   ```bash
   # Test with kafka-console-producer
   docker run -it confluentinc/cp-kafka:7.5.0 \
     kafka-console-producer \
     --broker-list pkc-xxxxx.confluent.cloud:9092 \
     --topic live-match-events \
     --producer-property security.protocol=SASL_SSL \
     --producer-property sasl.mechanism=PLAIN \
     --producer-property "sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username='YOUR_API_KEY' password='YOUR_API_SECRET';"
   ```

2. **Check SSL Context Service:**
   - Make sure **Confluent-Cloud-SSL** is **enabled** (green ⚡)
   - Verify **SSL Protocol = TLS**

3. **Check Security Protocol:**
   - PublishKafka → Properties → Security Protocol = **SASL_SSL**
   - SASL Mechanism = **PLAIN**

---

### **Issue 3: API Returns Empty Response**

**Symptoms:**
InvokeHTTP shows success, but no data flows to next processor.

**Solution:**
1. **Check API endpoint manually:**
   ```bash
   curl -H "X-Auth-Token: 798a49800fe84474bc7858ca06434966" \
     "https://api.football-data.org/v4/matches?status=IN_PLAY"
   ```

2. **No live matches right now:**
   - API returns `{"matches": []}`
   - This is normal when no matches are in play
   - Wait for match schedule or test with different status:
     ```
     Remote URL: https://api.football-data.org/v4/matches?status=SCHEDULED
     ```

3. **Check rate limit:**
   ```bash
   # API response headers show remaining calls
   curl -I -H "X-Auth-Token: 798a49800fe84474bc7858ca06434966" \
     "https://api.football-data.org/v4/matches"
   
   # Look for:
   # X-Requests-Available-Minute: 8
   ```

---

### **Issue 4: Processor Shows Yellow Warning**

**Symptoms:**
Processor has yellow warning icon.

**Solution:**
1. **Hover over processor** to see warning message
2. **Common warnings:**
   - "Invalid relationship" - Fix by auto-terminating unused relationships
   - "Controller service disabled" - Enable required services
   - "Required property not set" - Fill in missing configuration

3. **Right-click processor → View configuration → Validate** to see all issues

---

### **Issue 5: High CPU/Memory Usage**

**Symptoms:**
```bash
docker stats football-nifi
# Shows high CPU/Memory usage
```

**Solution:**
1. **Increase JVM heap:**
   ```yaml
   # docker-compose.streaming.yml
   environment:
     NIFI_JVM_HEAP_INIT: 4g  # Increase from 2g
     NIFI_JVM_HEAP_MAX: 8g   # Increase from 4g
   ```

2. **Reduce concurrent tasks:**
   - Each processor → Configure → Scheduling → Concurrent Tasks: 1

3. **Enable compression:**
   - PublishKafka → Properties → Compression Type: gzip

---

## 🎓 Step 7: Advanced Features

### **7.1 Error Handling**

Create failure handler:
1. Add **PutFile** processor
2. Connect PublishKafka **failure** to PutFile
3. Configure:
   ```
   Directory: /tmp/failed_messages
   Conflict Resolution Strategy: replace
   ```
4. This saves failed messages for debugging

### **7.2 Data Transformation**

Transform JSON before sending to Kafka:
1. Add **JoltTransformJSON** processor between UpdateAttribute and PublishKafka
2. Configure Jolt Specification:
   ```json
   [
     {
       "operation": "shift",
       "spec": {
         "matches": {
           "*": {
             "id": "match_id",
             "homeTeam": {
               "name": "home_team"
             },
             "awayTeam": {
               "name": "away_team"
             },
             "score": {
               "fullTime": {
                 "home": "home_score",
                 "away": "away_score"
               }
             }
           }
         }
       }
     }
   ]
   ```

### **7.3 Multiple Topics**

Route different match statuses to different topics:
1. After RouteOnAttribute, add another **RouteOnAttribute** processor
2. Configure routes:
   ```
   live_match = ${match.status:equals('IN_PLAY')}
   finished_match = ${match.status:equals('FINISHED')}
   scheduled_match = ${match.status:equals('SCHEDULED')}
   ```
3. Add separate PublishKafka processors for each route with different topics

### **7.4 Alerting**

Get notified on errors:
1. Add **PutEmail** processor
2. Connect failure relationships to PutEmail
3. Configure SMTP settings:
   ```
   SMTP Hostname: smtp.gmail.com
   SMTP Port: 587
   SMTP Username: your-email@gmail.com
   SMTP Password: your-app-password
   From: nifi-alerts@yourdomain.com
   To: admin@yourdomain.com
   Subject: NiFi Flow Error
   ```

---

## 📚 Step 8: Save & Export Flow

### **8.1 Save Flow as Template**

1. **Select all processors:**
   - Click and drag to select entire flow
   - Or `Ctrl+A` / `Cmd+A`

2. **Create template:**
   - Right-click → **Create template**
   - Name: `Football-API-to-Confluent-Cloud`
   - Description: `Ingest live match data from Football-Data.org to Confluent Cloud Kafka`
   - Click **Create**

3. **Download template:**
   - Click **Templates** icon (📄) in toolbar
   - Click **Download** icon next to your template
   - Save as: `football_nifi_template.xml`

### **8.2 Import Template (for deployment)**

On another NiFi instance:
1. Click **Upload Template** icon (📤) in toolbar
2. Select `football_nifi_template.xml`
3. Drag **Template** icon from toolbar to canvas
4. Select your template
5. Configure processor properties (API keys, Kafka credentials)
6. Start processors

---

## 🔄 Step 9: Verify End-to-End

### **9.1 Check NiFi → Kafka**

**In NiFi:**
- PublishKafka processor shows **Out: 1+** (messages sent)

**In Confluent Cloud:**
```bash
# Via web console
1. Login to https://confluent.cloud/
2. Cluster → Topics → live-match-events
3. Messages tab → See JSON messages

# Via CLI
confluent kafka topic consume live-match-events \
  --from-beginning \
  --max-messages 10
```

### **9.2 Check Kafka → Spark → PostgreSQL**

**Start Spark consumer:**
```bash
cd /home/hung/Downloads/bigdata/football_project

# Load environment
export $(cat .env | xargs)

# Start consumer
python src/streaming/live_events_consumer.py
```

**Verify in PostgreSQL:**
```bash
docker exec -it football-postgres psql -U postgres -d football_analytics

-- Check live events
SELECT * FROM streaming.live_events ORDER BY ingestion_time DESC LIMIT 10;

-- Count by competition
SELECT competition_name, COUNT(*) as match_count
FROM streaming.live_events
GROUP BY competition_name
ORDER BY match_count DESC;
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   FOOTBALL DATA STREAMING PIPELINE               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ Football-Data.org    │
│ REST API             │
│ (every 30 seconds)   │
└──────────┬───────────┘
           │ HTTPS
           │ X-Auth-Token
           ▼
┌──────────────────────────────────────────────────────────────────┐
│              APACHE NIFI (Visual Producer)                        │
│  https://localhost:8443/nifi                                      │
├──────────────────────────────────────────────────────────────────┤
│  [InvokeHTTP]                                                     │
│       ↓                                                           │
│  [EvaluateJsonPath]  ← Extract match fields                      │
│       ↓                                                           │
│  [RouteOnAttribute]  ← Filter IN_PLAY matches                    │
│       ↓                                                           │
│  [UpdateAttribute]   ← Add metadata                              │
│       ↓                                                           │
│  [PublishKafka]      ← SASL_SSL to Confluent Cloud              │
└──────────┬───────────────────────────────────────────────────────┘
           │ SASL_SSL
           │ Topic: live-match-events
           ▼
┌──────────────────────────────────────────────────────────────────┐
│           CONFLUENT CLOUD KAFKA (Managed)                         │
│  https://confluent.cloud/                                         │
│                                                                   │
│  • Topic: live-match-events                                       │
│  • Partitions: 3                                                  │
│  • Replication: 3 (automatic)                                     │
│  • Retention: 7 days                                              │
│  • Compression: gzip                                              │
└──────────┬───────────────────────────────────────────────────────┘
           │ Spark Structured Streaming
           │ (kafka.bootstrap.servers)
           ▼
┌──────────────────────────────────────────────────────────────────┐
│         SPARK STREAMING CONSUMER (Python)                         │
│  src/streaming/live_events_consumer.py                            │
│                                                                   │
│  • Read from Kafka with SASL_SSL                                  │
│  • Parse JSON events                                              │
│  • Transform to table schema                                      │
│  • Write to PostgreSQL                                            │
└──────────┬───────────────────────────────────────────────────────┘
           │ JDBC
           ▼
┌──────────────────────────────────────────────────────────────────┐
│           POSTGRESQL (localhost:5432)                             │
│                                                                   │
│  Database: football_analytics                                     │
│  Schema: streaming                                                │
│  Table: live_events                                               │
│                                                                   │
│  Views:                                                           │
│  • vw_current_live_matches                                        │
│  • vw_live_match_statistics                                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Summary

### **What You've Built:**

✅ **Apache NiFi** visual data flow for API ingestion
✅ **Confluent Cloud** managed Kafka cluster with SASL/SSL
✅ **Spark Streaming** consumer processing live events
✅ **PostgreSQL** storing streaming data
✅ **Real-time monitoring** via NiFi UI and Confluent Console

### **Key Benefits:**

- 🎨 **Visual Design:** No coding needed for producer logic
- 📊 **Real-time Monitoring:** See data flow in real-time
- 🔍 **Data Provenance:** Track every event from source to destination
- 🛡️ **Error Handling:** Automatic retry and failure routing
- 🚀 **Production Ready:** Built-in backpressure, scaling, and HA

### **Next Steps:**

1. ✅ **Setup Confluent Cloud** (if not done): [`CONFLUENT_CLOUD_SETUP.md`](./CONFLUENT_CLOUD_SETUP.md)
2. ✅ **Start NiFi & services**: `docker-compose -f docker-compose.streaming.yml up -d`
3. ✅ **Build NiFi flow** following this guide
4. ✅ **Start Spark consumer**: `python src/streaming/live_events_consumer.py`
5. ✅ **Monitor**: NiFi UI + Confluent Console + PostgreSQL

---

## 📖 Additional Resources

- **NiFi Documentation:** https://nifi.apache.org/docs.html
- **Confluent Kafka Connector:** https://www.confluent.io/hub/confluentinc/kafka-connect-jdbc
- **Football-Data.org API:** https://www.football-data.org/documentation/api
- **Spark Structured Streaming:** https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html

---

**🎉 Ready to stream! Access NiFi at https://localhost:8443/nifi**
