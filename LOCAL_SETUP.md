# 🚀 Local Setup Guide (No Docker)

## 📋 Overview

This guide shows how to run the Football Analytics Platform using **local installations** of NiFi, Superset, and PostgreSQL (no Docker required).

---

## ✅ Prerequisites

### **1. Java (for NiFi)**
```bash
# Check Java version (NiFi requires Java 11+)
java -version

# Expected: openjdk version "11" or higher
```

### **2. Python (for Superset)**
```bash
# Check Python version (Superset requires Python 3.9+)
python3 --version

# Expected: Python 3.9.0 or higher
```

### **3. PostgreSQL**
```bash
# Check PostgreSQL
psql --version

# Expected: psql (PostgreSQL) 12.0 or higher
```

---

## 🔧 Installation Paths

### **Typical Local Installation Paths:**

```bash
# NiFi
/opt/nifi/                    # Linux
C:\nifi\                      # Windows
~/Applications/nifi/          # macOS

# Superset
~/.local/bin/superset         # pip install
/usr/local/bin/superset       # system install

# PostgreSQL
/usr/lib/postgresql/14/       # Linux
C:\Program Files\PostgreSQL\  # Windows
/usr/local/var/postgres/      # macOS (Homebrew)
```

---

## 🚀 Step 1: Setup PostgreSQL

### **1.1 Create Database & User**

```bash
# Login as postgres user
sudo -u postgres psql

# Or on Windows/macOS:
psql -U postgres
```

```sql
-- Create database
CREATE DATABASE football_analytics;

-- Create user (if not exists)
CREATE USER postgres WITH PASSWORD '9281746356';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE football_analytics TO postgres;

-- Connect to database
\c football_analytics

-- Create schemas
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS events;
CREATE SCHEMA IF NOT EXISTS streaming;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant schema privileges
GRANT ALL PRIVILEGES ON SCHEMA bronze, silver, gold, events, streaming, analytics TO postgres;

-- Exit
\q
```

### **1.2 Test Connection**

```bash
# Test connection
psql -h localhost -U postgres -d football_analytics -c "SELECT 1;"

# Should output: 1
```

---

## 🔵 Step 2: Setup Apache NiFi (Local)

### **2.1 Check NiFi Installation**

```bash
# Find NiFi installation
# Linux/macOS:
ls /opt/nifi/nifi-*/bin/nifi.sh
# Or
find ~ -name "nifi.sh" 2>/dev/null

# Windows:
dir C:\nifi\nifi-*\bin\run-nifi.bat
```

### **2.2 Configure NiFi (Optional)**

Edit NiFi configuration if needed:

```bash
# Linux/macOS
nano /opt/nifi/nifi-*/conf/nifi.properties

# Key settings:
nifi.web.http.port=8080          # HTTP port
nifi.web.https.port=8443         # HTTPS port
nifi.security.user.login.identity.provider=single-user-provider
```

### **2.3 Start NiFi**

```bash
# Linux/macOS
cd /opt/nifi/nifi-*
./bin/nifi.sh start

# Check status
./bin/nifi.sh status

# View logs
tail -f logs/nifi-app.log

# Windows
cd C:\nifi\nifi-*
bin\run-nifi.bat
```

### **2.4 Access NiFi Web UI**

```
URL: http://localhost:8080/nifi
   or https://localhost:8443/nifi

# Get credentials (for single-user mode)
cat /opt/nifi/nifi-*/conf/login-identity-providers.xml

# Or check logs for auto-generated credentials
grep "Generated Username" logs/nifi-app.log
```

**Default credentials may be:**
- Username: admin
- Password: (check logs or configuration)

---

## 📊 Step 3: Setup Apache Superset (Local)

### **3.1 Check Superset Installation**

```bash
# Check if Superset is installed
which superset
superset version
```

### **3.2 Install Superset (if not installed)**

```bash
# Create virtual environment
python3 -m venv superset_env
source superset_env/bin/activate  # Linux/macOS
# superset_env\Scripts\activate   # Windows

# Install Superset
pip install apache-superset

# Install PostgreSQL driver
pip install psycopg2-binary
```

### **3.3 Initialize Superset**

```bash
# Set environment variables
export SUPERSET_SECRET_KEY='thisISaSECRET_1234'
export FLASK_APP=superset

# Initialize database (SQLite by default)
superset db upgrade

# Create admin user
superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@superset.com \
  --password admin

# Initialize Superset
superset init
```

### **3.4 Start Superset**

```bash
# Development mode (single process)
superset run -p 8088 --with-threads --reload --debugger

# Or production mode (with Gunicorn)
gunicorn \
  --bind 0.0.0.0:8088 \
  --workers 4 \
  --timeout 60 \
  --limit-request-line 0 \
  --limit-request-field_size 0 \
  "superset.app:create_app()"
```

### **3.5 Access Superset Web UI**

```
URL: http://localhost:8088
Username: admin
Password: admin
```

---

## ⚙️ Step 4: Configure Services

### **4.1 Configure PostgreSQL Connection (Superset)**

1. **Open Superset**: http://localhost:8088
2. **Settings → Database Connections → + DATABASE**
3. **Select: PostgreSQL**
4. **Configure:**
   ```
   Display Name: Football Analytics
   SQLAlchemy URI: postgresql://postgres:9281746356@localhost:5432/football_analytics
   ```
5. **Test Connection** → Should show "Connection looks good!"
6. **Save**

### **4.2 Configure Confluent Cloud (NiFi)**

1. **Setup Confluent Cloud** (follow `CONFLUENT_CLOUD_SETUP.md`)
2. **Get credentials:**
   ```bash
   cat .env
   
   # You need:
   KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.confluent.cloud:9092
   KAFKA_API_KEY=YOUR_API_KEY
   KAFKA_API_SECRET=YOUR_API_SECRET
   ```
