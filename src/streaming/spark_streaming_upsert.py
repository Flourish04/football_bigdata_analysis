"""
Spark Structured Streaming: Bronze → Silver → Postgres Pipeline
Kafka (raw JSON) → Normalize/Clean → Upsert to PostgreSQL

Architecture:
- Bronze Layer: Raw data from Kafka
- Silver Layer: Cleaned, normalized, validated data
- Postgres: Final storage with upsert logic

Usage:
    # Simple way - just run with python:
    python src/streaming/spark_streaming_upsert.py
    
    # Or with environment variables:
    KAFKA_BOOTSTRAP_SERVERS=<your-server> \
    KAFKA_API_KEY=<your-key> \
    KAFKA_API_SECRET=<your-secret> \
    python src/streaming/spark_streaming_upsert.py

Default Configuration (from environment or defaults):
- Kafka: pkc-312o0.ap-southeast-1.aws.confluent.cloud:9092
- Topic: live-match-events
- Postgres: localhost:5432/football_analytics
- Trigger: 30 seconds microbatch
"""

import os
import sys
import signal
import logging
import warnings
from pathlib import Path
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, lit, current_timestamp, to_json, coalesce, when, from_utc_timestamp
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, 
    IntegerType, MapType, ArrayType
)

# Suppress all Py4J and PySpark error logging
logging.getLogger("py4j").setLevel(logging.CRITICAL)
logging.getLogger("py4j.java_gateway").setLevel(logging.CRITICAL)
logging.getLogger("py4j.clientserver").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.ERROR)
warnings.filterwarnings("ignore")

# Get project root directory (2 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POSTGRESQL_JAR = PROJECT_ROOT / "jars" / "postgresql-42.7.1.jar"

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / ".env")

def create_spark_session():
    """
    Create Spark session with Kafka and Postgres support.
    Automatically downloads Kafka connector and includes Postgres JDBC driver.
    """
    print("[SETUP] Creating Spark session with dependencies...")
    
    # Check if PostgreSQL JDBC jar exists
    if not POSTGRESQL_JAR.exists():
        print(f"[WARNING]  Warning: PostgreSQL JDBC jar not found at {POSTGRESQL_JAR}")
        print("   Download it from: https://jdbc.postgresql.org/download/")
        sys.exit(1)
    
    # Disable PySpark's signal handler to avoid noisy Py4J errors on Ctrl+C
    os.environ["PYSPARK_PIN_THREAD"] = "true"
    
    builder = SparkSession.builder \
        .appName("football-kafka-postgres-streaming") \
        .master("local[*]") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
        .config("spark.jars", str(POSTGRESQL_JAR)) \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints/football") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g")
    
    spark = builder.getOrCreate()
    
    # Remove Spark's SIGINT handler to prevent noisy shutdown
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    return spark

def get_match_schema():
    """Define schema for match JSON from Kafka"""
    return StructType([
        StructField("id", LongType(), True),
        StructField("utcDate", StringType(), True),
        StructField("status", StringType(), True),
        StructField("matchday", IntegerType(), True),
        StructField("stage", StringType(), True),
        StructField("lastUpdated", StringType(), True),
        StructField("area", MapType(StringType(), StringType()), True),
        StructField("competition", MapType(StringType(), StringType()), True),
        StructField("season", MapType(StringType(), StringType()), True),
        StructField("homeTeam", MapType(StringType(), StringType()), True),
        StructField("awayTeam", MapType(StringType(), StringType()), True),
        StructField("score", StructType([
            StructField("winner", StringType(), True),
            StructField("duration", StringType(), True),
            StructField("fullTime", StructType([
                StructField("home", IntegerType(), True),
                StructField("away", IntegerType(), True)
            ]), True),
            StructField("halfTime", StructType([
                StructField("home", IntegerType(), True),
                StructField("away", IntegerType(), True)
            ]), True)
        ]), True),
        StructField("referees", ArrayType(MapType(StringType(), StringType())), True),
        StructField("odds", MapType(StringType(), StringType()), True)
    ])

