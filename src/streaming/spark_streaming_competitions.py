"""
Spark Structured Streaming: Competitions & Leaderboards → PostgreSQL Pipeline
Kafka (raw JSON) → Normalize/Clean → Upsert to PostgreSQL

Architecture:
- Bronze Layer: Raw data from Kafka
- Silver Layer: Cleaned, normalized, validated data (flatten nested JSON)
- Postgres: Final storage with upsert logic to streaming schema

Usage:
    python src/streaming/spark_streaming_competitions.py

Environment Variables (.env):
- KAFKA_BOOTSTRAP_SERVERS
- KAFKA_API_KEY, KAFKA_API_SECRET
- KAFKA_TOPIC_COMPETITIONS=football-competitions
- KAFKA_TOPIC_LEADERBOARDS=football-leaderboards
- POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
- POSTGRES_USER, POSTGRES_PASSWORD
"""

import os
import sys
import signal
import logging
import warnings
from pathlib import Path
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, current_timestamp, lit, explode, when, coalesce,
    to_timestamp, to_date, row_number, to_json
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, LongType,
    ArrayType, MapType
)
from pyspark.sql.window import Window

# Suppress logging noise
logging.getLogger("py4j").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.ERROR)
warnings.filterwarnings("ignore")

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POSTGRESQL_JAR = PROJECT_ROOT / "jars" / "postgresql-42.7.1.jar"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# Global checkpoint location (like streaming_upsert.py)
# Each query will auto-create its own subdirectory with UUID (run ID)
CHECKPOINT_DIR = "/tmp/spark-checkpoints/football-competitions-leaderboards"


def create_spark_session():
    """Create Spark session with Kafka and Postgres support"""
    print("🔧 Creating Spark session...")
    
    if not POSTGRESQL_JAR.exists():
        print(f"⚠️  PostgreSQL JDBC jar not found at {POSTGRESQL_JAR}")
        print("   Download from: https://jdbc.postgresql.org/download/")
        sys.exit(1)
    
    os.environ["PYSPARK_PIN_THREAD"] = "true"
    
    builder = SparkSession.builder \
        .appName("football-competitions-leaderboards-streaming") \
        .master("local[*]") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
        .config("spark.jars", str(POSTGRESQL_JAR)) \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g")
    
    spark = builder.getOrCreate()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    return spark


def get_competitions_schema():
    """
    Define schema for SINGLE competition object from Kafka
    NiFi sends individual competition objects, NOT an array
    """
    return StructType([
        StructField("id", IntegerType(), False),
        StructField("name", StringType(), False),
        StructField("code", StringType(), False),
        StructField("type", StringType(), True),
        StructField("emblem", StringType(), True),
        StructField("plan", StringType(), True),
        StructField("area", StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("code", StringType(), True),
            StructField("flag", StringType(), True)
        ]), True),
        StructField("currentSeason", StructType([
            StructField("id", IntegerType(), True),
            StructField("startDate", StringType(), True),
            StructField("endDate", StringType(), True),
            StructField("currentMatchday", IntegerType(), True),
            StructField("winner", StructType([
                StructField("id", IntegerType(), True),
                StructField("name", StringType(), True)
            ]), True)
        ]), True),
        StructField("numberOfAvailableSeasons", IntegerType(), True),
        StructField("lastUpdated", StringType(), True)
    ])


def get_leaderboards_schema():
    """Define schema for leaderboards JSON from Kafka"""
    return StructType([
        StructField("filters", MapType(StringType(), StringType()), True),
        StructField("area", StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("code", StringType(), True),
            StructField("flag", StringType(), True)
        ]), True),
        StructField("competition", StructType([
            StructField("id", IntegerType(), False),
            StructField("name", StringType(), False),
            StructField("code", StringType(), False),
            StructField("type", StringType(), True),
            StructField("emblem", StringType(), True)
        ]), False),
        StructField("season", StructType([
            StructField("id", IntegerType(), False),
            StructField("startDate", StringType(), True),
            StructField("endDate", StringType(), True),
            StructField("currentMatchday", IntegerType(), True),
            StructField("winner", StructType([
                StructField("id", IntegerType(), True),
                StructField("name", StringType(), True)
            ]), True)
        ]), False),
        StructField("standings", ArrayType(
            StructType([
                StructField("stage", StringType(), True),
                StructField("type", StringType(), True),
                StructField("group", StringType(), True),
                StructField("table", ArrayType(
                    StructType([
                        StructField("position", IntegerType(), False),
                        StructField("team", StructType([
                            StructField("id", IntegerType(), False),
                            StructField("name", StringType(), False),
                            StructField("shortName", StringType(), True),
                            StructField("tla", StringType(), True),
                            StructField("crest", StringType(), True)
                        ]), False),
                        StructField("playedGames", IntegerType(), True),
                        StructField("form", StringType(), True),
                        StructField("won", IntegerType(), True),
                        StructField("draw", IntegerType(), True),
                        StructField("lost", IntegerType(), True),
                        StructField("points", IntegerType(), True),
                        StructField("goalsFor", IntegerType(), True),
                        StructField("goalsAgainst", IntegerType(), True),
                        StructField("goalDifference", IntegerType(), True)
                    ])
                ), True)
            ])
        ), True)
    ])


