#!/usr/bin/env python3
"""
Live Events Spark Streaming Consumer
Consumes live match events from Kafka
Processes in micro-batches and writes to PostgreSQL
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, current_timestamp,
    when, lit, count, sum as _sum, avg
)
from pyspark.sql.types import *
import logging
import os
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Confluent Cloud Kafka Configuration
KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'pkc-xxxxx.region.provider.confluent.cloud:9092'),
    'sasl_jaas_config': f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{os.getenv("KAFKA_API_KEY", "your-api-key")}" password="{os.getenv("KAFKA_API_SECRET", "your-api-secret")}";',
    'sasl_mechanism': 'PLAIN',
    'security_protocol': 'SASL_SSL',
}
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'live-match-events')

# PostgreSQL Configuration
JDBC_URL = "jdbc:postgresql://localhost:5432/football_analytics"
JDBC_PROPERTIES = {
    'user': 'postgres',
    'password': '9281746356',
    'driver': 'org.postgresql.Driver'
}

# Match event schema from API
MATCH_EVENT_SCHEMA = StructType([
    StructField("match_id", StringType(), False),
    StructField("timestamp", StringType(), False),
    StructField("status", StringType(), True),
    StructField("utc_date", StringType(), True),
    StructField("minute", IntegerType(), True),
    
    StructField("competition_name", StringType(), True),
    StructField("competition_code", StringType(), True),
    
    StructField("home_team_id", IntegerType(), True),
    StructField("home_team_name", StringType(), True),
    StructField("home_team_short", StringType(), True),
    StructField("away_team_id", IntegerType(), True),
    StructField("away_team_name", StringType(), True),
    StructField("away_team_short", StringType(), True),
    
    StructField("home_score", IntegerType(), True),
    StructField("away_score", IntegerType(), True),
    StructField("half_time_home", IntegerType(), True),
    StructField("half_time_away", IntegerType(), True),
    
    StructField("venue", StringType(), True)
])


class LiveEventsConsumer:
    """Spark Structured Streaming consumer for live match events"""
    
    def __init__(self):
        """Initialize Spark session with Kafka support"""
        self.spark = SparkSession.builder \
            .appName('LiveEventsConsumer') \
            .config('spark.jars.packages', 
                   'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0') \
            .config('spark.jars', 'jars/postgresql-42.7.1.jar') \
            .config('spark.driver.memory', '4g') \
            .config('spark.executor.memory', '4g') \
            .config('spark.sql.streaming.checkpointLocation', '/tmp/spark_checkpoints') \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel('WARN')
        logger.info("✅ Spark session initialized with Kafka support")
    
    def read_kafka_stream(self):
        """Read streaming data from Confluent Cloud Kafka"""
        logger.info(f"📡 Connecting to Confluent Cloud Kafka: {KAFKA_CONFIG['bootstrap_servers']}")
        
        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_CONFIG['bootstrap_servers']) \
            .option("kafka.sasl.jaas.config", KAFKA_CONFIG['sasl_jaas_config']) \
            .option("kafka.sasl.mechanism", KAFKA_CONFIG['sasl_mechanism']) \
            .option("kafka.security.protocol", KAFKA_CONFIG['security_protocol']) \
            .option("subscribe", KAFKA_TOPIC) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()
        
        logger.info(f"✅ Connected to Kafka topic: {KAFKA_TOPIC}")
        return df
    
    def parse_events(self, kafka_df):
        """Parse JSON events from Kafka"""
        logger.info("🔍 Parsing JSON events...")
        
        # Parse JSON value
        parsed_df = kafka_df \
            .selectExpr("CAST(value AS STRING) as json_value") \
            .select(from_json(col("json_value"), MATCH_EVENT_SCHEMA).alias("data")) \
            .select("data.*")
        
        # Transform and enrich
        enriched_df = parsed_df \
            .withColumn("processed_at", current_timestamp()) \
            .withColumn("event_timestamp", to_timestamp(col("timestamp"))) \
            .withColumn("match_date", to_timestamp(col("utc_date"))) \
            .withColumn("total_goals", 
                col("home_score") + col("away_score")) \
            .withColumn("match_result",
                when(col("home_score") > col("away_score"), "HOME_WIN")
                .when(col("home_score") < col("away_score"), "AWAY_WIN")
                .when(col("status") == "IN_PLAY", "LIVE")
                .otherwise("DRAW")
            ) \
            .withColumn("is_live", col("status") == "IN_PLAY")
        
        return enriched_df
    
    def write_to_postgres(self, batch_df, batch_id):
        """Write micro-batch to PostgreSQL"""
        try:
            if batch_df.isEmpty():
                logger.info(f"📦 Batch {batch_id}: No data to write")
                return
            
            count = batch_df.count()
            logger.info(f"📦 Batch {batch_id}: Processing {count} events")
            
            # Select columns for streaming.live_events table
            output_df = batch_df.select(
                col("match_id"),
                col("event_timestamp"),
                col("status"),
                col("minute"),
                col("competition_name"),
                col("competition_code"),
                col("home_team_name"),
                col("away_team_name"),
                col("home_score"),
                col("away_score"),
                col("total_goals"),
                col("match_result"),
                col("venue"),
                col("is_live"),
                col("processed_at")
            )
            
            # Write to PostgreSQL (append mode)
            output_df.write \
                .jdbc(url=JDBC_URL, 
                     table='streaming.live_events',
                     mode='append',
                     properties=JDBC_PROPERTIES)
            
            logger.info(f"✅ Batch {batch_id}: {count} events written to PostgreSQL")
            
            # Log live matches
            live_count = batch_df.filter(col("is_live")).count()
            if live_count > 0:
                logger.info(f"⚽ {live_count} LIVE matches in this batch")
                
                live_matches = batch_df.filter(col("is_live")).collect()
                for match in live_matches:
                    logger.info(f"   🔴 {match.home_team_name} {match.home_score}-{match.away_score} "
                              f"{match.away_team_name} (Minute: {match.minute})")
        
        except Exception as e:
            logger.error(f"❌ Batch {batch_id} failed: {e}")
            import traceback
            traceback.print_exc()
    
    def run_streaming(self):
        """Start streaming pipeline"""
        logger.info("="*80)
        logger.info("  LIVE EVENTS SPARK STREAMING CONSUMER")
        logger.info(f"  Kafka: Confluent Cloud → Topic: {KAFKA_TOPIC}")
        logger.info(f"  Output: PostgreSQL streaming.live_events")
        logger.info(f"  Micro-batch interval: 30 seconds")
        logger.info("="*80)
        
        try:
            # Read from Kafka
            kafka_stream = self.read_kafka_stream()
            
            # Parse and transform
            events_stream = self.parse_events(kafka_stream)
            
            # Write to PostgreSQL in micro-batches
            query = events_stream \
                .writeStream \
                .foreachBatch(self.write_to_postgres) \
                .outputMode("append") \
                .trigger(processingTime='30 seconds') \
                .start()
            
            logger.info("🚀 Streaming started! Listening for events...")
            logger.info("   Press Ctrl+C to stop\n")
            
            query.awaitTermination()
        
        except KeyboardInterrupt:
            logger.info("\n🛑 Streaming stopped by user")
        
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        logger.info("✅ Spark session stopped")


def main():
    """Main execution"""
    consumer = LiveEventsConsumer()
    consumer.run_streaming()


if __name__ == "__main__":
    main()
