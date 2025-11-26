"""
PostgreSQL Data Loader for Gold Layer Analytics

This script loads Gold Layer Parquet files into PostgreSQL analytics schema.
Requires: PostgreSQL database with analytics schema already created.

Usage:
    python schema/load_gold_to_postgres.py

Configuration:
    Set environment variables:
    - POSTGRES_HOST (default: localhost)
    - POSTGRES_PORT (default: 5432)
    - POSTGRES_DB (default: football_analytics)
    - POSTGRES_USER (default: postgres)
    - POSTGRES_PASSWORD (default: postgres)
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from pyspark.sql import SparkSession

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/postgres_loader.log')
    ]
)
logger = logging.getLogger(__name__)

# PostgreSQL configuration from environment
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'football_analytics')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '9281746356')

POSTGRES_URL = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Gold Layer path
GOLD_PATH = "/tmp/football_datalake/gold"

# Tables to load (in order - respects dependencies)
TABLES = [
    'player_form_metrics',
    'market_value_trends',
    'injury_risk_scores',
    'transfer_intelligence',
    'player_analytics_360'
]


class PostgreSQLLoader:
    """Load Gold Layer Parquet files into PostgreSQL"""
    
    def __init__(self, gold_path: str, postgres_url: str):
        self.gold_path = gold_path
        self.postgres_url = postgres_url
        self.spark = None
        self.load_stats = {}
        
    def initialize_spark(self):
        """Initialize Spark session with PostgreSQL JDBC driver"""
        logger.info("🚀 Initializing Spark session...")
        
        # Check if PostgreSQL JDBC driver is available
        jdbc_jar_path = self._find_postgres_jdbc_driver()
        
        builder = SparkSession.builder \
            .appName("PostgreSQL Loader") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.driver.memory", "4g") \
            .config("spark.executor.memory", "4g")
        
        if jdbc_jar_path:
            logger.info(f"   Using PostgreSQL JDBC driver: {jdbc_jar_path}")
            builder = builder.config("spark.jars", jdbc_jar_path)
        else:
            logger.warning("   ⚠️  PostgreSQL JDBC driver not found")
            logger.warning("   Download from: https://jdbc.postgresql.org/download/")
            logger.warning("   Place in: /usr/share/java/ or specify with SPARK_CLASSPATH")
        
        self.spark = builder.getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")
        
        logger.info("✅ Spark session initialized")
        
    def _find_postgres_jdbc_driver(self) -> str:
        """Find PostgreSQL JDBC driver in common locations"""
        common_paths = [
            "./jars/postgresql-42.7.1.jar",
            "../jars/postgresql-42.7.1.jar",
            "/usr/share/java/postgresql.jar",
            "/usr/share/java/postgresql-42.jar",
            "/usr/local/share/java/postgresql.jar",
            os.path.expanduser("~/.m2/repository/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar"),
            "./lib/postgresql.jar"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
        
    def load_table(self, table_name: str) -> bool:
        """Load a single table from Parquet to PostgreSQL"""
        logger.info(f"📊 Loading table: {table_name}")
        
        input_path = f"{self.gold_path}/{table_name}"
        
        # Check if Parquet file exists
        if not os.path.exists(input_path):
            logger.error(f"   ❌ Input path not found: {input_path}")
            self.load_stats[table_name] = {
                'status': 'FAILED',
                'error': 'Input file not found',
                'records': 0
            }
            return False
        
        try:
            start_time = datetime.now()
            
            # Read Parquet
            logger.info(f"   Reading Parquet: {input_path}")
            df = self.spark.read.parquet(input_path)
            record_count = df.count()
            
            logger.info(f"   Found {record_count:,} records")
            
            # Write to PostgreSQL
            logger.info(f"   Writing to PostgreSQL: analytics.{table_name}")
            df.write \
                .format("jdbc") \
                .option("url", self.postgres_url) \
                .option("dbtable", f"analytics.{table_name}") \
                .option("user", POSTGRES_USER) \
                .option("password", POSTGRES_PASSWORD) \
                .option("driver", "org.postgresql.Driver") \
                .option("batchsize", "10000") \
                .option("truncate", "true") \
                .mode("overwrite") \
                .save()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"   ✅ {table_name} loaded successfully")
            logger.info(f"   📊 Records: {record_count:,}")
            logger.info(f"   ⏱️  Duration: {duration:.2f}s")
            
            self.load_stats[table_name] = {
                'status': 'SUCCESS',
                'records': record_count,
                'duration': duration
            }
            
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Failed to load {table_name}: {str(e)}")
            self.load_stats[table_name] = {
                'status': 'FAILED',
                'error': str(e),
                'records': 0
            }
            return False
            
    def load_all_tables(self):
        """Load all Gold Layer tables to PostgreSQL"""
        logger.info("=" * 60)
        logger.info("PostgreSQL Data Loader - Gold Layer → PostgreSQL")
        logger.info("=" * 60)
        logger.info(f"Gold Path: {self.gold_path}")
        logger.info(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        logger.info(f"Schema: analytics")
        logger.info(f"Tables to load: {len(TABLES)}")
        logger.info("")
        
        # Initialize Spark
        self.initialize_spark()
        
        # Load each table
        success_count = 0
        failed_count = 0
        total_records = 0
        
        for table_name in TABLES:
            logger.info("")
            success = self.load_table(table_name)
            
            if success:
                success_count += 1
                total_records += self.load_stats[table_name]['records']
            else:
                failed_count += 1
        
        # Print summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("Load Summary")
        logger.info("=" * 60)
        
        for table_name, stats in self.load_stats.items():
            status_icon = "✅" if stats['status'] == 'SUCCESS' else "❌"
            logger.info(f"{status_icon} {table_name}: {stats['status']}")
            
            if stats['status'] == 'SUCCESS':
                logger.info(f"   Records: {stats['records']:,}")
                logger.info(f"   Duration: {stats['duration']:.2f}s")
            else:
                logger.info(f"   Error: {stats.get('error', 'Unknown error')}")
        
        logger.info("")
        logger.info(f"✅ Successful: {success_count}/{len(TABLES)}")
        logger.info(f"❌ Failed: {failed_count}/{len(TABLES)}")
        logger.info(f"📊 Total records loaded: {total_records:,}")
        logger.info("")
        
        if success_count == len(TABLES):
            logger.info("🎉 All tables loaded successfully!")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Run VACUUM ANALYZE on all tables")
            logger.info("  2. Refresh materialized views:")
            logger.info("     SELECT analytics.refresh_all_materialized_views();")
            logger.info("  3. Test queries on loaded data")
        else:
            logger.warning(f"⚠️  {failed_count} table(s) failed to load")
            logger.warning("Check logs for details: /tmp/postgres_loader.log")
        
        # Cleanup
        self.spark.stop()
        
        return success_count == len(TABLES)


def main():
    """Main execution"""
    # Check if Gold Layer path exists
    if not os.path.exists(GOLD_PATH):
        logger.error(f"❌ Gold Layer path not found: {GOLD_PATH}")
        logger.error("   Please run Gold Layer ETL first:")
        logger.error("   python src/gold_layer.py")
        sys.exit(1)
    
    # Create loader and run
    loader = PostgreSQLLoader(
        gold_path=GOLD_PATH,
        postgres_url=POSTGRES_URL
    )
    
    success = loader.load_all_tables()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Load interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
