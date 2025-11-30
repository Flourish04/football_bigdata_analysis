"""
GOLD LAYER - Business Logic & Analytics
Reads from Silver layer, applies aggregations, calculations, and business logic
Creates analytics-ready datasets for consumption
"""

import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, avg, sum as spark_sum, count, max as spark_max, min as spark_min, least, round as spark_round,
    lag, lead, row_number, dense_rank, percent_rank,
    current_timestamp, lit, datediff, current_date, year, months_between
)
from pyspark.sql.types import DoubleType
from pyspark.sql.window import Window
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SILVER_PATH = os.getenv('SILVER_PATH', '/tmp/football_datalake/silver')
GOLD_PATH = os.getenv('GOLD_PATH', '/tmp/football_datalake/gold')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'football_analytics')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'football_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'football_pass')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoldLayer:
    """Gold Layer - Business analytics and aggregations"""
    
    def __init__(self):
        """Initialize Gold Layer processor"""
        self.spark = self._create_spark_session()
        self.silver_path = SILVER_PATH
        self.gold_path = GOLD_PATH
        self.postgres_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        logger.info(f"[SUCCESS] Gold Layer initialized")
        logger.info(f"   Input: {self.silver_path}")
        logger.info(f"   Output: {self.gold_path}")
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session for Gold layer"""
        spark = SparkSession.builder \
            .appName("Football Analytics - Gold Layer") \
            .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.executor.memory", "4g") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        logger.info("[SUCCESS] Spark session created for Gold layer")
        return spark
    
    def calculate_player_form_metrics(self):
        """Calculate player form and performance metrics"""
        logger.info("[DATA] Calculating: player_form_metrics")
        
        performances = self.spark.read.parquet(f"{self.silver_path}/player_performances")
        
        # Aggregate by player (using actual column names from Silver)
        form_metrics = performances \
            .groupBy('player_id') \
            .agg(
                count('*').alias('total_seasons'),
                spark_sum('nb_on_pitch').alias('total_appearances'),  # Changed from 'appearances'
                spark_sum('goals').alias('total_goals'),
                spark_sum('assists').alias('total_assists'),
                spark_sum('yellow_cards').alias('total_yellow_cards'),
                # Calculate total red cards from second_yellow + direct_red
                (spark_sum('second_yellow_cards') + spark_sum('direct_red_cards')).alias('total_red_cards'),
                spark_sum('minutes_played').alias('total_minutes_played'),
                avg('goals').alias('avg_goals_per_season'),
                avg('assists').alias('avg_assists_per_season'),
                spark_max('goals').alias('best_goals_season'),
                spark_max('assists').alias('best_assists_season')
            ) \
            .withColumn('goals_per_90min', 
                       spark_round(when(col('total_minutes_played') >= 90,
                            least(col('total_goals') / (col('total_minutes_played') / 90), lit(3.0)))
                       .otherwise(lit(None)), 4)) \
            .withColumn('assists_per_90min', 
                       spark_round(when(col('total_minutes_played') >= 90,
                            least(col('total_assists') / (col('total_minutes_played') / 90), lit(3.0)))
                       .otherwise(lit(None)), 4)) \
            .withColumn('goal_contributions', 
                       col('total_goals') + col('total_assists')) \
            .withColumn('avg_goals_per_season', spark_round(col('avg_goals_per_season'), 2)) \
            .withColumn('avg_assists_per_season', spark_round(col('avg_assists_per_season'), 2)) \
            .withColumn('gold_processed_timestamp', current_timestamp())
        
        record_count = form_metrics.count()
        logger.info(f"[SUCCESS] Gold: player_form_metrics → {record_count:,} records")
        
        # Write to Gold layer
        output_path = f"{self.gold_path}/player_form_metrics"
        form_metrics.write.mode("overwrite").parquet(output_path)
        
        return form_metrics
    
    def calculate_market_value_trends(self):
        """Calculate market value trends and changes"""
        logger.info("[DATA] Calculating: market_value_trends")
        
        market_values = self.spark.read.parquet(f"{self.silver_path}/player_market_value")
        
        # Window for time-based calculations (using date_unix as order)
        window_spec = Window.partitionBy('player_id').orderBy('date_unix')
        
        trends = market_values \
            .withColumn('prev_value', lag('value').over(window_spec)) \
            .withColumn('next_value', lead('value').over(window_spec)) \
            .withColumn('value_change', col('value') - col('prev_value')) \
            .withColumn('value_change_pct', 
                       when(col('prev_value') > 0, 
                            (col('value_change') / col('prev_value')) * 100)
                       .otherwise(0)) \
            .withColumn('trend_direction', 
                       when(col('value_change') > 0, 'INCREASING')
                       .when(col('value_change') < 0, 'DECREASING')
                       .otherwise('STABLE'))
        
        # Get latest market value for each player
        window_latest = Window.partitionBy('player_id').orderBy(col('date_unix').desc())
        latest_values = trends \
            .withColumn('rank', row_number().over(window_latest)) \
            .filter(col('rank') == 1) \
            .select('player_id', 
                   col('value').alias('latest_market_value'),
                   col('date_unix').alias('latest_valuation_timestamp'))
        
        # Aggregate by player for summary stats
        player_market_summary = trends \
            .groupBy('player_id') \
            .agg(
                spark_max('value').alias('peak_market_value'),
                spark_min('value').alias('lowest_market_value'),
                avg('value').alias('avg_market_value'),
                count('*').alias('value_records_count')
            ) \
            .join(latest_values, 'player_id', 'left') \
            .withColumn('value_volatility', 
                       col('peak_market_value') - col('lowest_market_value')) \
            .withColumn('peak_market_value', col('peak_market_value').cast('long')) \
            .withColumn('latest_market_value', col('latest_market_value').cast('long')) \
            .withColumn('lowest_market_value', col('lowest_market_value').cast('long')) \
            .withColumn('avg_market_value', col('avg_market_value').cast('long')) \
            .withColumn('value_volatility', col('value_volatility').cast('long')) \
            .withColumn('gold_processed_timestamp', current_timestamp())
        
        record_count = player_market_summary.count()
        logger.info(f"[SUCCESS] Gold: market_value_trends → {record_count:,} records")
        
        output_path = f"{self.gold_path}/market_value_trends"
        player_market_summary.write.mode("overwrite").parquet(output_path)
        
        return player_market_summary
    
    def calculate_injury_risk_scores(self):
        """Calculate injury risk and history metrics"""
        logger.info("[DATA] Calculating: injury_risk_scores")
        
        injuries = self.spark.read.parquet(f"{self.silver_path}/player_injuries")
        
        risk_scores = injuries \
            .groupBy('player_id') \
            .agg(
                count('*').alias('total_injuries'),
                spark_sum('days_missed').alias('total_days_missed'),
                spark_sum('games_missed').alias('total_games_missed'),
                avg('days_missed').alias('avg_days_per_injury'),
                avg('games_missed').alias('avg_games_per_injury'),
                spark_max('days_missed').alias('longest_injury_days'),
                spark_max('games_missed').alias('longest_injury_games')
            ) \
            .withColumn('injury_severity_score',
                       spark_round((col('total_injuries') * 5 + col('total_days_missed') / 10) / 100, 2)) \
            .withColumn('avg_days_per_injury', spark_round(col('avg_days_per_injury'), 2)) \
            .withColumn('avg_games_per_injury', spark_round(col('avg_games_per_injury'), 2)) \
            .withColumn('injury_risk_level',
                       when(col('injury_severity_score') > 5, 'HIGH')
                       .when(col('injury_severity_score') > 2, 'MEDIUM')
                       .otherwise('LOW')) \
            .withColumn('gold_processed_timestamp', current_timestamp())
        
        record_count = risk_scores.count()
        logger.info(f"[SUCCESS] Gold: injury_risk_scores → {record_count:,} records")
        
        output_path = f"{self.gold_path}/injury_risk_scores"
        risk_scores.write.mode("overwrite").parquet(output_path)
        
        return risk_scores
    
    def calculate_transfer_intelligence(self):
        """Calculate transfer market intelligence"""
        logger.info("[DATA] Calculating: transfer_intelligence")
        
        transfers = self.spark.read.parquet(f"{self.silver_path}/transfer_history")
        
        # Cast transfer_fee to numeric if it's string
        transfers = transfers.withColumn('transfer_fee_numeric', 
                                        col('transfer_fee').cast(DoubleType()))
        
        transfer_stats = transfers \
            .groupBy('player_id') \
            .agg(
                count('*').alias('total_transfers'),
                spark_sum('transfer_fee_numeric').alias('total_transfer_fees'),
                avg('transfer_fee_numeric').alias('avg_transfer_fee'),
                spark_max('transfer_fee_numeric').alias('highest_transfer_fee'),
                avg('value_at_transfer').alias('avg_value_at_transfer'),  # Changed from 'market_value'
                spark_max('date').alias('last_transfer_date')  # Changed from 'transfer_date'
            ) \
            .withColumn('total_transfer_fees', col('total_transfer_fees').cast('long')) \
            .withColumn('avg_transfer_fee', col('avg_transfer_fee').cast('long')) \
            .withColumn('highest_transfer_fee', col('highest_transfer_fee').cast('long')) \
            .withColumn('avg_value_at_transfer', col('avg_value_at_transfer').cast('long')) \
            .withColumn('transfer_frequency',
                       spark_round(col('total_transfers') / 10, 2)) \
            .withColumn('transfer_value_trend',
                       when(col('total_transfer_fees') > col('avg_value_at_transfer'), 'PROFIT')
                       .otherwise('LOSS')) \
            .withColumn('gold_processed_timestamp', current_timestamp())
        
        record_count = transfer_stats.count()
        logger.info(f"[SUCCESS] Gold: transfer_intelligence → {record_count:,} records")
        
        output_path = f"{self.gold_path}/transfer_intelligence"
        transfer_stats.write.mode("overwrite").parquet(output_path)
        
        return transfer_stats
    
    def create_player_analytics_360(self):
        """Create comprehensive 360-degree player analytics"""
        logger.info("[DATA] Creating: player_analytics_360")
        
        # Load all necessary data
        profiles = self.spark.read.parquet(f"{self.silver_path}/player_profiles")
        form_metrics = self.spark.read.parquet(f"{self.gold_path}/player_form_metrics")
        market_trends = self.spark.read.parquet(f"{self.gold_path}/market_value_trends")
        injury_risks = self.spark.read.parquet(f"{self.gold_path}/injury_risk_scores")
        transfer_intel = self.spark.read.parquet(f"{self.gold_path}/transfer_intelligence")
        
        # Join all datasets
        analytics_360 = profiles \
            .join(form_metrics, 'player_id', 'left') \
            .join(market_trends, 'player_id', 'left') \
            .join(injury_risks, 'player_id', 'left') \
            .join(transfer_intel, 'player_id', 'left')
        
        # Calculate age
        analytics_360 = analytics_360 \
            .withColumn('age', 
                       year(current_date()) - year(col('date_of_birth')))
        
        # Calculate overall player score (0-100)
        # Normalize performance to 0-100 (cap at 2.0 goals/90 = 100 points)
        analytics_360 = analytics_360 \
            .withColumn('performance_score',
                       spark_round(when(col('goals_per_90min').isNotNull(),
                            when(col('goals_per_90min') + col('assists_per_90min') > 2.0, lit(100.0))
                            .otherwise((col('goals_per_90min') + col('assists_per_90min')) * 50.0))
                       .otherwise(0), 2)) \
            .withColumn('market_score',
                       spark_round(when(col('peak_market_value').isNotNull(),
                            when(col('peak_market_value') > 100000000, lit(100.0))  # Cap at 100M = 100 points
                            .otherwise(col('peak_market_value') / 1000000.0))
                       .otherwise(0), 2)) \
            .withColumn('health_score',
                       spark_round(when(col('injury_severity_score').isNotNull(),
                            when(col('injury_severity_score') >= 10.0, lit(0.0))  # Very injury prone
                            .otherwise(100.0 - col('injury_severity_score') * 10.0))
                       .otherwise(100.0), 2)) \
            .withColumn('overall_player_score',
                       spark_round((col('performance_score') * 0.4 + 
                        col('market_score') * 0.3 + 
                        col('health_score') * 0.3), 2))
        
        # Add ranking
        window_rank = Window.orderBy(col('overall_player_score').desc())
        analytics_360 = analytics_360 \
            .withColumn('player_rank', row_number().over(window_rank)) \
            .withColumn('player_rank_percentile', percent_rank().over(window_rank))
        
        # Filter out records with missing required fields
        analytics_360 = analytics_360.filter(
            col('player_name').isNotNull() & 
            col('player_id').isNotNull()
        )
        
        # Select final columns (using actual column names from Silver)
        final_analytics = analytics_360.select(
            'player_id',
            'player_name',
            'date_of_birth',
            'age',
            col('position').alias('player_main_position'),
            'citizenship',
            col('current_club_id').cast('long').alias('current_club_id'),  # Cast to bigint for PostgreSQL
            col('height').cast('int').alias('height'),  # Remove decimals from height
            'foot',
            # Performance
            'total_appearances',
            'total_goals',
            'total_assists',
            spark_round(col('goals_per_90min'), 4).alias('goals_per_90min'),  # 4 decimals for rates
            spark_round(col('assists_per_90min'), 4).alias('assists_per_90min'),
            'goal_contributions',
            spark_round(col('avg_goals_per_season'), 2).alias('avg_goals_per_season'),  # 2 decimals for averages
            spark_round(col('avg_assists_per_season'), 2).alias('avg_assists_per_season'),
            # Market Value - No decimals for money
            col('peak_market_value').cast('long').alias('peak_market_value'),
            col('latest_market_value').cast('long').alias('latest_market_value'),
            col('avg_market_value').cast('long').alias('avg_market_value'),
            col('value_volatility').cast('long').alias('value_volatility'),
            'latest_valuation_timestamp',  # Changed from 'latest_valuation_date'
            # Injury Risk
            'total_injuries',
            col('total_days_missed').cast('int').alias('total_days_missed'),
            spark_round(col('injury_severity_score'), 2).alias('injury_severity_score'),
            'injury_risk_level',
            # Transfer - No decimals for money
            'total_transfers',
            col('total_transfer_fees').cast('long').alias('total_transfer_fees'),
            col('avg_transfer_fee').cast('long').alias('avg_transfer_fee'),
            'last_transfer_date',
            # Scores - Already rounded to 2 decimals above
            'performance_score',
            'market_score',
            'health_score',
            'overall_player_score',
            'player_rank',
            spark_round(col('player_rank_percentile'), 2).alias('player_rank_percentile')
        ) \
        .withColumn('gold_processed_timestamp', current_timestamp())
        
        record_count = final_analytics.count()
        logger.info(f"[SUCCESS] Gold: player_analytics_360 → {record_count:,} records")
        
        output_path = f"{self.gold_path}/player_analytics_360"
        final_analytics.write.mode("overwrite").parquet(output_path)
        
        return final_analytics
    
    def write_to_postgres(self, df, table_name: str):
        """Write Gold layer data to PostgreSQL for consumption"""
        logger.info(f"[SAVE] Writing to PostgreSQL: {table_name}")
        
        try:
            df.write \
                .format("jdbc") \
                .option("url", self.postgres_url) \
                .option("dbtable", f"analytics.{table_name}") \
                .option("user", POSTGRES_USER) \
                .option("password", POSTGRES_PASSWORD) \
                .option("driver", "org.postgresql.Driver") \
                .mode("overwrite") \
                .save()
            
            logger.info(f"[SUCCESS] PostgreSQL: {table_name} written successfully")
        except Exception as e:
            logger.error(f"[ERROR] Error writing to PostgreSQL: {str(e)}")
    
    def process_all_analytics(self, write_to_db: bool = False):
        """Process all Gold layer analytics"""
        logger.info("=" * 80)
        logger.info("[GOLD] GOLD LAYER - Starting analytics processing")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # Process in order (some depend on others)
        try:
            # Step 1: Calculate base metrics
            form_metrics = self.calculate_player_form_metrics()
            market_trends = self.calculate_market_value_trends()
            injury_risks = self.calculate_injury_risk_scores()
            transfer_intel = self.calculate_transfer_intelligence()
            
            # Step 2: Create comprehensive analytics
            analytics_360 = self.create_player_analytics_360()
            
            # Step 3: Write to PostgreSQL (optional)
            if write_to_db:
                logger.info("\n[SAVE] Writing to PostgreSQL...")
                self.write_to_postgres(form_metrics, 'player_form_metrics')
                self.write_to_postgres(market_trends, 'market_value_trends')
                self.write_to_postgres(injury_risks, 'injury_risk_scores')
                self.write_to_postgres(transfer_intel, 'transfer_intelligence')
                self.write_to_postgres(analytics_360, 'player_analytics_360')
            
            # Show top 10 players
            logger.info("\n[TROPHY] TOP 10 PLAYERS BY OVERALL SCORE:")
            analytics_360.select(
                'player_rank',
                'player_name',
                'player_main_position',
                'current_club_id',  # Changed from 'current_club'
                'overall_player_score',
                'total_goals',
                'peak_market_value'
            ).show(10, truncate=False)
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing analytics: {str(e)}")
            raise
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("[GOLD] GOLD LAYER - Processing Summary")
        logger.info("=" * 80)
        logger.info(f"[SUCCESS] All analytics processed successfully")
        logger.info(f"[TIME]  Duration: {duration:.2f} seconds")
        logger.info(f"[FOLDER] Output location: {self.gold_path}")
        if write_to_db:
            logger.info(f"[SAVE] PostgreSQL: Data written to analytics schema")
        logger.info("=" * 80)
    
    def stop(self):
        """Stop Spark session"""
        if self.spark:
            self.spark.stop()
            logger.info("[STOP] Gold Layer - Spark session stopped")


def main():
    """Main entry point for Gold layer"""
    logger.info("\n" + "=" * 80)
    logger.info("[FOOTBALL] FOOTBALL ANALYTICS - GOLD LAYER")
    logger.info("=" * 80)
    
    gold = GoldLayer()
    
    try:
        # Process all analytics
        # Set write_to_db=True to write to PostgreSQL
        gold.process_all_analytics(write_to_db=False)
        
        logger.info("\n[SUCCESS] Gold layer processing completed successfully!")
        logger.info("[INFO] To write to PostgreSQL, set write_to_db=True")
        
    except Exception as e:
        logger.error(f"\n[ERROR] Gold layer processing failed: {str(e)}")
        raise
    finally:
        gold.stop()


if __name__ == '__main__':
    main()