def normalize_to_silver(bronze_df):
    """
    Transform Bronze layer (raw Kafka data) to Silver layer (HYBRID design)
    
    Hybrid Design:
    - Frequently queried fields → FLAT columns (IDs, names)
    - Metadata/rare queries → JSONB (details, URLs)
    
    Data Quality Checks:
    - Remove nulls in critical fields
    - Validate timestamps
    - Normalize data types
    - Handle missing scores
    """
    from pyspark.sql.functions import when, coalesce, to_date
    
    silver_df = bronze_df.select(
        # === PRIMARY IDENTIFIERS ===
        col("id").alias("match_id"),
        # Convert UTC to UTC+7 (Vietnam timezone)
        from_utc_timestamp(
            to_timestamp(col("utcDate"), "yyyy-MM-dd'T'HH:mm:ss'Z'"), 
            "Asia/Ho_Chi_Minh"
        ).alias("utc_date"),
        from_utc_timestamp(
            to_timestamp(col("lastUpdated"), "yyyy-MM-dd'T'HH:mm:ss'Z'"),
            "Asia/Ho_Chi_Minh"
        ).alias("last_updated"),
        
        # === MATCH METADATA ===
        col("status"),
        coalesce(col("matchday"), lit(0)).alias("matchday"),
        coalesce(col("stage"), lit("UNKNOWN")).alias("stage"),
        
        # === AREA (FLAT: IDs & names for queries) ===
        col("area.id").cast("integer").alias("area_id"),
        col("area.name").alias("area_name"),
        col("area.code").alias("area_code"),
        
        # === COMPETITION (FLAT: IDs & names for queries) ===
        col("competition.id").cast("integer").alias("competition_id"),
        col("competition.name").alias("competition_name"),
        col("competition.code").alias("competition_code"),
        
        # === SEASON (FLAT: IDs & dates for time queries) ===
        col("season.id").cast("integer").alias("season_id"),
        to_date(col("season.startDate")).alias("season_start_date"),
        to_date(col("season.endDate")).alias("season_end_date"),
        
        # === HOME TEAM (FLAT: IDs & names for queries) ===
        col("homeTeam.id").cast("integer").alias("home_team_id"),
        col("homeTeam.name").alias("home_team_name"),
        col("homeTeam.shortName").alias("home_team_short_name"),
        col("homeTeam.tla").alias("home_team_tla"),
        
        # === AWAY TEAM (FLAT: IDs & names for queries) ===
        col("awayTeam.id").cast("integer").alias("away_team_id"),
        col("awayTeam.name").alias("away_team_name"),
        col("awayTeam.shortName").alias("away_team_short_name"),
        col("awayTeam.tla").alias("away_team_tla"),
        
        # === SCORES (FLAT: for statistics) ===
        coalesce(col("score.winner"), lit("DRAW")).alias("winner"),
        coalesce(col("score.duration"), lit("REGULAR")).alias("duration"),
        coalesce(col("score.fullTime.home"), lit(0)).alias("ft_home_goals"),
        coalesce(col("score.fullTime.away"), lit(0)).alias("ft_away_goals"),
        coalesce(col("score.halfTime.home"), lit(0)).alias("ht_home_goals"),
        coalesce(col("score.halfTime.away"), lit(0)).alias("ht_away_goals"),
        
        # === JSONB DETAILS (metadata, rarely queried) ===
        to_json(col("area")).alias("area_details"),
        to_json(col("competition")).alias("competition_details"),
        to_json(col("season")).alias("season_details"),
        to_json(col("homeTeam")).alias("home_team_details"),
        to_json(col("awayTeam")).alias("away_team_details"),
        to_json(col("score")).alias("score_details"),
        to_json(col("referees")).alias("referees"),
        
        # === AUDIT TRAIL ===
        col("raw_json").alias("raw"),
        current_timestamp().alias("processing_ts")
    )
    
    # Data quality filters
    silver_df = silver_df.filter(
        (col("match_id").isNotNull()) &
        (col("utc_date").isNotNull()) &
        (col("status").isNotNull())
    )
    
    return silver_df

