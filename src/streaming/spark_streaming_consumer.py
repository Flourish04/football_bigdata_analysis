"""
Spark Structured Streaming Consumer for Live Football Matches
Consumes from Kafka and writes to PostgreSQL + Parquet
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, current_timestamp, window,
    count, sum as _sum, avg, max as _max, min as _min
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    TimestampType, LongType
)
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Schema definitions
MATCH_SCHEMA = StructType([
    StructField("match_id", LongType(), False),
    StructField("timestamp", TimestampType(), False),
    StructField("competition", StringType(), True),
    StructField("competition_id", IntegerType(), True),
    StructField("country", StringType(), True),
    StructField("season", IntegerType(), True),
    StructField("home_team", StringType(), False),
    StructField("home_team_id", IntegerType(), True),
    StructField("away_team", StringType(), False),
    StructField("away_team_id", IntegerType(), True),
    StructField("home_score", IntegerType(), True),
    StructField("away_score", IntegerType(), True),
    StructField("status", StringType(), True),
    StructField("status_short", StringType(), True),
    StructField("minute", IntegerType(), True),
    StructField("venue", StringType(), True),
    StructField("referee", StringType(), True)
])

EVENT_SCHEMA = StructType([
    StructField("match_id", LongType(), False),
    StructField("timestamp", TimestampType(), False),
    StructField("event_type", StringType(), False),
    StructField("detail", StringType(), True),
    StructField("minute", IntegerType(), True),
    StructField("extra_time", IntegerType(), True),
    StructField("team", StringType(), True),
    StructField("team_id", IntegerType(), True),
    StructField("player_id", IntegerType(), True),
    StructField("player_name", StringType(), True),
    StructField("assist_player_id", IntegerType(), True),
    StructField("assist_player_name", StringType(), True),
    StructField("comments", StringType(), True)
])


class LiveMatchStreamProcessor:
    """Spark Structured Streaming processor for live matches"""
    
    def __init__(self):
        self.spark = None
        self.kafka_bootstrap_servers = os.getenv(
            'KAFKA_BOOTSTRAP_SERVERS',
            'localhost:9092'
        )
        self.checkpoint_location = os.getenv(
            'CHECKPOINT_LOCATION',
            '/tmp/spark-checkpoints'
        )
        self.output_path = os.getenv(
            'STREAMING_OUTPUT_PATH',
            '/tmp/football_streaming'
        )
        
        # PostgreSQL config
        self.pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'football_analytics'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '9281746356')
        }
        
    def create_spark_session(self):
        """Initialize Spark session with Kafka support"""
        self.spark = SparkSession.builder \
            .appName('FootballLiveStreaming') \
            .config('spark.jars.packages', 
                   'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,'
                   'org.postgresql:postgresql:42.7.1') \
            .config('spark.sql.streaming.checkpointLocation', 
                   self.checkpoint_location) \
            .config('spark.sql.shuffle.partitions', '4') \
            .config('spark.streaming.kafka.maxRatePerPartition', '100') \
            .config('spark.sql.streaming.metricsEnabled', 'true') \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel('WARN')
        logger.info("Spark session created")
        
    def read_kafka_stream(self, topic):
        """Read from Kafka topic"""
        return self.spark \
            .readStream \
            .format('kafka') \
            .option('kafka.bootstrap.servers', self.kafka_bootstrap_servers) \
            .option('subscribe', topic) \
            .option('startingOffsets', 'latest') \
            .option('failOnDataLoss', 'false') \
            .load()
    
    def process_live_matches(self):
        """Process live match stream"""
        logger.info("Starting live matches stream...")
        
        # Read from Kafka
        kafka_df = self.read_kafka_stream('live-matches')
        
        # Parse JSON
        matches_df = kafka_df \
            .select(
                from_json(col('value').cast('string'), MATCH_SCHEMA).alias('data')
            ) \
            .select('data.*') \
            .withColumn('processing_time', current_timestamp())
        
        # Write to PostgreSQL (append mode)
        jdbc_url = (
            f"jdbc:postgresql://{self.pg_config['host']}:"
            f"{self.pg_config['port']}/{self.pg_config['database']}"
        )
        
        query = matches_df \
            .writeStream \
            .outputMode('append') \
            .format('jdbc') \
            .option('url', jdbc_url) \
            .option('dbtable', 'streaming.live_matches') \
            .option('user', self.pg_config['user']) \
            .option('password', self.pg_config['password']) \
            .option('driver', 'org.postgresql.Driver') \
            .option('checkpointLocation', 
                   f"{self.checkpoint_location}/live_matches") \
            .trigger(processingTime='30 seconds') \
            .start()
        
        return query
    
    def process_match_events(self):
        """Process match events stream"""
        logger.info("Starting match events stream...")
        
        # Read from Kafka
        kafka_df = self.read_kafka_stream('match-events')
        
        # Parse JSON
        events_df = kafka_df \
            .select(
                from_json(col('value').cast('string'), EVENT_SCHEMA).alias('data')
            ) \
            .select('data.*') \
            .withColumn('processing_time', current_timestamp())
        
        # Write to PostgreSQL
        jdbc_url = (
            f"jdbc:postgresql://{self.pg_config['host']}:"
            f"{self.pg_config['port']}/{self.pg_config['database']}"
        )
        
        query = events_df \
            .writeStream \
            .outputMode('append') \
            .format('jdbc') \
            .option('url', jdbc_url) \
            .option('dbtable', 'streaming.match_events') \
            .option('user', self.pg_config['user']) \
            .option('password', self.pg_config['password']) \
            .option('driver', 'org.postgresql.Driver') \
            .option('checkpointLocation', 
                   f"{self.checkpoint_location}/match_events") \
            .trigger(processingTime='10 seconds') \
            .start()
        
        return query
    
    def process_windowed_aggregations(self):
        """Process windowed aggregations for real-time analytics"""
        logger.info("Starting windowed aggregations...")
        
        # Read events
        kafka_df = self.read_kafka_stream('match-events')
        events_df = kafka_df \
            .select(
                from_json(col('value').cast('string'), EVENT_SCHEMA).alias('data')
            ) \
            .select('data.*')
        
        # 5-minute window aggregations by match
        windowed_stats = events_df \
            .withWatermark('timestamp', '10 minutes') \
            .groupBy(
                window('timestamp', '5 minutes'),
                'match_id',
                'team'
            ) \
            .agg(
                count('*').alias('total_events'),
                _sum(
                    col('event_type') == 'Goal'
                ).cast('int').alias('goals'),
                _sum(
                    col('event_type').isin(['Yellow Card', 'Red Card'])
                ).cast('int').alias('cards'),
                _sum(
                    col('event_type') == 'subst'
                ).cast('int').alias('substitutions')
            )
        
        # Write to Parquet (for historical analysis)
        query = windowed_stats \
            .writeStream \
            .outputMode('append') \
            .format('parquet') \
            .option('path', f"{self.output_path}/windowed_stats") \
            .option('checkpointLocation',
                   f"{self.checkpoint_location}/windowed_stats") \
            .trigger(processingTime='1 minute') \
            .start()
        
        return query
    
    def process_live_scoreboard(self):
        """Maintain live scoreboard with latest scores"""
        logger.info("Starting live scoreboard...")
        
        # Read matches
        kafka_df = self.read_kafka_stream('live-matches')
        matches_df = kafka_df \
            .select(
                from_json(col('value').cast('string'), MATCH_SCHEMA).alias('data')
            ) \
            .select('data.*')
        
        # Keep only latest record per match (complete mode with aggregation)
        latest_scores = matches_df \
            .withWatermark('timestamp', '5 minutes') \
            .groupBy('match_id') \
            .agg(
                _max('timestamp').alias('last_updated'),
                _max('home_score').alias('home_score'),
                _max('away_score').alias('away_score'),
                _max('minute').alias('minute'),
                _max('status').alias('status')
            )
        
        # Write to console for monitoring
        query = latest_scores \
            .writeStream \
            .outputMode('complete') \
            .format('console') \
            .option('truncate', 'false') \
            .option('numRows', 20) \
            .trigger(processingTime='30 seconds') \
            .start()
        
        return query
    
    def run(self):
        """Start all streaming queries"""
        try:
            self.create_spark_session()
            
            # Start multiple streaming queries
            queries = []
            
            # 1. Live matches to PostgreSQL
            queries.append(self.process_live_matches())
            
            # 2. Match events to PostgreSQL
            queries.append(self.process_match_events())
            
            # 3. Windowed aggregations to Parquet
            queries.append(self.process_windowed_aggregations())
            
            # 4. Live scoreboard to console
            queries.append(self.process_live_scoreboard())
            
            logger.info(f"Started {len(queries)} streaming queries")
            logger.info("Press Ctrl+C to stop...")
            
            # Wait for all queries to finish
            for query in queries:
                query.awaitTermination()
                
        except KeyboardInterrupt:
            logger.info("Stopping streaming queries...")
            for query in queries:
                query.stop()
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            raise
        finally:
            if self.spark:
                self.spark.stop()
            logger.info("Spark session stopped")


def main():
    """Entry point"""
    processor = LiveMatchStreamProcessor()
    processor.run()


if __name__ == '__main__':
    main()
