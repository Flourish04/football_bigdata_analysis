# ☁️ Confluent Cloud Kafka Setup Guide

## 📋 Tổng Quan

Dự án sử dụng **Confluent Cloud** (managed Kafka service) thay vì self-hosted Kafka để:
- ✅ Không cần quản lý infrastructure (Zookeeper, Kafka brokers)
- ✅ Auto-scaling & high availability
- ✅ Built-in monitoring & alerting
- ✅ $400 FREE credits (đủ dùng ~4 tháng)
- ✅ SASL/SSL security mặc định

---

## 🚀 Hướng Dẫn Setup (5 phút)

### **Bước 1: Tạo Confluent Cloud Account**

1. Truy cập: https://confluent.cloud/signup
2. Đăng ký với email (hoặc Google/GitHub)
3. Xác nhận email
4. **Nhận $400 FREE credits** (không cần credit card)

---

### **Bước 2: Tạo Kafka Cluster**

#### **2.1. Tạo Environment**
```
1. Login vào Confluent Cloud Console
2. Click "Environments" → "Add environment"
   - Name: football-streaming
   - Stream Governance Package: Essentials (FREE)
3. Click "Create"
```

#### **2.2. Tạo Kafka Cluster**
```
1. Trong environment "football-streaming"
2. Click "Add cluster"
3. Chọn cluster type:
   ┌──────────────────────────────────────────────────────────┐
   │ ✅ Basic (RECOMMENDED)                                   │
   │    - $0.00/hour base + $0.10/GB ingress                 │
   │    - Single zone, 99.5% uptime SLA                      │
   │    - Perfect for development & staging                   │
   │                                                          │
   │ ⚠️  Standard                                             │
   │    - $1.50/hour base + data transfer                    │
   │    - Multi-zone, 99.95% uptime SLA                      │
   │                                                          │
   │ ❌ Dedicated                                             │
   │    - $1.00/CKU/hour (~$720/month)                       │
   │    - Production-grade                                    │
   └──────────────────────────────────────────────────────────┘
4. Chọn Region:
   - AWS: us-east-1, us-west-2, ap-southeast-1 (Singapore)
   - GCP: us-central1, asia-southeast1
   - Azure: eastus, westeurope
   
   💡 Tip: Chọn region gần bạn nhất để giảm latency

5. Cluster Name: football-kafka-cluster
6. Click "Launch cluster" (takes ~5 minutes)
```

#### **2.3. Tạo Kafka Topic**
```
1. Vào cluster vừa tạo
2. Click "Topics" → "Create topic"
   - Topic name: live-match-events
   - Partitions: 3 (recommended)
   - Retention time: 7 days
   - Cleanup policy: delete
3. Click "Create"
```

---

### **Bước 3: Tạo API Key & Secret**

```
1. Trong cluster, click "API keys" (left sidebar)
2. Click "Add key"
3. Chọn scope:
   - ✅ Global access (recommended for simplicity)
   - OR Specific topic (live-match-events)
4. Click "Generate API key"
5. **COPY & SAVE:**
   ┌────────────────────────────────────────────┐
   │ API Key:    XXXXXXXXXXXXXXXX               │
   │ API Secret: YYYYYYYYYYYYYYYYYYYYYYYYYYYY   │
   │                                            │
   │ ⚠️  Secret chỉ hiện 1 lần! Lưu ngay!      │
   └────────────────────────────────────────────┘
6. Download credentials hoặc copy manual
```

---

### **Bước 4: Lấy Bootstrap Servers**

```
1. Trong cluster, click "Cluster settings"
2. Copy "Bootstrap server":
   
   Example:
   pkc-xxxxx.ap-southeast-1.aws.confluent.cloud:9092
   
   Format:
   pkc-<cluster-id>.<region>.<provider>.confluent.cloud:9092
```

---

### **Bước 5: Cấu Hình Dự Án**

#### **5.1. Tạo file `.env`**

```bash
# Copy template
cp .env.example .env

# Edit với credentials của bạn
nano .env
```

#### **5.2. Điền thông tin:**

```bash
# ============================================================================
# CONFLUENT CLOUD KAFKA CONFIGURATION
# ============================================================================

# Bootstrap Servers (from Step 4)
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.ap-southeast-1.aws.confluent.cloud:9092

# API Credentials (from Step 3)
KAFKA_API_KEY=XXXXXXXXXXXXXXXX
KAFKA_API_SECRET=YYYYYYYYYYYYYYYYYYYYYYYYYYYY

# Topic Name
KAFKA_TOPIC=live-match-events

# ============================================================================
# FOOTBALL API
# ============================================================================
FOOTBALL_API_TOKEN=798a49800fe84474bc7858ca06434966
```

