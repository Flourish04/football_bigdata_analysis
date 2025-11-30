"""
SILVER LAYER - Data Cleaning & Standardization
Reads from Bronze layer, applies cleaning, deduplication, and standardization
Outputs clean, validated data to Silver layer
"""

import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, trim, upper, lower, regexp_replace,
    current_timestamp, lit, coalesce, to_date, year
)
from pyspark.sql.types import IntegerType, DoubleType, StringType
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BRONZE_PATH = os.getenv('BRONZE_PATH', '/tmp/football_datalake/bronze')
SILVER_PATH = os.getenv('SILVER_PATH', '/tmp/football_datalake/silver')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SilverLayer:
    """Silver Layer - Data cleaning and standardization"""
    
    def __init__(self):
        """Initialize Silver Layer processor"""
        self.spark = self._create_spark_session()
        self.bronze_path = BRONZE_PATH
        self.silver_path = SILVER_PATH
        logger.info(f"[SUCCESS] Silver Layer initialized")
        logger.info(f"   Input: {self.bronze_path}")
        logger.info(f"   Output: {self.silver_path}")
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session for Silver layer"""
        spark = SparkSession.builder \
            .appName("Football Analytics - Silver Layer") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.executor.memory", "4g") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        logger.info("[SUCCESS] Spark session created for Silver layer")
        return spark
    
    def clean_player_profiles(self):
        """Clean and standardize player profiles based on actual schema"""
        logger.info("[CONFIG] Cleaning: player_profiles")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/player_profiles")
        
        # Cleaning transformations based on actual schema
        cleaned_df = df \
            .dropDuplicates(['player_id']) \
            .withColumn('player_name', 
                       coalesce(trim(col('player_name')), trim(col('player_slug')))) \
            .withColumn('player_slug', trim(col('player_slug'))) \
            .withColumn('date_of_birth', 
                       to_date(col('date_of_birth'), 'yyyy-MM-dd')) \
            .withColumn('place_of_birth', 
                       coalesce(trim(col('place_of_birth')), lit('Unknown'))) \
            .withColumn('country_of_birth', 
                       coalesce(trim(col('country_of_birth')), lit('Unknown'))) \
            .withColumn('height', 
                       when((col('height') == 0) | (col('height').isNull()), lit(None).cast(IntegerType()))
                       .when(col('height') < 10, (col('height') * 100).cast(IntegerType()))  # Convert meters to cm
                       .otherwise(col('height').cast(IntegerType()))) \
            .withColumn('citizenship_country', 
                       coalesce(trim(col('citizenship')), lit('Unknown'))) \
            .withColumn('position', 
                       coalesce(trim(col('position')), lit('Unknown'))) \
            .withColumn('foot', 
                       coalesce(upper(trim(col('foot'))), lit('UNKNOWN'))) \
            .withColumn('current_club_id', trim(col('current_club_id'))) \
            .withColumn('joined', to_date(col('joined'), 'yyyy-MM-dd')) \
            .withColumn('contract_expires', to_date(col('contract_expires'), 'yyyy-MM-dd')) \
            .withColumn('player_main_position', trim(col('main_position'))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'player_id',
                'player_slug',
                'player_name',
                'player_image_url',
                'date_of_birth',
                'place_of_birth',
                'country_of_birth',
                'height',
                'citizenship',
                'citizenship_country',
                'position',
                'foot',
                'current_club_id',
                'joined',
                'contract_expires',
                'social_media_url',
                'player_main_position',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        # Remove invalid records
        cleaned_df = cleaned_df.filter(col('player_id').isNotNull())
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: player_profiles → {count:,} records")
        
        # Write to Silver layer
        output_path = f"{self.silver_path}/player_profiles"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_player_performances(self):
        """Clean and standardize player performances based on actual schema"""
        logger.info("[CONFIG] Cleaning: player_performances")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/player_performances")
        
        cleaned_df = df \
            .withColumn('season_name', trim(col('season_name'))) \
            .withColumn('competition_id', trim(col('competition_id'))) \
            .withColumn('competition_name', trim(col('competition_name'))) \
            .withColumn('team_id', trim(col('team_id'))) \
            .withColumn('team_name', trim(col('team_name'))) \
            .withColumn('nb_in_group', 
                       coalesce(col('nb_in_group').cast(IntegerType()), lit(0))) \
            .withColumn('nb_on_pitch', 
                       coalesce(col('nb_on_pitch').cast(IntegerType()), lit(0))) \
            .withColumn('goals', 
                       coalesce(col('goals').cast(IntegerType()), lit(0))) \
            .withColumn('own_goals', 
                       coalesce(col('own_goals').cast(IntegerType()), lit(0))) \
            .withColumn('assists', 
                       coalesce(col('assists').cast(IntegerType()), lit(0))) \
            .withColumn('subed_in', 
                       coalesce(col('subed_in').cast(IntegerType()), lit(0))) \
            .withColumn('subed_out', 
                       coalesce(col('subed_out').cast(IntegerType()), lit(0))) \
            .withColumn('yellow_cards', 
                       coalesce(col('yellow_cards').cast(IntegerType()), lit(0))) \
            .withColumn('second_yellow_cards', 
                       coalesce(col('second_yellow_cards').cast(IntegerType()), lit(0))) \
            .withColumn('direct_red_cards', 
                       coalesce(col('direct_red_cards').cast(IntegerType()), lit(0))) \
            .withColumn('penalty_goals', 
                       coalesce(col('penalty_goals').cast(IntegerType()), lit(0))) \
            .withColumn('minutes_played', 
                       coalesce(col('minutes_played').cast(IntegerType()), lit(0))) \
            .withColumn('goals_conceded', 
                       coalesce(col('goals_conceded').cast(IntegerType()), lit(0))) \
            .withColumn('clean_sheets', 
                       coalesce(col('clean_sheets').cast(IntegerType()), lit(0))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'player_id',
                'season_name',
                'competition_id',
                'competition_name',
                'team_id',
                'team_name',
                'nb_in_group',
                'nb_on_pitch',
                'goals',
                'own_goals',
                'assists',
                'subed_in',
                'subed_out',
                'yellow_cards',
                'second_yellow_cards',
                'direct_red_cards',
                'penalty_goals',
                'minutes_played',
                'goals_conceded',
                'clean_sheets',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        # Filter invalid records
        cleaned_df = cleaned_df.filter(
            col('player_id').isNotNull() & 
            col('season_name').isNotNull()
        )
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: player_performances → {count:,} records")
        
        output_path = f"{self.silver_path}/player_performances"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_player_market_values(self):
        """Clean and standardize market values based on actual schema"""
        logger.info("[CONFIG] Cleaning: player_market_value")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/player_market_value")
        
        cleaned_df = df \
            .withColumn('value', 
                       coalesce(col('value').cast(IntegerType()), lit(0))) \
            .withColumn('date_unix', col('date_unix')) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'player_id',
                'date_unix',  # This is the PK in the schema
                'value',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        # Remove duplicates and nulls
        cleaned_df = cleaned_df \
            .filter(col('player_id').isNotNull()) \
            .dropDuplicates(['player_id', 'date_unix'])
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: player_market_value → {count:,} records")
        
        output_path = f"{self.silver_path}/player_market_value"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_player_injuries(self):
        """Clean and standardize injury records based on actual schema"""
        logger.info("[CONFIG] Cleaning: player_injuries")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/player_injuries")
        
        cleaned_df = df \
            .withColumn('season_name', trim(col('season_name'))) \
            .withColumn('injury_reason', trim(col('injury_reason'))) \
            .withColumn('from_date', to_date(col('from_date'), 'yyyy-MM-dd')) \
            .withColumn('end_date', to_date(col('end_date'), 'yyyy-MM-dd')) \
            .withColumn('days_missed', 
                       coalesce(col('days_missed').cast(IntegerType()), lit(0))) \
            .withColumn('games_missed', 
                       coalesce(col('games_missed').cast(IntegerType()), lit(0))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'player_id',
                'season_name',
                'injury_reason',
                'from_date',  # PK
                'end_date',
                'days_missed',
                'games_missed',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        cleaned_df = cleaned_df.filter(col('player_id').isNotNull())
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: player_injuries → {count:,} records")
        
        output_path = f"{self.silver_path}/player_injuries"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_transfer_history(self):
        """Clean and standardize transfer history based on actual schema"""
        logger.info("[CONFIG] Cleaning: transfer_history")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/transfer_history")
        
        cleaned_df = df \
            .withColumn('season', trim(col('season_name'))) \
            .withColumn('date', to_date(col('transfer_date'), 'yyyy-MM-dd')) \
            .withColumn('from_team_id', trim(col('from_team_id'))) \
            .withColumn('from_team_name', trim(col('from_team_name'))) \
            .withColumn('to_team_id', trim(col('to_team_id'))) \
            .withColumn('to_team_name', trim(col('to_team_name'))) \
            .withColumn('value_at_transfer', 
                       coalesce(col('value_at_transfer').cast(IntegerType()), lit(0))) \
            .withColumn('transfer_fee', trim(col('transfer_fee'))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'player_id',
                'season',
                'date',
                'from_team_id',
                'from_team_name',
                'to_team_id',
                'to_team_name',
                'value_at_transfer',
                'transfer_fee',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        cleaned_df = cleaned_df.filter(col('player_id').isNotNull())
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: transfer_history → {count:,} records")
        
        output_path = f"{self.silver_path}/transfer_history"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_team_details(self):
        """Clean and standardize team details based on actual schema"""
        logger.info("[CONFIG] Cleaning: team_details")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/team_details")
        
        cleaned_df = df \
            .dropDuplicates(['club_id']) \
            .withColumn('club_id', trim(col('club_id'))) \
            .withColumn('club_slug', trim(col('club_slug'))) \
            .withColumn('club_name', trim(col('club_name'))) \
            .withColumn('country_name', trim(col('country_name'))) \
            .withColumn('season_id', trim(col('season_id'))) \
            .withColumn('competition_id', trim(col('competition_id'))) \
            .withColumn('competition_slug', trim(col('competition_slug'))) \
            .withColumn('competition_name', trim(col('competition_name'))) \
            .withColumn('club_division', trim(col('club_division'))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'club_id',  # PK
                'club_slug',
                'club_name',
                'logo_url',
                'country_name',
                'season_id',
                'competition_id',
                'competition_slug',
                'competition_name',
                'club_division',
                'source_url',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        cleaned_df = cleaned_df.filter(col('club_id').isNotNull())
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: team_details → {count:,} records")
        
        output_path = f"{self.silver_path}/team_details"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_player_national_performances(self):
        """Clean and standardize national team performances"""
        logger.info("[CONFIG] Cleaning: player_national_performances")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/player_national_performances")
        
        cleaned_df = df \
            .withColumn('team_id', trim(col('team_id'))) \
            .withColumn('first_game_date', to_date(col('debut'), 'yyyy-MM-dd')) \
            .withColumn('matches', 
                       coalesce(col('matches').cast(IntegerType()), lit(0))) \
            .withColumn('goals', 
                       coalesce(col('goals').cast(IntegerType()), lit(0))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'player_id',
                'team_id',
                'first_game_date',  # PK
                'matches',
                'goals',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        cleaned_df = cleaned_df.filter(col('player_id').isNotNull())
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: player_national_performances → {count:,} records")
        
        output_path = f"{self.silver_path}/player_national_performances"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_player_teammates(self):
        """Clean and standardize player teammates data"""
        logger.info("[CONFIG] Cleaning: player_teammates_played_with")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/player_teammates_played_with")
        
        cleaned_df = df \
            .withColumn('teammate_player_id', trim(col('teammate_player_id'))) \
            .withColumn('player_with_name', trim(col('teammate_player_name'))) \
            .withColumn('ppg_played_with', 
                       coalesce(col('ppg_played_with').cast(DoubleType()), lit(0.0))) \
            .withColumn('joint_goal_participation', 
                       coalesce(col('joint_goal_participation').cast(IntegerType()), lit(0))) \
            .withColumn('minutes_played_with', 
                       coalesce(col('minutes_played_with').cast(IntegerType()), lit(0))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'player_id',
                'teammate_player_id',
                'player_with_name',
                'ppg_played_with',
                'joint_goal_participation',
                'minutes_played_with',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        cleaned_df = cleaned_df.filter(
            col('player_id').isNotNull() & col('teammate_player_id').isNotNull()
        )
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: player_teammates_played_with → {count:,} records")
        
        output_path = f"{self.silver_path}/player_teammates_played_with"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_team_competitions_seasons(self):
        """Clean and standardize team competitions seasons"""
        logger.info("[CONFIG] Cleaning: team_competitions_seasons")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/team_competitions_seasons")
        
        cleaned_df = df \
            .withColumn('club_id', trim(col('club_id'))) \
            .withColumn('competition_id', trim(col('competition_id'))) \
            .withColumn('competition_name', trim(col('competition_name'))) \
            .withColumn('team_name', trim(col('team_name'))) \
            .withColumn('season_season', trim(col('season_season'))) \
            .withColumn('season_rank', 
                       coalesce(col('season_rank').cast(IntegerType()), lit(0))) \
            .withColumn('season_draws', 
                       coalesce(col('season_draws').cast(IntegerType()), lit(0))) \
            .withColumn('season_wins', 
                       coalesce(col('season_wins').cast(IntegerType()), lit(0))) \
            .withColumn('season_losses', 
                       coalesce(col('season_losses').cast(IntegerType()), lit(0))) \
            .withColumn('season_points', 
                       coalesce(col('season_points').cast(IntegerType()), lit(0))) \
            .withColumn('season_goals_for', 
                       coalesce(col('season_goals_for').cast(IntegerType()), lit(0))) \
            .withColumn('season_goals_against', 
                       coalesce(col('season_goals_against').cast(IntegerType()), lit(0))) \
            .withColumn('season_goal_difference', 
                       coalesce(col('season_goal_difference').cast(IntegerType()), lit(0))) \
            .withColumn('silver_processed_timestamp', current_timestamp())
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: team_competitions_seasons → {count:,} records")
        
        output_path = f"{self.silver_path}/team_competitions_seasons"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def clean_team_children(self):
        """Clean and standardize team children (parent/child relationships)"""
        logger.info("[CONFIG] Cleaning: team_children")
        
        df = self.spark.read.parquet(f"{self.bronze_path}/team_children")
        
        cleaned_df = df \
            .withColumn('parent_team_id', trim(col('parent_team_id'))) \
            .withColumn('parent_team_name', trim(col('parent_team_name'))) \
            .withColumn('child_team_id', trim(col('child_team_id'))) \
            .withColumn('child_team_name', trim(col('child_team_name'))) \
            .withColumn('silver_processed_timestamp', current_timestamp()) \
            .select(
                'parent_team_id',
                'parent_team_name',
                'child_team_id',
                'child_team_name',
                'bronze_ingestion_timestamp',
                'silver_processed_timestamp'
            )
        
        cleaned_df = cleaned_df.filter(
            col('parent_team_id').isNotNull() & col('child_team_id').isNotNull()
        )
        
        count = cleaned_df.count()
        logger.info(f"[SUCCESS] Silver: team_children → {count:,} records")
        
        output_path = f"{self.silver_path}/team_children"
        cleaned_df.write.mode("overwrite").parquet(output_path)
        
        return cleaned_df
    
    def process_all_tables(self):
        """Process all tables from Bronze to Silver"""
        logger.info("=" * 80)
        logger.info("[SILVER] SILVER LAYER - Starting data cleaning")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        results = {}
        
        # Process each table
        processors = {
            # Player tables
            'player_profiles': self.clean_player_profiles,
            'player_performances': self.clean_player_performances,
            'player_market_value': self.clean_player_market_values,
            'player_injuries': self.clean_player_injuries,
            'player_national_performances': self.clean_player_national_performances,
            'player_teammates_played_with': self.clean_player_teammates,
            # Transfer
            'transfer_history': self.clean_transfer_history,
            # Team tables
            'team_details': self.clean_team_details,
            'team_competitions_seasons': self.clean_team_competitions_seasons,
            'team_children': self.clean_team_children,
        }
        
        for table_name, processor_func in processors.items():
            try:
                df = processor_func()
                results[table_name] = {'status': 'SUCCESS', 'records': df.count()}
            except Exception as e:
                results[table_name] = {'status': 'FAILED', 'error': str(e)}
                logger.error(f"[ERROR] Failed to process {table_name}: {str(e)}")
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("[SILVER] SILVER LAYER - Processing Summary")
        logger.info("=" * 80)
        
        success_count = sum(1 for r in results.values() if r['status'] == 'SUCCESS')
        total_records = sum(r.get('records', 0) for r in results.values() if r['status'] == 'SUCCESS')
        
        logger.info(f"[SUCCESS] Successful: {success_count}/{len(processors)}")
        logger.info(f"[DATA] Total records: {total_records:,}")
        logger.info(f"[TIME]  Duration: {duration:.2f} seconds")
        logger.info(f"[FOLDER] Output location: {self.silver_path}")
        logger.info("=" * 80)
        
        return results
    
    def stop(self):
        """Stop Spark session"""
        if self.spark:
            self.spark.stop()
            logger.info("[STOP] Silver Layer - Spark session stopped")


def main():
    """Main entry point for Silver layer"""
    logger.info("\n" + "=" * 80)
    logger.info("[FOOTBALL] FOOTBALL ANALYTICS - SILVER LAYER")
    logger.info("=" * 80)
    
    silver = SilverLayer()
    
    try:
        # Process all tables
        results = silver.process_all_tables()
        
        logger.info("\n[SUCCESS] Silver layer processing completed successfully!")
        
    except Exception as e:
        logger.error(f"\n[ERROR] Silver layer processing failed: {str(e)}")
        raise
    finally:
        silver.stop()


if __name__ == '__main__':
    main()
