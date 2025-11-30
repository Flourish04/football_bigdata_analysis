#!/usr/bin/env python3
"""
Load SELECTIVE Silver tables to PostgreSQL for easy querying
Strategy: Load small dimension tables, keep large fact tables in Parquet

Recommended tables to load:
  [SUCCESS] team_details (2,175 rows) - Dimension table
  [SUCCESS] team_children (7,695 rows) - Team relationships
  [SUCCESS] team_competitions_seasons (58,247 rows) - Competition metadata
  [WARNING]  player_profiles (92,671 rows) - Optional, for quick lookups
  
Skip large fact tables (query via Spark):
  [ERROR] player_performances (1.8M rows)
  [ERROR] player_market_value (901K rows)
  [ERROR] transfer_history (1.1M rows)
  [ERROR] player_teammates (1.2M rows)
"""

from pyspark.sql import SparkSession
import time
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SilverToPostgresLoader:
    """Load selective Silver layer tables to PostgreSQL"""
    
    def __init__(self, 
                 postgres_host='localhost',
                 postgres_port=5432,
                 postgres_db='football_analytics',
                 postgres_user='postgres',
                 postgres_password=None,
                 silver_path='/tmp/football_datalake/silver'):
        
        postgres_password = postgres_password or os.getenv('POSTGRES_PASSWORD', 'your_password')
        self.postgres_url = f'jdbc:postgresql://{postgres_host}:{postgres_port}/{postgres_db}'
        self.properties = {
            'user': postgres_user,
            'password': postgres_password,
            'driver': 'org.postgresql.Driver',
            'batchsize': '1000'
        }
        self.silver_path = silver_path
        
        # Find JDBC driver
        self.jdbc_jar = self._find_jdbc_driver()
        
        # Create Spark session
        self.spark = SparkSession.builder \
            .appName('LoadSilverToPostgreSQL') \
            .config('spark.jars', self.jdbc_jar) \
            .config('spark.driver.memory', '4g') \
            .config('spark.executor.memory', '4g') \
            .getOrCreate()
        
        logger.info("[SUCCESS] SilverToPostgresLoader initialized")
    
    def _find_jdbc_driver(self):
        """Find PostgreSQL JDBC driver"""
        search_paths = [
            './jars/postgresql-42.7.1.jar',
            'jars/postgresql-42.7.1.jar',
            '/tmp/postgresql-42.7.1.jar',
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"[SUCCESS] Found JDBC driver: {path}")
                return path
        
        raise FileNotFoundError(
            "[ERROR] PostgreSQL JDBC driver not found. "
            "Download from: https://jdbc.postgresql.org/download/"
        )
    
    def create_schema(self):
        """Create silver_layer schema in PostgreSQL"""
        import psycopg2
        
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='football_analytics',
                user='postgres',
                password=os.getenv('POSTGRES_PASSWORD', 'your_password')
            )
            cur = conn.cursor()
            
            # Create schema
            cur.execute("CREATE SCHEMA IF NOT EXISTS silver_layer;")
            conn.commit()
            
            logger.info("[SUCCESS] Schema 'silver_layer' created")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to create schema: {e}")
            raise
    
    def load_table(self, table_name, schema='silver_layer', mode='overwrite'):
        """Load a single Silver table to PostgreSQL"""
        try:
            start_time = time.time()
            logger.info(f"[DATA] Loading table: {table_name}")
            
            # Read from Parquet
            parquet_path = f"{self.silver_path}/{table_name}"
            logger.info(f"   Reading Parquet: {parquet_path}")
            df = self.spark.read.parquet(parquet_path)
            
            row_count = df.count()
            logger.info(f"   Found {row_count:,} records")
            
            # Write to PostgreSQL
            target_table = f"{schema}.{table_name}"
            logger.info(f"   Writing to PostgreSQL: {target_table}")
            
            df.write.jdbc(
                url=self.postgres_url,
                table=target_table,
                mode=mode,
                properties=self.properties
            )
            
            duration = time.time() - start_time
            logger.info(f"   [SUCCESS] {table_name} loaded successfully")
            logger.info(f"   [TIME]  Duration: {duration:.2f}s")
            
            return {
                'table': table_name,
                'status': 'SUCCESS',
                'records': row_count,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"   [ERROR] Failed to load {table_name}: {str(e)[:200]}")
            return {
                'table': table_name,
                'status': 'FAILED',
                'error': str(e)[:200]
            }
    
    def load_recommended_tables(self):
        """Load recommended Silver tables (small dimension tables)"""
        
        # Recommended tables to load
        recommended_tables = [
            ('team_details', 'Small dimension table - 2K rows'),
            ('team_children', 'Team relationships - 8K rows'),
            ('team_competitions_seasons', 'Competition metadata - 58K rows'),
        ]
        
        # Optional tables (if needed)
        optional_tables = [
            ('player_profiles', 'Player master data - 93K rows'),
            ('player_injuries', 'Injury history - 143K rows'),
            ('player_national_performances', 'National team stats - 93K rows'),
        ]
        
        logger.info("\n" + "="*70)
        logger.info("[TARGET] LOADING RECOMMENDED SILVER TABLES")
        logger.info("="*70)
        
        results = []
        
        # Load recommended tables
        for table_name, description in recommended_tables:
            logger.info(f"\n[BATCH] {table_name} - {description}")
            result = self.load_table(table_name)
            results.append(result)
        
        # Show optional tables (don't load by default)
        logger.info("\n" + "="*70)
        logger.info("[WARNING]  OPTIONAL TABLES (not loaded by default)")
        logger.info("="*70)
        for table_name, description in optional_tables:
            logger.info(f"   {table_name} - {description}")
        
        logger.info("\n   To load optional tables, run:")
        logger.info("   loader.load_table('player_profiles')")
        
        return results
    
    def load_all_small_tables(self, max_rows=100000):
        """Load all Silver tables with < max_rows records"""
        
        logger.info(f"\n[CHECK] Finding Silver tables with < {max_rows:,} rows...")
        
        # Get all Silver tables
        import os
        silver_tables = [d for d in os.listdir(self.silver_path) 
                        if os.path.isdir(os.path.join(self.silver_path, d))]
        
        small_tables = []
        large_tables = []
        
        for table_name in silver_tables:
            try:
                df = self.spark.read.parquet(f"{self.silver_path}/{table_name}")
                row_count = df.count()
                
                if row_count < max_rows:
                    small_tables.append((table_name, row_count))
                else:
                    large_tables.append((table_name, row_count))
                    
            except Exception as e:
                logger.warning(f"[WARNING]  Skipping {table_name}: {e}")
        
        # Display summary
        logger.info(f"\n[SUCCESS] Small tables (< {max_rows:,} rows) - WILL LOAD:")
        for table, count in sorted(small_tables, key=lambda x: x[1]):
            logger.info(f"   {table:40s} {count:>10,} rows")
        
        logger.info(f"\n[ERROR] Large tables (>= {max_rows:,} rows) - SKIP:")
        for table, count in sorted(large_tables, key=lambda x: x[1]):
            logger.info(f"   {table:40s} {count:>10,} rows")
        
        # Load small tables
        logger.info("\n" + "="*70)
        logger.info("[BATCH] Loading small tables...")
        logger.info("="*70)
        
        results = []
        for table_name, row_count in small_tables:
            result = self.load_table(table_name)
            results.append(result)
        
        return results
    
    def print_summary(self, results):
        """Print loading summary"""
        logger.info("\n" + "="*70)
        logger.info("[DATA] LOADING SUMMARY")
        logger.info("="*70)
        
        successful = [r for r in results if r['status'] == 'SUCCESS']
        failed = [r for r in results if r['status'] == 'FAILED']
        
        for result in successful:
            logger.info(f"[SUCCESS] {result['table']}: SUCCESS")
            logger.info(f"   Records: {result['records']:,}")
            logger.info(f"   Duration: {result['duration']:.2f}s")
        
        for result in failed:
            logger.info(f"[ERROR] {result['table']}: FAILED")
            logger.info(f"   Error: {result['error']}")
        
        total_records = sum(r['records'] for r in successful)
        total_duration = sum(r['duration'] for r in successful)
        
        logger.info(f"\n[SUCCESS] Successful: {len(successful)}/{len(results)}")
        logger.info(f"[ERROR] Failed: {len(failed)}/{len(results)}")
        logger.info(f"[DATA] Total records loaded: {total_records:,}")
        logger.info(f"[TIME]  Total duration: {total_duration:.2f}s")
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        logger.info("[STOP] Spark session stopped")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load Silver tables to PostgreSQL')
    parser.add_argument('--mode', choices=['recommended', 'all-small', 'custom'], 
                       default='recommended',
                       help='Loading mode')
    parser.add_argument('--tables', nargs='+', 
                       help='Custom tables to load (for --mode=custom)')
    parser.add_argument('--max-rows', type=int, default=100000,
                       help='Max rows for --mode=all-small')
    
    args = parser.parse_args()
    
    # Create loader
    loader = SilverToPostgresLoader()
    
    try:
        # Create schema
        loader.create_schema()
        
        # Load based on mode
        if args.mode == 'recommended':
            results = loader.load_recommended_tables()
        
        elif args.mode == 'all-small':
            results = loader.load_all_small_tables(max_rows=args.max_rows)
        
        elif args.mode == 'custom':
            if not args.tables:
                logger.error("[ERROR] --tables required for custom mode")
                return
            
            results = []
            for table in args.tables:
                result = loader.load_table(table)
                results.append(result)
        
        # Print summary
        loader.print_summary(results)
        
        # Verification query
        logger.info("\n" + "="*70)
        logger.info("[CHECK] VERIFICATION QUERIES")
        logger.info("="*70)
        logger.info("\nRun in psql:")
        logger.info("  \\dt silver_layer.*")
        logger.info("  SELECT COUNT(*) FROM silver_layer.team_details;")
        logger.info("  SELECT * FROM silver_layer.team_details LIMIT 5;")
        
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        loader.stop()


if __name__ == '__main__':
    main()