3. **Configure NiFi PublishKafka processor** with these credentials

---

## 🏃 Step 5: Run Complete Pipeline

### **5.1 Start All Services**

```bash
# Terminal 1: Start PostgreSQL (if not auto-started)
sudo systemctl start postgresql  # Linux
# brew services start postgresql # macOS
# (Windows: PostgreSQL runs as service)

# Terminal 2: Start NiFi
cd /opt/nifi/nifi-*
./bin/nifi.sh start

# Terminal 3: Start Superset
source superset_env/bin/activate
superset run -p 8088 --with-threads
```

### **5.2 Run Batch ETL Pipeline**

```bash
# Terminal 4: Run batch processing
cd /home/hung/Downloads/bigdata/football_project
python run_pipeline.py

# This will:
# 1. Process CSV files (Bronze layer)
# 2. Clean data (Silver layer)
# 3. Create analytics (Gold layer)
# 4. Load to PostgreSQL
# Runtime: ~3 minutes
```

### **5.3 Setup NiFi Flow (Producer)**

```bash
# Follow NiFi setup guide
# 1. Access NiFi: http://localhost:8080/nifi
# 2. Build flow: InvokeHTTP → EvaluateJsonPath → PublishKafka
# 3. Configure Confluent Cloud credentials
# 4. Start processors

# See: NIFI_SETUP_GUIDE.md for detailed steps
```

### **5.4 Start Spark Consumer**

```bash
# Terminal 5: Start streaming consumer
cd /home/hung/Downloads/bigdata/football_project
export $(cat .env | xargs)
python src/streaming/live_events_consumer.py
```

### **5.5 Create Superset Dashboards**

```bash
# 1. Access Superset: http://localhost:8088
# 2. Connect to PostgreSQL
# 3. Create datasets from gold/silver/events schemas
# 4. Build charts and dashboards

# See: SUPERSET_SETUP.md for detailed steps
```

---

## 🔍 Verify Installation

### **Check PostgreSQL:**
```bash
psql -h localhost -U postgres -d football_analytics -c "\dt gold.*"
# Should list gold layer tables
```

### **Check NiFi:**
```bash
curl -k https://localhost:8443/nifi
# Should return HTML
```

### **Check Superset:**
```bash
curl http://localhost:8088/health
# Should return {"message": "OK"}
```

---

## 🛑 Stop Services

### **Stop NiFi:**
```bash
cd /opt/nifi/nifi-*
./bin/nifi.sh stop
```

### **Stop Superset:**
```bash
# Press Ctrl+C in terminal where Superset is running
```

### **Stop PostgreSQL:**
```bash
sudo systemctl stop postgresql  # Linux
brew services stop postgresql   # macOS
# Windows: Services → PostgreSQL → Stop
```

---

## 📊 Service Ports Summary

| Service | Port | URL |
|---------|------|-----|
| **NiFi HTTP** | 8080 | http://localhost:8080/nifi |
| **NiFi HTTPS** | 8443 | https://localhost:8443/nifi |
| **Superset** | 8088 | http://localhost:8088 |
| **PostgreSQL** | 5432 | localhost:5432 |

---

## 🐛 Troubleshooting

### **Issue: NiFi won't start**

```bash
# Check Java version
java -version  # Must be 11+

# Check if port is in use
sudo lsof -i :8080
sudo lsof -i :8443

# View NiFi logs
tail -f /opt/nifi/nifi-*/logs/nifi-app.log
```

### **Issue: Superset database error**

```bash
# Reinitialize Superset database
superset db upgrade

# Check PostgreSQL connection
psql -h localhost -U postgres -d football_analytics -c "SELECT 1;"
```

### **Issue: PostgreSQL connection refused**

```bash
# Check PostgreSQL status
sudo systemctl status postgresql  # Linux
brew services list                # macOS

# Check PostgreSQL is listening
sudo netstat -tuln | grep 5432

# Edit pg_hba.conf to allow local connections
# Add: host all all 127.0.0.1/32 md5
```

---

## 📚 Next Steps

1. ✅ **Run batch pipeline**: `python run_pipeline.py`
2. ✅ **Build NiFi flow**: Follow `NIFI_SETUP_GUIDE.md`
3. ✅ **Setup Confluent Cloud**: Follow `CONFLUENT_CLOUD_SETUP.md`
4. ✅ **Start consumer**: `python src/streaming/live_events_consumer.py`
5. ✅ **Create dashboards**: Follow `SUPERSET_SETUP.md`

---

## 💡 Tips

### **NiFi Performance:**
```bash
# Edit nifi.properties for better performance
nifi.nar.library.directory.lib1=/opt/nifi/nifi-*/lib
java.arg.2=-Xms2g    # Min heap
java.arg.3=-Xmx4g    # Max heap
```

### **Superset Performance:**
```bash
# Use Gunicorn for production
gunicorn --workers 4 --timeout 60 "superset.app:create_app()"

# Enable simple cache in superset_config.py
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
}
```

### **PostgreSQL Performance:**
```bash
# Edit postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 256MB
```

---

## 🎉 Summary

**Running locally without Docker:**
- ✅ NiFi: Local installation (port 8080/8443)
- ✅ Superset: Local installation (port 8088)
- ✅ PostgreSQL: Local installation (port 5432)
- ✅ Confluent Cloud: Managed Kafka (external)

**All services accessible at:**
- NiFi: http://localhost:8080/nifi
- Superset: http://localhost:8088
- PostgreSQL: localhost:5432/football_analytics

**No Docker containers needed! 🚀**