def write_to_postgres(batch_df, batch_id):
    """
    Process microbatch through Bronze → Silver → Postgres pipeline
    
    Pipeline:
    1. Bronze: Raw data from Kafka
    2. Silver: Normalized, cleaned, deduplicated
    3. Postgres: Upsert to final table
    """
    if batch_df.isEmpty():
        print(f"Batch {batch_id}: No data to process")
        return
    
    print(f"[BATCH] Batch {batch_id}: Processing {batch_df.count()} records (Bronze layer)...")
    
    # BRONZE → SILVER: Normalize and clean data
    print(f"[PROCESS] Batch {batch_id}: Transforming to Silver layer...")
    silver_df = normalize_to_silver(batch_df)
    print(f"[SUCCESS] Batch {batch_id}: Silver layer - {silver_df.count()} records after quality checks")
    
    # Deduplicate within batch - keep latest record for each match_id
    from pyspark.sql.window import Window
    from pyspark.sql.functions import row_number
    
    window_spec = Window.partitionBy("match_id").orderBy(col("last_updated").desc())
    silver_df = silver_df.withColumn("row_num", row_number().over(window_spec)) \
                         .filter(col("row_num") == 1) \
                         .drop("row_num")
    print(f"[CHECK] Batch {batch_id}: After deduplication - {silver_df.count()} unique matches")
    
    # Postgres connection properties
    jdbc_url = f"jdbc:postgresql://{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'football_analytics')}"
    connection_properties = {
        "user": os.environ.get('POSTGRES_USER', 'postgres'),
        "password": os.environ.get('POSTGRES_PASSWORD', 'your_password'),
        "driver": "org.postgresql.Driver"
    }
    
    # SILVER → POSTGRES: Write to staging table
    print(f"[SAVE] Batch {batch_id}: Writing Silver data to Postgres staging...")
    staging_table = "streaming.football_matches_staging"
    silver_df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", staging_table) \
        .option("user", connection_properties["user"]) \
        .option("password", connection_properties["password"]) \
        .option("driver", connection_properties["driver"]) \
        .mode("append") \
        .save()
    
    print(f"[SUCCESS] Batch {batch_id}: Wrote {silver_df.count()} records to staging table")
    
    # Execute upsert from staging to main table
    import psycopg2
    try:
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=os.environ.get('POSTGRES_PORT', '5432'),
            database=os.environ.get('POSTGRES_DB', 'football_analytics'),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ.get('POSTGRES_PASSWORD', 'your_password')
        )
        cursor = conn.cursor()
        
        upsert_sql = """
        INSERT INTO streaming.football_matches 
            (match_id, utc_date, last_updated, status, matchday, stage,
             area_id, area_name, area_code,
             competition_id, competition_name, competition_code,
             season_id, season_start_date, season_end_date,
             home_team_id, home_team_name, home_team_short_name, home_team_tla,
             away_team_id, away_team_name, away_team_short_name, away_team_tla,
             winner, duration, ft_home_goals, ft_away_goals, ht_home_goals, ht_away_goals,
             area_details, competition_details, season_details, 
             home_team_details, away_team_details, score_details, referees,
             raw, processing_ts)
        SELECT 
            match_id, utc_date, last_updated, status, matchday, stage,
            area_id, area_name, area_code,
            competition_id, competition_name, competition_code,
            season_id, season_start_date, season_end_date,
            home_team_id, home_team_name, home_team_short_name, home_team_tla,
            away_team_id, away_team_name, away_team_short_name, away_team_tla,
            winner, duration, ft_home_goals, ft_away_goals, ht_home_goals, ht_away_goals,
            area_details::jsonb, competition_details::jsonb, season_details::jsonb,
            home_team_details::jsonb, away_team_details::jsonb, score_details::jsonb, referees::jsonb,
            raw::jsonb, processing_ts
        FROM streaming.football_matches_staging
        ON CONFLICT (match_id) DO UPDATE SET
            utc_date = EXCLUDED.utc_date,
            last_updated = EXCLUDED.last_updated,
            status = EXCLUDED.status,
            matchday = EXCLUDED.matchday,
            stage = EXCLUDED.stage,
            area_id = EXCLUDED.area_id,
            area_name = EXCLUDED.area_name,
            area_code = EXCLUDED.area_code,
            competition_id = EXCLUDED.competition_id,
            competition_name = EXCLUDED.competition_name,
            competition_code = EXCLUDED.competition_code,
            season_id = EXCLUDED.season_id,
            season_start_date = EXCLUDED.season_start_date,
            season_end_date = EXCLUDED.season_end_date,
            home_team_id = EXCLUDED.home_team_id,
            home_team_name = EXCLUDED.home_team_name,
            home_team_short_name = EXCLUDED.home_team_short_name,
            home_team_tla = EXCLUDED.home_team_tla,
            away_team_id = EXCLUDED.away_team_id,
            away_team_name = EXCLUDED.away_team_name,
            away_team_short_name = EXCLUDED.away_team_short_name,
            away_team_tla = EXCLUDED.away_team_tla,
            winner = EXCLUDED.winner,
            duration = EXCLUDED.duration,
            ft_home_goals = EXCLUDED.ft_home_goals,
            ft_away_goals = EXCLUDED.ft_away_goals,
            ht_home_goals = EXCLUDED.ht_home_goals,
            ht_away_goals = EXCLUDED.ht_away_goals,
            area_details = EXCLUDED.area_details,
            competition_details = EXCLUDED.competition_details,
            season_details = EXCLUDED.season_details,
            home_team_details = EXCLUDED.home_team_details,
            away_team_details = EXCLUDED.away_team_details,
            score_details = EXCLUDED.score_details,
            referees = EXCLUDED.referees,
            raw = EXCLUDED.raw,
            processing_ts = EXCLUDED.processing_ts;
        """
        
        print(f"[PROCESS] Batch {batch_id}: Executing upsert to main table...")
        cursor.execute(upsert_sql)
        upserted_count = cursor.rowcount
        conn.commit()
        
        # Clear staging table
        cursor.execute("TRUNCATE TABLE streaming.football_matches_staging;")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"[SUCCESS] Batch {batch_id}: Successfully upserted {upserted_count} records to main table")
        print(f"[COMPLETE] Batch {batch_id} COMPLETE: Bronze({batch_df.count()}) → Silver({silver_df.count()}) → Postgres({upserted_count})")
        
    except Exception as e:
        print(f"[ERROR] Batch {batch_id}: Error during upsert: {e}")
        import traceback
        traceback.print_exc()

