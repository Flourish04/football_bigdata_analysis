"""
BRONZE LAYER - Raw Data Ingestion
Loads raw data from CSV files and stores in Bronze layer (Parquet format)
No transformations, only data type inference and basic validation
"""

import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATA_PATH = os.getenv('DATA_PATH', '/home/hung/Downloads/bigdata/football_project/football-datasets/datalake/transfermarkt')
BRONZE_PATH = os.getenv('BRONZE_PATH', '/tmp/football_datalake/bronze')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BronzeLayer:
    """Bronze Layer - Raw data ingestion from source files"""
    
    def __init__(self):
        """Initialize Bronze Layer processor"""
        self.spark = self._create_spark_session()
        self.data_path = DATA_PATH
        self.bronze_path = BRONZE_PATH
        logger.info(f"✅ Bronze Layer initialized")
        logger.info(f"   Source: {self.data_path}")
        logger.info(f"   Output: {self.bronze_path}")
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session for Bronze layer"""
        spark = SparkSession.builder \
            .appName("Football Analytics - Bronze Layer") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.executor.memory", "4g") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        logger.info("✅ Spark session created for Bronze layer")
        return spark
    
    def ingest_csv_to_bronze(self, csv_folder: str, table_name: str):
        """
        Ingest CSV files to Bronze layer (Parquet format)
        
        Args:
            csv_folder: Folder name under DATA_PATH (e.g., 'player_profiles')
            table_name: Output table name (e.g., 'player_profiles')
        """
        csv_path = f"{self.data_path}/{csv_folder}/{table_name}.csv"
        bronze_output = f"{self.bronze_path}/{table_name}"
        
        logger.info(f"📥 Ingesting: {csv_folder}/{table_name}.csv")
        
        try:
            # Read CSV with schema inference
            df = self.spark.read.csv(
                csv_path,
                header=True,
                inferSchema=True,
                multiLine=True,  # Handle multi-line fields
                escape='"'
            )
            
            # Add metadata columns
            df_with_metadata = df \
                .withColumn('bronze_ingestion_timestamp', current_timestamp()) \
                .withColumn('bronze_source_file', lit(csv_path))
            
            record_count = df_with_metadata.count()
            
            # Write to Bronze layer (Parquet)
            df_with_metadata.write \
                .mode("overwrite") \
                .parquet(bronze_output)
            
            logger.info(f"✅ Bronze: {table_name} → {record_count:,} records")
            
            return df_with_metadata
            
        except Exception as e:
            logger.error(f"❌ Error ingesting {table_name}: {str(e)}")
            raise
    
    def ingest_all_tables(self):
        """Ingest all source tables to Bronze layer"""
        logger.info("=" * 80)
        logger.info("🥉 BRONZE LAYER - Starting data ingestion")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # Define all tables to ingest (folder_name, table_name)
        tables = [
            # Player tables (7 categories)
            ('player_profiles', 'player_profiles'),
            ('player_performances', 'player_performances'),
            ('player_market_value', 'player_market_value'),
            ('player_latest_market_value', 'player_latest_market_value'),
            ('player_injuries', 'player_injuries'),
            ('player_national_performances', 'player_national_performances'),
            ('player_teammates_played_with', 'player_teammates_played_with'),
            # Team tables (3 categories)
            ('team_details', 'team_details'),
            ('team_competitions_seasons', 'team_competitions_seasons'),
            ('team_children', 'team_children'),
            # Transfer history
            ('transfer_history', 'transfer_history'),
        ]
        
        results = {}
        total_records = 0
        
        for folder, table in tables:
            try:
                df = self.ingest_csv_to_bronze(folder, table)
                count = df.count()
                results[table] = {'status': 'SUCCESS', 'records': count}
                total_records += count
            except Exception as e:
                results[table] = {'status': 'FAILED', 'error': str(e)}
                logger.error(f"❌ Failed to ingest {table}: {str(e)}")
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("🥉 BRONZE LAYER - Ingestion Summary")
        logger.info("=" * 80)
        
        success_count = sum(1 for r in results.values() if r['status'] == 'SUCCESS')
        failed_count = len(results) - success_count
        
        logger.info(f"✅ Successful: {success_count}/{len(tables)}")
        logger.info(f"❌ Failed: {failed_count}/{len(tables)}")
        logger.info(f"📊 Total records: {total_records:,}")
        logger.info(f"⏱️  Duration: {duration:.2f} seconds")
        logger.info(f"📁 Output location: {self.bronze_path}")
        
        if failed_count > 0:
            logger.warning("\n⚠️  Failed tables:")
            for table, result in results.items():
                if result['status'] == 'FAILED':
                    logger.warning(f"   - {table}: {result.get('error', 'Unknown error')}")
        
        logger.info("=" * 80)
        
        return results
    
    def verify_bronze_data(self):
        """Verify Bronze layer data quality"""
        logger.info("\n🔍 Verifying Bronze layer data...")
        
        tables = [
            'player_profiles', 'player_performances', 'player_market_value',
            'player_injuries', 'transfer_history', 'team_details'
        ]
        
        for table in tables:
            try:
                path = f"{self.bronze_path}/{table}"
                df = self.spark.read.parquet(path)
                
                count = df.count()
                columns = len(df.columns)
                
                logger.info(f"   {table}: {count:,} rows, {columns} columns")
                
            except Exception as e:
                logger.warning(f"   ⚠️ {table}: Not found or error - {str(e)}")
    
    def stop(self):
        """Stop Spark session"""
        if self.spark:
            self.spark.stop()
            logger.info("🛑 Bronze Layer - Spark session stopped")


def main():
    """Main entry point for Bronze layer"""
    logger.info("\n" + "=" * 80)
    logger.info("⚽ FOOTBALL ANALYTICS - BRONZE LAYER")
    logger.info("=" * 80)
    
    bronze = BronzeLayer()
    
    try:
        # Ingest all data
        results = bronze.ingest_all_tables()
        
        # Verify data
        bronze.verify_bronze_data()
        
        logger.info("\n✅ Bronze layer processing completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Bronze layer processing failed: {str(e)}")
        raise
    finally:
        bronze.stop()


if __name__ == '__main__':
    main()
