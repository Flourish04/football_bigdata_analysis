# 🚀 HƯỚNG DẪN TRIỂN KHAI NHANH

## Bước 1: Cài đặt Dependencies

### System Requirements
```bash
# Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin

# Python 3.9+
sudo apt-get install python3.9 python3-pip

# Java 11+ (for Spark, Kafka)
sudo apt-get install openjdk-11-jdk

# Git
sudo apt-get install git
```

### Python Packages
```bash
# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows

# Cài đặt packages
pip install -r requirements.txt
```

## Bước 2: Khởi động Infrastructure

### Start all services với Docker Compose
```bash
# Khởi động tất cả services
docker-compose up -d

# Kiểm tra trạng thái
docker-compose ps

# Xem logs
docker-compose logs -f
```

### Các services sẽ chạy tại:
- **Kafka**: localhost:9092
- **PostgreSQL**: localhost:5432
- **TimescaleDB**: localhost:5433
- **Redis**: localhost:6379
- **Elasticsearch**: localhost:9200
- **Grafana**: http://localhost:3000 (admin/admin)
- **Airflow**: http://localhost:8080 (admin/admin)
- **Jupyter**: http://localhost:8888
- **Prometheus**: http://localhost:9090
- **MinIO**: http://localhost:9001 (minioadmin/minioadmin)
- **Superset**: http://localhost:8088

## Bước 3: Tạo Kafka Topics

```bash
# Vào container Kafka
docker exec -it kafka bash

# Tạo topics
kafka-topics --create --topic live-matches \
  --bootstrap-server localhost:9092 \
  --partitions 10 \
  --replication-factor 1

kafka-topics --create --topic player-events \
  --bootstrap-server localhost:9092 \
  --partitions 20 \
  --replication-factor 1

kafka-topics --create --topic social-media \
  --bootstrap-server localhost:9092 \
  --partitions 50 \
  --replication-factor 1

kafka-topics --create --topic betting-odds \
  --bootstrap-server localhost:9092 \
  --partitions 5 \
  --replication-factor 1

# Liệt kê topics
kafka-topics --list --bootstrap-server localhost:9092

# Exit container
exit
```

## Bước 4: Setup Database

```bash
# Kết nối PostgreSQL
docker exec -it postgres psql -U football_user -d football_analytics

# Tạo tables (copy từ ARCHITECTURE_DETAILS.md section 4.1)
# Hoặc chạy script init
docker exec -i postgres psql -U football_user -d football_analytics < docker/init-db.sql
```

## Bước 5: Lấy API Keys

### Football-Data.org API
1. Truy cập: https://www.football-data.org/
2. Đăng ký tài khoản free
3. Lấy API key từ dashboard
4. Cập nhật trong `src/kafka_producer_live_matches.py`:
   ```python
   FOOTBALL_API_KEY = 'YOUR_API_KEY_HERE'
   ```

### Twitter API (Optional)
1. Truy cập: https://developer.twitter.com/
2. Tạo application
3. Lấy API credentials

## Bước 6: Chạy Batch ETL Pipeline

```bash
# Activate virtual environment
source venv/bin/activate

# Chạy batch ETL
cd src
python batch_etl_pipeline.py
```

Output sẽ được lưu tại:
- Parquet files: `/tmp/football_processed/`
- PostgreSQL: `football_analytics` database

## Bước 7: Chạy Streaming Pipeline

### Terminal 1 - Start Kafka Producer
```bash
cd src
python kafka_producer_live_matches.py
```

### Terminal 2 - Start Spark Streaming Consumer
```bash
cd src
python spark_streaming_consumer.py
```

## Bước 8: Monitoring & Visualization

### Grafana Dashboard
1. Truy cập: http://localhost:3000
2. Login: admin/admin
3. Add datasource → PostgreSQL
   - Host: postgres:5432
   - Database: football_analytics
   - User: football_user
   - Password: football_pass

### Jupyter Notebooks
1. Truy cập: http://localhost:8888
2. Data có sẵn tại: `/home/jovyan/data/`
3. Tạo notebook mới và bắt đầu phân tích!

### Apache Superset
1. Truy cập: http://localhost:8088
2. Setup admin user
3. Connect to PostgreSQL
4. Create dashboards

## Bước 9: Airflow DAG (Optional)

```bash
# Copy DAG files
cp dags/*.py airflow/dags/

# Airflow web UI
# http://localhost:8080
# Login: admin/admin

# Trigger DAG manually hoặc để nó chạy theo schedule
```

## Troubleshooting

### Kafka connection issues
```bash
# Kiểm tra Kafka logs
docker logs kafka

# Test connection
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic live-matches --from-beginning
```

### PostgreSQL connection issues
```bash
# Check PostgreSQL logs
docker logs postgres

# Test connection
docker exec -it postgres psql -U football_user -d football_analytics -c "SELECT 1;"
```

### Spark memory issues
```bash
# Tăng memory trong spark config
spark = SparkSession.builder \
    .config("spark.executor.memory", "8g") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()
```

### Docker space issues
```bash
# Clean up
docker system prune -a
docker volume prune
```

## Testing

### Test Kafka Producer
```bash
# Terminal 1 - Start consumer để xem messages
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic live-matches --from-beginning

# Terminal 2 - Run producer
python src/kafka_producer_live_matches.py
```

### Test Batch ETL
```bash
# Chạy với sample data
python src/batch_etl_pipeline.py

# Check output
ls -lh /tmp/football_processed/
```

### Test Database
```bash
# Query PostgreSQL
docker exec -it postgres psql -U football_user -d football_analytics \
  -c "SELECT COUNT(*) FROM player_analytics;"
```

## Next Steps

1. ✅ Infrastructure setup hoàn tất
2. 🔄 Chạy batch ETL để load historical data
3. 🚀 Start streaming pipeline cho real-time data
4. 📊 Setup Grafana dashboards
5. 🤖 Train ML models (xem BIGDATA_PROJECT_PLAN.md section 5.3)
6. 🌐 Build REST API
7. 📱 Create web dashboard

## Useful Commands

```bash
# Stop all services
docker-compose down

# Stop và xóa volumes
docker-compose down -v

# Restart một service
docker-compose restart kafka

# View logs của một service
docker-compose logs -f spark

# Scale a service
docker-compose up -d --scale kafka=3

# Execute command trong container
docker exec -it kafka bash
```

## Resources

- **Documentation**: Xem `BIGDATA_PROJECT_PLAN.md` và `ARCHITECTURE_DETAILS.md`
- **API Docs**: 
  - Football-Data: https://www.football-data.org/documentation/quickstart
  - Kafka: https://kafka.apache.org/documentation/
  - Spark: https://spark.apache.org/docs/latest/
- **Support**: GitHub Issues

---

**Good luck với dự án! ⚽🚀**