def main():
    """
    Main function to run the streaming pipeline.
    Automatically loads configuration from environment variables or uses defaults.
    """
    print("="*60)
    print("[START] Football Match Streaming Pipeline")
    print("   Bronze → Silver → Postgres")
    print("="*60)
    print()
    
    # Load configuration from environment or use defaults
    config = {
        'kafka_bootstrap': os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'pkc-312o0.ap-southeast-1.aws.confluent.cloud:9092'),
        'kafka_api_key': os.environ.get('KAFKA_API_KEY', 'your_kafka_key'),
        'kafka_api_secret': os.environ.get('KAFKA_API_SECRET', 'your_kafka_secret'),
        'kafka_topic': os.environ.get('KAFKA_TOPIC', 'live-match-events'),
        'postgres_host': os.environ.get('POSTGRES_HOST', 'localhost'),
        'postgres_port': os.environ.get('POSTGRES_PORT', '5432'),
        'postgres_db': os.environ.get('POSTGRES_DB', 'football_analytics'),
        'postgres_user': os.environ.get('POSTGRES_USER', 'postgres'),
        'postgres_password': os.environ.get('POSTGRES_PASSWORD', 'your_password')
    }
    
    print(f"[CONFIG] Configuration:")
    print(f"   Kafka Bootstrap: {config['kafka_bootstrap']}")
    print(f"   Kafka Topic: {config['kafka_topic']}")
    print(f"   Postgres: {config['postgres_user']}@{config['postgres_host']}:{config['postgres_port']}/{config['postgres_db']}")
    print(f"   Checkpoint: /tmp/spark-checkpoints/football")
    print(f"   Trigger Interval: 30 seconds")
    print()
    
    try:
        # Create Spark session
        spark = create_spark_session()
        spark.sparkContext.setLogLevel("WARN")
        
        print("[SUCCESS] Spark session created")
        print()
        
        # Read from Kafka
        print("[CONNECT] Connecting to Kafka...")
        df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", config['kafka_bootstrap']) \
            .option("subscribe", config['kafka_topic']) \
            .option("startingOffsets", "latest") \
            .option("kafka.security.protocol", "SASL_SSL") \
            .option("kafka.sasl.mechanism", "PLAIN") \
            .option("kafka.sasl.jaas.config", 
                    f'org.apache.kafka.common.security.plain.PlainLoginModule required '
                    f'username="{config["kafka_api_key"]}" password="{config["kafka_api_secret"]}";') \
            .load()
        
        print("[SUCCESS] Connected to Kafka stream")
        print()
        
        # Parse JSON
        match_schema = get_match_schema()
        
        parsed_df = df.selectExpr("CAST(value AS STRING) as json_str", "CAST(value AS STRING) as raw_json") \
            .select(
                from_json(col("json_str"), match_schema).alias("data"),
                col("raw_json")
            ) \
            .select("data.*", "raw_json")
        
        print("[CONFIG] Starting streaming query...")
        print("   Trigger: 15 seconds microbatch (aligned with NiFi 10s interval)")
        print("   Press Ctrl+C to stop")
        print()
        
        # Write stream with foreachBatch
        # NiFi pushes every 10s, Spark processes every 15s (allows 1-2 batches per trigger)
        query = parsed_df.writeStream \
            .foreachBatch(write_to_postgres) \
            .trigger(processingTime='15 seconds') \
            .outputMode("append") \
            .start()
        
        print("[SUCCESS] Streaming query started!")
        print()
        
        # Wait for termination with proper signal handling
        try:
            query.awaitTermination()
        except KeyboardInterrupt:
            # Suppress all stderr output during Ctrl+C cleanup
            import contextlib
            import io
            
            # Redirect stderr to suppress Py4J tracebacks
            with contextlib.redirect_stderr(io.StringIO()):
                print("\n\n[WARNING]  Received Ctrl+C, stopping streaming...")
                try:
                    query.stop()
                except Exception:
                    pass
            print("[SUCCESS] Streaming query stopped")
        
    except KeyboardInterrupt:
        print("\n\n[WARNING]  Received Ctrl+C during initialization")
        
    except Exception as e:
        # Ignore Py4J errors during shutdown
        error_type = type(e).__name__
        if "Py4J" in error_type or "Network" in error_type:
            print("\n[WARNING]  Stream interrupted by user")
        else:
            print(f"\n[ERROR] Error occurred: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    finally:
        if 'spark' in locals():
            # Suppress all stderr during Spark cleanup
            import contextlib
            import io
            
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    spark.stop()
                except Exception:
                    pass
            print("[STOP] Spark session stopped")
        print("\n[BYE] Pipeline stopped. Goodbye!\n")

if __name__ == '__main__':
    import contextlib
    import io
    
    # Override sys.stderr to suppress Py4J errors
    class SuppressStderr:
        def __init__(self):
            self.original_stderr = sys.stderr
            self.suppress = False
            
        def write(self, text):
            # Suppress Py4J errors during shutdown
            if self.suppress and any(x in text for x in ['ERROR:root:', 'Traceback', 'py4j', 'Py4JError', 'RuntimeError']):
                return
            self.original_stderr.write(text)
            
        def flush(self):
            self.original_stderr.flush()
    
    suppressor = SuppressStderr()
    sys.stderr = suppressor
    
    try:
        main()
    except KeyboardInterrupt:
        suppressor.suppress = True
        print("\n[BYE] Stopped by user. Goodbye!\n")
        sys.exit(0)
