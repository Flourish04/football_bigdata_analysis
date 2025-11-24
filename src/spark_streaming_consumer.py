"""
Spark Streaming Consumer for Football Analytics
Processes live match data from Kafka in real-time
"""

import json
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, current_timestamp, window, 
    avg, count, sum as spark_sum, lit
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    TimestampType, DoubleType
)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'live-matches'
CHECKPOINT_DIR = '/tmp/spark-checkpoints'
POSTGRES_URL = 'jdbc:postgresql://localhost:5432/football_analytics'
POSTGRES_USER = 'football_user'
POSTGRES_PASSWORD = 'football_pass'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session with required configurations"""
    spark = SparkSession.builder \
        .appName("Football Live Match Streaming") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,"
                "org.postgresql:postgresql:42.6.0") \
        .config("spark.streaming.kafka.maxRatePerPartition", "1000") \
        .config("spark.streaming.backpressure.enabled", "true") \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR) \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info("Spark session created")
    return spark


def define_schema():
    """Define the schema for incoming match data"""
    return StructType([
        StructField("match_id", IntegerType(), True),
        StructField("status", StringType(), True),
        StructField("minute", IntegerType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("competition", StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("code", StringType(), True)
        ])),
        StructField("home_team", StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("crest", StringType(), True)
        ])),
        StructField("away_team", StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("crest", StringType(), True)
        ])),
        StructField("score", StructType([
            StructField("home", IntegerType(), True),
            StructField("away", IntegerType(), True),
            StructField("winner", StringType(), True)
        ])),
        StructField("utc_date", TimestampType(), True)
    ])


def read_from_kafka(spark, topic):
    """Read streaming data from Kafka"""
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    logger.info(f"Reading from Kafka topic: {topic}")
    return df


def parse_json_data(df, schema):
    """Parse JSON data from Kafka"""
    parsed_df = df.select(
        from_json(col("value").cast("string"), schema).alias("data"),
        col("timestamp").alias("kafka_timestamp")
    ).select("data.*", "kafka_timestamp")
    
    return parsed_df


def enrich_match_data(df):
    """Enrich match data with additional calculations"""
    enriched_df = df \
        .withColumn("total_goals", 
                   col("score.home") + col("score.away")) \
        .withColumn("goal_difference", 
                   col("score.home") - col("score.away")) \
        .withColumn("is_draw", 
                   col("score.home") == col("score.away")) \
        .withColumn("processing_time", current_timestamp())
    
    return enriched_df


def calculate_live_statistics(df):
    """Calculate real-time statistics"""
    stats_df = df \
        .withWatermark("timestamp", "10 seconds") \
        .groupBy(
            window("timestamp", "1 minute"),
            "competition.name"
        ) \
        .agg(
            count("match_id").alias("matches_count"),
            avg("total_goals").alias("avg_goals"),
            spark_sum("total_goals").alias("total_goals"),
            count(col("is_draw")).alias("draws_count")
        )
    
    return stats_df


def write_to_postgres(df, table_name, mode="append"):
    """Write streaming data to PostgreSQL"""
    def write_batch(batch_df, batch_id):
        try:
            batch_df.write \
                .format("jdbc") \
                .option("url", POSTGRES_URL) \
                .option("dbtable", table_name) \
                .option("user", POSTGRES_USER) \
                .option("password", POSTGRES_PASSWORD) \
                .option("driver", "org.postgresql.Driver") \
                .mode(mode) \
                .save()
            
            logger.info(f"Batch {batch_id} written to {table_name}")
        except Exception as e:
            logger.error(f"Error writing batch {batch_id}: {e}")
    
    query = df.writeStream \
        .foreachBatch(write_batch) \
        .outputMode("append") \
        .trigger(processingTime='10 seconds') \
        .start()
    
    return query


def write_to_console(df, output_mode="append"):
    """Write streaming data to console for debugging"""
    query = df.writeStream \
        .outputMode(output_mode) \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime='10 seconds') \
        .start()
    
    return query


def detect_goals(df):
    """Detect goal events (score changes)"""
    # This is simplified - in production, you'd compare with previous state
    goals_df = df \
        .filter(col("total_goals") > 0) \
        .select(
            "match_id",
            "home_team.name",
            "away_team.name",
            "score.home",
            "score.away",
            "total_goals",
            "minute",
            "timestamp"
        )
    
    return goals_df


def main():
    """Main streaming application"""
    # Create Spark session
    spark = create_spark_session()
    
    # Define schema
    schema = define_schema()
    
    # Read from Kafka
    raw_stream = read_from_kafka(spark, KAFKA_TOPIC)
    
    # Parse JSON data
    parsed_stream = parse_json_data(raw_stream, schema)
    
    # Enrich data
    enriched_stream = enrich_match_data(parsed_stream)
    
    # Calculate statistics
    stats_stream = calculate_live_statistics(enriched_stream)
    
    # Detect goals
    goals_stream = detect_goals(enriched_stream)
    
    # Write to console (for development)
    console_query = write_to_console(enriched_stream)
    
    # Write statistics to console
    stats_console_query = write_to_console(stats_stream, output_mode="complete")
    
    # Write goals to console
    goals_console_query = write_to_console(goals_stream)
    
    # In production, also write to PostgreSQL:
    # postgres_query = write_to_postgres(enriched_stream, "live_match_events")
    
    logger.info("Streaming queries started")
    
    # Wait for termination
    try:
        spark.streams.awaitAnyTermination()
    except KeyboardInterrupt:
        logger.info("Shutting down streaming queries...")
        spark.stop()


if __name__ == '__main__':
    main()