def normalize_competitions_to_silver(bronze_df):
    """
    Transform Bronze (raw Kafka) to Silver (normalized)
    Flatten nested JSON structures for SINGLE competition object
    NiFi sends individual objects, NOT arrays
    """
    # NO EXPLODE needed - data is already a single competition object
    silver_df = bronze_df.select(
        # Primary identifiers
        col("data.id").alias("competition_id"),
        col("data.name").alias("competition_name"),
        col("data.code").alias("competition_code"),
        col("data.type").alias("competition_type"),
        col("data.emblem").alias("emblem_url"),
        col("data.plan").alias("plan"),
        
        # Area (flat fields)
        col("data.area.id").alias("area_id"),
        col("data.area.name").alias("area_name"),
        col("data.area.code").alias("area_code"),
        col("data.area.flag").alias("area_flag_url"),
        
        # Current season (flat fields)
        col("data.currentSeason.id").alias("current_season_id"),
        to_date(col("data.currentSeason.startDate")).alias("season_start_date"),
        to_date(col("data.currentSeason.endDate")).alias("season_end_date"),
        coalesce(col("data.currentSeason.currentMatchday"), lit(0)).alias("current_matchday"),
        col("data.currentSeason.winner.id").alias("season_winner_id"),
        col("data.currentSeason.winner.name").alias("season_winner_name"),
        
        # Metadata
        coalesce(col("data.numberOfAvailableSeasons"), lit(0)).alias("number_of_available_seasons"),
        to_timestamp(col("data.lastUpdated"), "yyyy-MM-dd'T'HH:mm:ss'Z'").alias("last_updated"),
        
        # Audit
        current_timestamp().alias("processed_at")
    )
    
    # Data quality filter
    silver_df = silver_df.filter(
        (col("competition_id").isNotNull()) &
        (col("competition_name").isNotNull())
    )
    
    return silver_df


def normalize_leaderboards_to_silver(bronze_df):
    """
    Transform Bronze (raw Kafka) to Silver (normalized)
    Flatten nested JSON structures for leaderboards
    """
    # Explode standings array
    df_standings = bronze_df.select(
        col("data.area").alias("area"),
        col("data.competition").alias("competition"),
        col("data.season").alias("season"),
        explode(col("data.standings")).alias("standing"),
        col("raw_json")
    )
    
    # Explode table array
    df_exploded = df_standings.select(
        col("area"),
        col("competition"),
        col("season"),
        col("standing.stage").alias("stage"),
        col("standing.type").alias("standing_type"),
        col("standing.group").alias("group_name"),
        explode(col("standing.table")).alias("entry"),
        col("raw_json")
    )
    
    # Flatten structure
    silver_df = df_exploded.select(
        # Competition
        col("competition.id").alias("competition_id"),
        col("competition.name").alias("competition_name"),
        col("competition.code").alias("competition_code"),
        col("competition.type").alias("competition_type"),
        
        # Season
        col("season.id").alias("season_id"),
        to_date(col("season.startDate")).alias("season_start_date"),
        to_date(col("season.endDate")).alias("season_end_date"),
        coalesce(col("season.currentMatchday"), lit(0)).alias("current_matchday"),
        
        # Area
        col("area.id").alias("area_id"),
        col("area.name").alias("area_name"),
        col("area.code").alias("area_code"),
        
        # Standing details
        coalesce(col("stage"), lit("REGULAR_SEASON")).alias("stage"),
        coalesce(col("standing_type"), lit("TOTAL")).alias("standing_type"),
        col("group_name"),
        
        # Team position
        col("entry.position").alias("position"),
        col("entry.team.id").alias("team_id"),
        col("entry.team.name").alias("team_name"),
        col("entry.team.shortName").alias("team_short_name"),
        col("entry.team.tla").alias("team_tla"),
        col("entry.team.crest").alias("team_crest_url"),
        
        # Statistics
        coalesce(col("entry.playedGames"), lit(0)).alias("played_games"),
        coalesce(col("entry.won"), lit(0)).alias("won"),
        coalesce(col("entry.draw"), lit(0)).alias("draw"),
        coalesce(col("entry.lost"), lit(0)).alias("lost"),
        coalesce(col("entry.points"), lit(0)).alias("points"),
        coalesce(col("entry.goalsFor"), lit(0)).alias("goals_for"),
        coalesce(col("entry.goalsAgainst"), lit(0)).alias("goals_against"),
        coalesce(col("entry.goalDifference"), lit(0)).alias("goal_difference"),
        col("entry.form").alias("form"),
        
        # Audit
        current_timestamp().alias("processed_at")
    )
    
    # Data quality filter
    silver_df = silver_df.filter(
        (col("competition_id").isNotNull()) &
        (col("season_id").isNotNull()) &
        (col("team_id").isNotNull())
    )
    
    return silver_df