#### **5.3. Load environment variables:**

```bash
# Linux/Mac
export $(cat .env | xargs)

# OR use python-dotenv (recommended)
pip install python-dotenv
```

---

### **Bước 6: Test Connection**

#### **6.1. Install Dependencies**

```bash
pip install kafka-python confluent-kafka python-dotenv
```

#### **6.2. Test Producer**

```python
# test_confluent.py
from kafka import KafkaProducer
import json
import os
from dotenv import load_dotenv

load_dotenv()

producer = KafkaProducer(
    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
    security_protocol='SASL_SSL',
    sasl_mechanism='PLAIN',
    sasl_plain_username=os.getenv('KAFKA_API_KEY'),
    sasl_plain_password=os.getenv('KAFKA_API_SECRET'),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send test message
test_msg = {'test': 'Hello Confluent Cloud!', 'timestamp': '2025-01-15'}
future = producer.send('live-match-events', test_msg)
result = future.get(timeout=10)

print(f"✅ Message sent! Partition: {result.partition}, Offset: {result.offset}")
producer.close()
```

```bash
python test_confluent.py
```

**Expected output:**
```
✅ Message sent! Partition: 0, Offset: 123
```

#### **6.3. Verify in Confluent Cloud Console**

```
1. Vào Confluent Cloud Console
2. Navigate to: Cluster → Topics → live-match-events
3. Click "Messages" tab
4. Bạn sẽ thấy test message vừa gửi!
```

---

## 🎯 Sử Dụng Trong Dự Án

### **1. Start Producer**

```bash
# Load .env
export $(cat .env | xargs)

# Run producer
python src/streaming/live_events_producer.py
```

**Output:**
```
================================================================================
  LIVE MATCH EVENTS PRODUCER
  Kafka: Confluent Cloud (pkc-xxxxx.ap-southeast-1.aws.confluent.cloud:9092)
  Topic: live-match-events
  API: Football-Data.org
================================================================================
✅ Kafka producer initialized (Confluent Cloud)
🔄 [14:35:22] Checking live matches...
📡 Fetched 3 live matches
📤 Sent 3/3 events to Kafka
```

### **2. Start Consumer**

```bash
# Terminal 2
export $(cat .env | xargs)

# Run consumer
python src/streaming/live_events_consumer.py
```

**Output:**
```
================================================================================
  LIVE EVENTS SPARK STREAMING CONSUMER
  Kafka: Confluent Cloud → Topic: live-match-events
  Output: PostgreSQL streaming.live_events
  Micro-batch interval: 30 seconds
================================================================================
✅ Spark session initialized with Kafka support
📡 Connecting to Confluent Cloud Kafka
✅ Connected to Kafka topic: live-match-events
🚀 Streaming started!
```

---

## 📊 Monitoring & Management

### **Confluent Cloud Console**

#### **1. Cluster Health**
```
Dashboard → Cluster Overview
- Throughput (MB/s)
- Request rate (req/s)
- Active connections
- Storage used
```

#### **2. Topic Metrics**
```
Topics → live-match-events → Metrics
- Messages per second
- Bytes in/out
- Consumer lag
- Partition distribution
```

#### **3. Consumer Groups**
```
Consumers → Consumer Groups
- Group ID: live-events-consumer
- Lag per partition
- Last offset committed
```

#### **4. Data Viewer**
```
Topics → live-match-events → Messages
- Browse messages in real-time
- Filter by partition/offset
- View message headers & payload
```

---

## 💰 Cost Optimization

### **FREE Credits Usage ($400)**

**Basic Cluster Costs:**
```
Base:       $0.00/hour  (FREE tier)
Ingress:    $0.10/GB
Egress:     $0.09/GB
Storage:    $0.10/GB/month
```

**Example Calculation:**
```
Scenario: Live match streaming 24/7

Messages:
- 10 live matches/day
- 1 update/30s = 2 updates/min = 120 updates/hour
- 10 matches × 120 = 1,200 messages/hour
- 1,200 × 24 = 28,800 messages/day

Data:
- Average message size: ~2 KB
- Daily ingress: 28,800 × 2 KB = 57.6 MB ≈ 0.06 GB
- Monthly ingress: 0.06 × 30 = 1.8 GB

Cost:
- Ingress: 1.8 GB × $0.10 = $0.18/month
- Storage: 1.8 GB × $0.10 = $0.18/month
- Total: ~$0.36/month

FREE $400 credits → lasts ~1,111 months! 🎉
```