def write_competitions_to_postgres(batch_df, batch_id):
    """Process competitions microbatch: Bronze → Silver → Postgres"""
    if batch_df.isEmpty():
        print(f"⏭️  Batch {batch_id} (Competitions): No data", flush=True)
        return
    
    print(f"\n{'='*60}", flush=True)
    print(f"📦 Batch {batch_id} (Competitions): Processing {batch_df.count()} records...", flush=True)
    
    # BRONZE → SILVER
    silver_df = normalize_competitions_to_silver(batch_df)
    silver_count = silver_df.count()
    print(f"🥈 Batch {batch_id} (Competitions): Silver transformation complete - {silver_count} records", flush=True)
    
    # Deduplicate
    window_spec = Window.partitionBy("competition_id").orderBy(col("last_updated").desc())
    silver_df = silver_df.withColumn("row_num", row_number().over(window_spec)) \
                         .filter(col("row_num") == 1) \
                         .drop("row_num")
    dedup_count = silver_df.count()
    print(f"🔍 Batch {batch_id} (Competitions): After deduplication - {dedup_count} unique records", flush=True)
    
    # Postgres connection
    jdbc_url = f"jdbc:postgresql://{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'football_analytics')}"
    connection_properties = {
        "user": os.environ.get('POSTGRES_USER', 'postgres'),
        "password": os.environ.get('POSTGRES_PASSWORD', 'your_password'),
        "driver": "org.postgresql.Driver"
    }
    
    # Write to staging
    staging_table = "streaming.competitions_staging"
    print(f"💾 Batch {batch_id} (Competitions): Writing {dedup_count} records to staging table...", flush=True)
    silver_df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", staging_table) \
        .option("user", connection_properties["user"]) \
        .option("password", connection_properties["password"]) \
        .option("driver", connection_properties["driver"]) \
        .mode("append") \
        .save()
    print(f"✅ Batch {batch_id} (Competitions): Staging write complete", flush=True)
    
    # Execute upsert
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
        INSERT INTO streaming.competitions
            (competition_id, competition_name, competition_code, competition_type,
             emblem_url, plan, area_id, area_name, area_code, area_flag_url,
             current_season_id, season_start_date, season_end_date, current_matchday,
             season_winner_id, season_winner_name, number_of_available_seasons,
             last_updated, processed_at)
        SELECT 
            competition_id, competition_name, competition_code, competition_type,
            emblem_url, plan, area_id, area_name, area_code, area_flag_url,
            current_season_id, season_start_date, season_end_date, current_matchday,
            season_winner_id, season_winner_name, number_of_available_seasons,
            last_updated, processed_at
        FROM streaming.competitions_staging
        ON CONFLICT (competition_id) DO UPDATE SET
            competition_name = EXCLUDED.competition_name,
            competition_code = EXCLUDED.competition_code,
            competition_type = EXCLUDED.competition_type,
            emblem_url = EXCLUDED.emblem_url,
            plan = EXCLUDED.plan,
            area_id = EXCLUDED.area_id,
            area_name = EXCLUDED.area_name,
            area_code = EXCLUDED.area_code,
            area_flag_url = EXCLUDED.area_flag_url,
            current_season_id = EXCLUDED.current_season_id,
            season_start_date = EXCLUDED.season_start_date,
            season_end_date = EXCLUDED.season_end_date,
            current_matchday = EXCLUDED.current_matchday,
            season_winner_id = EXCLUDED.season_winner_id,
            season_winner_name = EXCLUDED.season_winner_name,
            number_of_available_seasons = EXCLUDED.number_of_available_seasons,
            last_updated = EXCLUDED.last_updated,
            processed_at = EXCLUDED.processed_at;
        """
        
        print(f"🔄 Batch {batch_id} (Competitions): Executing upsert to main table...", flush=True)
        cursor.execute(upsert_sql)
        upserted_count = cursor.rowcount
        conn.commit()
        
        # Cleanup staging
        cursor.execute("TRUNCATE TABLE streaming.competitions_staging;")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Batch {batch_id} (Competitions): Successfully upserted {upserted_count} records to main table", flush=True)
        print(f"🎯 Batch {batch_id} COMPLETE: Bronze({batch_df.count()}) → Silver({silver_count}) → Dedup({dedup_count}) → Postgres({upserted_count})", flush=True)
        print(f"{'='*60}\n", flush=True)
        
    except Exception as e:
        print(f"❌ Batch {batch_id} (Competitions): Error during upsert: {e}", flush=True)
        import traceback
        traceback.print_exc()
        import traceback
        traceback.print_exc()


def write_leaderboards_to_postgres(batch_df, batch_id):
    """Process leaderboards microbatch: Bronze → Silver → Postgres"""
    if batch_df.isEmpty():
        print(f"⏭️  Batch {batch_id} (Leaderboards): No data", flush=True)
        return
    
    print(f"\n{'='*60}", flush=True)
    print(f"📦 Batch {batch_id} (Leaderboards): Processing {batch_df.count()} records...", flush=True)
    
    # BRONZE → SILVER
    silver_df = normalize_leaderboards_to_silver(batch_df)
    silver_count = silver_df.count()
    print(f"🥈 Batch {batch_id} (Leaderboards): Silver transformation complete - {silver_count} records", flush=True)
    
    # Deduplicate
    window_spec = Window.partitionBy("competition_id", "season_id", "team_id", "stage", "standing_type", "group_name").orderBy(col("processed_at").desc())
    silver_df = silver_df.withColumn("row_num", row_number().over(window_spec)) \
                         .filter(col("row_num") == 1) \
                         .drop("row_num")
    dedup_count = silver_df.count()
    print(f"🔍 Batch {batch_id} (Leaderboards): After deduplication - {dedup_count} unique records", flush=True)
    
    # Postgres connection
    jdbc_url = f"jdbc:postgresql://{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'football_analytics')}"
    connection_properties = {
        "user": os.environ.get('POSTGRES_USER', 'postgres'),
        "password": os.environ.get('POSTGRES_PASSWORD', 'your_password'),
        "driver": "org.postgresql.Driver"
    }
    
    # Write to staging
    staging_table = "streaming.leaderboards_staging"
    print(f"💾 Batch {batch_id} (Leaderboards): Writing {dedup_count} records to staging table...", flush=True)
    silver_df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", staging_table) \
        .option("user", connection_properties["user"]) \
        .option("password", connection_properties["password"]) \
        .option("driver", connection_properties["driver"]) \
        .mode("append") \
        .save()
    print(f"✅ Batch {batch_id} (Leaderboards): Staging write complete", flush=True)
    
    # Execute upsert
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
        INSERT INTO streaming.leaderboards
            (competition_id, competition_name, competition_code, competition_type,
             season_id, season_start_date, season_end_date, current_matchday,
             area_id, area_name, area_code, stage, standing_type, group_name,
             position, team_id, team_name, team_short_name, team_tla, team_crest_url,
             played_games, won, draw, lost, points, goals_for, goals_against,
             goal_difference, form, processed_at)
        SELECT 
            competition_id, competition_name, competition_code, competition_type,
            season_id, season_start_date, season_end_date, current_matchday,
            area_id, area_name, area_code, stage, standing_type, group_name,
            position, team_id, team_name, team_short_name, team_tla, team_crest_url,
            played_games, won, draw, lost, points, goals_for, goals_against,
            goal_difference, form, processed_at
        FROM streaming.leaderboards_staging
        ON CONFLICT (competition_id, season_id, stage, standing_type, team_id, COALESCE(group_name, '')) 
        DO UPDATE SET
            competition_name = EXCLUDED.competition_name,
            competition_code = EXCLUDED.competition_code,
            competition_type = EXCLUDED.competition_type,
            season_start_date = EXCLUDED.season_start_date,
            season_end_date = EXCLUDED.season_end_date,
            current_matchday = EXCLUDED.current_matchday,
            area_id = EXCLUDED.area_id,
            area_name = EXCLUDED.area_name,
            area_code = EXCLUDED.area_code,
            position = EXCLUDED.position,
            team_name = EXCLUDED.team_name,
            team_short_name = EXCLUDED.team_short_name,
            team_tla = EXCLUDED.team_tla,
            team_crest_url = EXCLUDED.team_crest_url,
            played_games = EXCLUDED.played_games,
            won = EXCLUDED.won,
            draw = EXCLUDED.draw,
            lost = EXCLUDED.lost,
            points = EXCLUDED.points,
            goals_for = EXCLUDED.goals_for,
            goals_against = EXCLUDED.goals_against,
            goal_difference = EXCLUDED.goal_difference,
            form = EXCLUDED.form,
            processed_at = EXCLUDED.processed_at;
        """
        
        print(f"🔄 Batch {batch_id} (Leaderboards): Executing upsert to main table...", flush=True)
        cursor.execute(upsert_sql)
        upserted_count = cursor.rowcount
        conn.commit()
        
        # Cleanup staging
        cursor.execute("TRUNCATE TABLE streaming.leaderboards_staging;")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Batch {batch_id} (Leaderboards): Successfully upserted {upserted_count} records to main table", flush=True)
        print(f"🎯 Batch {batch_id} COMPLETE: Bronze({batch_df.count()}) → Silver({silver_count}) → Dedup({dedup_count}) → Postgres({upserted_count})", flush=True)
        print(f"{'='*60}\n", flush=True)
        
    except Exception as e:
        print(f"❌ Batch {batch_id} (Leaderboards): Error during upsert: {e}", flush=True)
        import traceback
        traceback.print_exc()
        import traceback
        traceback.print_exc()