**Tips to Stay in FREE Tier:**
- ✅ Use Basic cluster (not Standard/Dedicated)
- ✅ Set retention to 7 days (not infinite)
- ✅ Delete old topics không dùng
- ✅ Monitor usage in Billing dashboard

---

## 🔒 Security Best Practices

### **1. API Key Management**

```bash
# ✅ DO: Store in .env (gitignore)
KAFKA_API_KEY=xxx
KAFKA_API_SECRET=yyy

# ❌ DON'T: Hardcode in code
producer = KafkaProducer(
    sasl_plain_username='XXXXXXX',  # ❌ BAD!
    sasl_plain_password='YYYYYYY'   # ❌ BAD!
)
```

### **2. Rotate API Keys**

```
1. Confluent Cloud Console → API Keys
2. Create new key
3. Update .env with new credentials
4. Test producer/consumer
5. Delete old key
```

### **3. Restrict Access**

```
- Create separate API keys for producer/consumer
- Use resource-level ACLs:
  * Producer: WRITE on topic
  * Consumer: READ on topic + consumer group
```

---

## 🛠️ Troubleshooting

### **Error: Authentication failed**

```
Error: kafka.errors.AuthenticationFailedError

Solution:
1. Verify API Key/Secret in .env
2. Check key is not expired
3. Ensure key has correct permissions
```

### **Error: Topic not found**

```
Error: UnknownTopicOrPartitionError

Solution:
1. Create topic in Confluent Cloud Console
2. OR enable auto.create.topics.enable (not recommended for production)
```

### **Error: Connection timeout**

```
Error: KafkaTimeoutError: Failed to update metadata

Solution:
1. Check bootstrap servers URL (typo?)
2. Verify network connectivity:
   telnet pkc-xxxxx.region.provider.confluent.cloud 9092
3. Check firewall rules (port 9092 must be open)
```

### **High Latency**

```
Symptoms: Messages take >5 seconds to appear

Solution:
1. Use geographically closer region
2. Increase partitions (3 → 6)
3. Check producer batch settings:
   linger_ms=10  # Wait max 10ms before sending
   batch_size=32768  # 32KB batches
```

---

## 📚 Confluent CLI (Optional)

### **Install CLI**

```bash
# Mac
brew install confluent-cli

# Linux
curl -sL --http1.1 https://cnfl.io/cli | sh -s -- latest

# Verify
confluent version
```

### **Login**

```bash
confluent login --save
```

### **Useful Commands**

```bash
# List environments
confluent environment list

# Use environment
confluent environment use env-xxxxx

# List clusters
confluent kafka cluster list

# Use cluster
confluent kafka cluster use lkc-xxxxx

# List topics
confluent kafka topic list

# Describe topic
confluent kafka topic describe live-match-events

# Produce message
echo '{"test":"message"}' | confluent kafka topic produce live-match-events

# Consume messages
confluent kafka topic consume live-match-events --from-beginning

# Create API key
confluent api-key create --resource lkc-xxxxx
```

---

## 🔗 Useful Links

- **Confluent Cloud Console**: https://confluent.cloud/
- **Documentation**: https://docs.confluent.io/cloud/current/
- **Pricing Calculator**: https://www.confluent.io/confluent-cloud/pricing/
- **Free Trial**: https://www.confluent.io/confluent-cloud/tryfree/
- **Support**: https://support.confluent.io/

---

## ✅ Checklist

- [ ] Created Confluent Cloud account ($400 FREE credits)
- [ ] Created environment & Basic cluster
- [ ] Created topic: live-match-events (3 partitions)
- [ ] Generated API Key & Secret
- [ ] Copied Bootstrap Servers URL
- [ ] Updated `.env` with credentials
- [ ] Tested producer connection
- [ ] Tested consumer connection
- [ ] Verified messages in Console
- [ ] Set up monitoring alerts (optional)

---

## 🎓 Next Steps

1. ✅ Setup Confluent Cloud (this guide)
2. ⏭️ Run producer: `python src/streaming/live_events_producer.py`
3. ⏭️ Run consumer: `python src/streaming/live_events_consumer.py`
4. ⏭️ Query live data: `SELECT * FROM streaming.vw_current_live_matches;`
5. ⏭️ Build dashboard with Grafana/Metabase

---

**🎉 Bây giờ bạn đã có Kafka cluster production-ready trên cloud!**

**Cost: ~$0.36/month** (với $400 FREE credits → 1000+ months) 🚀