def main():
    """Main streaming pipeline execution"""
    print("="*80, flush=True)
    print("🚀 Competitions & Leaderboards Streaming Pipeline", flush=True)
    print("   Kafka → Bronze → Silver → PostgreSQL", flush=True)
    print("="*80, flush=True)
    print(flush=True)
    
    # Load configuration
    config = {
        'kafka_bootstrap': os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'pkc-312o0.ap-southeast-1.aws.confluent.cloud:9092'),
        'kafka_api_key': os.environ.get('KAFKA_API_KEY', 'your_kafka_key'),
        'kafka_api_secret': os.environ.get('KAFKA_API_SECRET', 'your_kafka_secret'),
        'kafka_topic_competitions': os.environ.get('KAFKA_TOPIC_COMPETITIONS', 'live-competitions'),
        'kafka_topic_leaderboards': os.environ.get('KAFKA_TOPIC_LEADERBOARDS', 'live-leaderboards'),
        'postgres_host': os.environ.get('POSTGRES_HOST', 'localhost'),
        'postgres_port': os.environ.get('POSTGRES_PORT', '5432'),
        'postgres_db': os.environ.get('POSTGRES_DB', 'football_analytics'),
        'postgres_user': os.environ.get('POSTGRES_USER', 'postgres'),
        'postgres_password': os.environ.get('POSTGRES_PASSWORD', 'your_password')
    }
    
    print(f"📊 Configuration:", flush=True)
    print(f"   Kafka Bootstrap: {config['kafka_bootstrap']}", flush=True)
    print(f"   Competitions Topic: {config['kafka_topic_competitions']}", flush=True)
    print(f"   Leaderboards Topic: {config['kafka_topic_leaderboards']}", flush=True)
    print(f"   Postgres: {config['postgres_user']}@{config['postgres_host']}:{config['postgres_port']}/{config['postgres_db']}", flush=True)
    print(f"   Checkpoint: {CHECKPOINT_DIR} (auto-creates RUN ID subdirs, batch resets)", flush=True)
    print(f"   Trigger Interval: 60 seconds (aligned with NiFi 60s schedule)", flush=True)
    print(flush=True)
    
    try:
        # Create Spark session
        spark = create_spark_session()
        spark.sparkContext.setLogLevel("WARN")
        print("✅ Spark session created", flush=True)
        print(flush=True)
        
        # === COMPETITIONS STREAM ===
        print("🔗 Connecting to Kafka (Competitions)...", flush=True)
        competitions_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", config['kafka_bootstrap']) \
            .option("subscribe", config['kafka_topic_competitions']) \
            .option("startingOffsets", "latest") \
            .option("kafka.security.protocol", "SASL_SSL") \
            .option("kafka.sasl.mechanism", "PLAIN") \
            .option("kafka.sasl.jaas.config", 
                    f'org.apache.kafka.common.security.plain.PlainLoginModule required '
                    f'username="{config["kafka_api_key"]}" password="{config["kafka_api_secret"]}";') \
            .load()
        
        competitions_schema = get_competitions_schema()
        parsed_competitions = competitions_df.selectExpr("CAST(value AS STRING) as json_str", "CAST(value AS STRING) as raw_json") \
            .select(
                from_json(col("json_str"), competitions_schema).alias("data"),
                col("raw_json")
            )
        
        print("✅ Connected to Competitions stream", flush=True)
        
        # === LEADERBOARDS STREAM ===
        print("🔗 Connecting to Kafka (Leaderboards)...")
        leaderboards_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", config['kafka_bootstrap']) \
            .option("subscribe", config['kafka_topic_leaderboards']) \
            .option("startingOffsets", "latest") \
            .option("kafka.security.protocol", "SASL_SSL") \
            .option("kafka.sasl.mechanism", "PLAIN") \
            .option("kafka.sasl.jaas.config", 
                    f'org.apache.kafka.common.security.plain.PlainLoginModule required '
                    f'username="{config["kafka_api_key"]}" password="{config["kafka_api_secret"]}";') \
            .load()
        
        leaderboards_schema = get_leaderboards_schema()
        parsed_leaderboards = leaderboards_df.selectExpr("CAST(value AS STRING) as json_str", "CAST(value AS STRING) as raw_json") \
            .select(
                from_json(col("json_str"), leaderboards_schema).alias("data"),
                col("raw_json")
            )
        
        print("✅ Connected to Leaderboards stream", flush=True)
        print(flush=True)
        
        # Start streaming queries
        print("📊 Starting streaming queries...", flush=True)
        print("   Trigger: 60 seconds microbatch (aligned with NiFi 60s interval)", flush=True)
        print("   Press Ctrl+C to stop", flush=True)
        print(flush=True)
        
        # NiFi pushes every 60s, Spark processes every 60s (exactly 1 batch per trigger)
        # Global checkpoint → Each query auto-creates RUN ID subdirectory
        # Batch ID resets to 0 on each restart (like streaming_upsert)
        query_competitions = parsed_competitions.writeStream \
            .foreachBatch(write_competitions_to_postgres) \
            .trigger(processingTime='60 seconds') \
            .outputMode("append") \
            .start()
        
        query_leaderboards = parsed_leaderboards.writeStream \
            .foreachBatch(write_leaderboards_to_postgres) \
            .trigger(processingTime='60 seconds') \
            .outputMode("append") \
            .start()
        
        print("✅ Streaming queries started!", flush=True)
        print(flush=True)
        print()
        
        # Wait for termination
        try:
            spark.streams.awaitAnyTermination()
        except KeyboardInterrupt:
            import contextlib
            import io
            with contextlib.redirect_stderr(io.StringIO()):
                print("\n\n⚠️  Received Ctrl+C, stopping streaming...")
                try:
                    query_competitions.stop()
                    query_leaderboards.stop()
                except Exception:
                    pass
            print("✅ Streaming queries stopped")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Received Ctrl+C during initialization")
        
    except Exception as e:
        error_type = type(e).__name__
        if "Py4J" in error_type or "Network" in error_type:
            print("\n⚠️  Stream interrupted by user")
        else:
            print(f"\n❌ Error occurred: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    finally:
        if 'spark' in locals():
            import contextlib
            import io
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    spark.stop()
                except Exception:
                    pass
            print("🛑 Spark session stopped")
        print("\n👋 Pipeline stopped. Goodbye!\n")


if __name__ == '__main__':
    import contextlib
    import io
    
    class SuppressStderr:
        def __init__(self):
            self.original_stderr = sys.stderr
            self.suppress = False
            
        def write(self, text):
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
        print("\n👋 Stopped by user. Goodbye!\n")
        sys.exit(0)
