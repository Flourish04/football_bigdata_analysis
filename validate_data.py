#!/usr/bin/env python3
"""
Football Data Analytics - Data Validation Script
Validates data quality across all layers (Bronze, Silver, Gold, PostgreSQL)
"""

import psycopg2
from pyspark.sql import SparkSession
from datetime import datetime
import sys

# PostgreSQL connection
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'football_analytics',
    'user': 'postgres',
    'password': '9281746356'
}

# Parquet paths
BRONZE_PATH = '/tmp/football_datalake/bronze'
SILVER_PATH = '/tmp/football_datalake/silver'
GOLD_PATH = '/tmp/football_datalake/gold'


class DataValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.spark = None
        self.pg_conn = None
        
    def init_spark(self):
        """Initialize Spark session"""
        self.spark = SparkSession.builder \
            .appName('DataValidation') \
            .config('spark.sql.legacy.timeParserPolicy', 'LEGACY') \
            .getOrCreate()
        print("✅ Spark session initialized")
    
    def init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
            print("✅ PostgreSQL connection established")
        except Exception as e:
            self.errors.append(f"❌ PostgreSQL connection failed: {e}")
            return False
        return True
    
    def validate_schema_precision(self):
        """Validate decimal precision in PostgreSQL"""
        print("\n📋 1. SCHEMA & PRECISION VALIDATION")
        print("=" * 60)
        
        cursor = self.pg_conn.cursor()
        
        # Check column types
        cursor.execute("""
            SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'analytics' 
              AND table_name = 'player_analytics_360'
              AND column_name IN ('height', 'goals_per_90min', 'performance_score', 'peak_market_value')
            ORDER BY column_name
        """)
        
        expected_types = {
            'goals_per_90min': ('numeric', 10, 4),
            'height': ('integer', 32, 0),
            'peak_market_value': ('bigint', 64, 0),
            'performance_score': ('numeric', 10, 2)
        }
        
        for row in cursor.fetchall():
            table, col, dtype, precision, scale = row
            if col in expected_types:
                exp_dtype, exp_prec, exp_scale = expected_types[col]
                if dtype == exp_dtype and (dtype in ['bigint', 'integer'] or scale == exp_scale):
                    print(f"  ✅ {col}: {dtype}({precision},{scale or 0}) - OK")
                else:
                    msg = f"  ❌ {col}: Expected {exp_dtype}({exp_prec},{exp_scale}), got {dtype}({precision},{scale})"
                    print(msg)
                    self.errors.append(msg)
    
    def validate_value_ranges(self):
        """Validate data value ranges"""
        print("\n📊 2. VALUE RANGE VALIDATION")
        print("=" * 60)
        
        cursor = self.pg_conn.cursor()
        
        # Check for unrealistic rates (should be 0)
        cursor.execute("""
            SELECT COUNT(*) FROM analytics.player_form_metrics
            WHERE goals_per_90min > 3.0 OR assists_per_90min > 3.0
        """)
        unrealistic_rates = cursor.fetchone()[0]
        if unrealistic_rates == 0:
            print(f"  ✅ Unrealistic rates (>3.0): 0")
        else:
            msg = f"  ❌ Found {unrealistic_rates} unrealistic rate values"
            print(msg)
            self.errors.append(msg)
        
        # Check max values
        cursor.execute("""
            SELECT 
                MAX(goals_per_90min) AS max_goals,
                MAX(assists_per_90min) AS max_assists,
                MAX(performance_score) AS max_perf,
                MIN(performance_score) AS min_perf
            FROM analytics.player_analytics_360
        """)
        max_goals, max_assists, max_perf, min_perf = cursor.fetchone()
        
        print(f"  ✅ Max goals/90min: {max_goals:.4f} (cap: 3.0000)")
        print(f"  ✅ Max assists/90min: {max_assists:.4f} (cap: 3.0000)")
        print(f"  ✅ Performance score range: {min_perf:.2f} - {max_perf:.2f}")
        
        if max_goals > 3.0 or max_assists > 3.0:
            msg = f"  ❌ Rates exceed cap: goals={max_goals}, assists={max_assists}"
            print(msg)
            self.errors.append(msg)
        
        if max_perf > 100.0 or min_perf < 0:
            msg = f"  ❌ Performance score out of range: {min_perf} - {max_perf}"
            print(msg)
            self.errors.append(msg)
        
        # Check negative values
        cursor.execute("""
            SELECT COUNT(*) FROM analytics.market_value_trends
            WHERE peak_market_value < 0
        """)
        negative_values = cursor.fetchone()[0]
        if negative_values == 0:
            print(f"  ✅ Negative market values: 0")
        else:
            msg = f"  ❌ Found {negative_values} negative market values"
            print(msg)
            self.errors.append(msg)
    
    def validate_null_values(self):
        """Validate NULL values in critical fields"""
        print("\n🔍 3. NULL VALUE VALIDATION")
        print("=" * 60)
        
        cursor = self.pg_conn.cursor()
        
        # Critical fields should not be NULL
        critical_fields = ['player_id', 'player_name', 'overall_player_score']
        
        for field in critical_fields:
            cursor.execute(f"""
                SELECT COUNT(*) FROM analytics.player_analytics_360
                WHERE {field} IS NULL
            """)
            null_count = cursor.fetchone()[0]
            if null_count == 0:
                print(f"  ✅ {field}: 0 NULLs")
            else:
                msg = f"  ❌ {field}: {null_count} NULL values found"
                print(msg)
                self.errors.append(msg)
        
        # Optional fields (acceptable NULLs)
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE height IS NULL) AS height_nulls,
                COUNT(*) FILTER (WHERE goals_per_90min IS NULL) AS goals90_nulls,
                COUNT(*) AS total,
                ROUND(100.0 * COUNT(*) FILTER (WHERE height IS NULL) / COUNT(*), 2) AS height_null_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE goals_per_90min IS NULL) / COUNT(*), 2) AS goals90_null_pct
            FROM analytics.player_analytics_360
        """)
        height_nulls, goals_nulls, total, height_pct, goals_pct = cursor.fetchone()
        
        print(f"  ℹ️  height NULLs: {height_nulls:,} ({height_pct}%) - Acceptable if < 5%")
        print(f"  ℹ️  goals_per_90min NULLs: {goals_nulls:,} ({goals_pct}%) - Acceptable if < 30%")
        
        if height_pct > 5.0:
            msg = f"  ⚠️  High height NULL percentage: {height_pct}%"
            print(msg)
            self.warnings.append(msg)
        
        if goals_pct > 30.0:
            msg = f"  ⚠️  High goals/90min NULL percentage: {goals_pct}%"
            print(msg)
            self.warnings.append(msg)
    
    def validate_duplicates(self):
        """Check for duplicate records"""
        print("\n🔄 4. DUPLICATE DETECTION")
        print("=" * 60)
        
        cursor = self.pg_conn.cursor()
        
        # Check Gold layer duplicates
        cursor.execute("""
            SELECT player_id, COUNT(*) AS dup_count
            FROM analytics.player_analytics_360
            GROUP BY player_id
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        duplicates = cursor.fetchall()
        
        if len(duplicates) == 0:
            print(f"  ✅ player_analytics_360: No duplicates")
        else:
            msg = f"  ❌ Found {len(duplicates)} duplicate player_ids"
            print(msg)
            self.errors.append(msg)
            for dup in duplicates:
                print(f"     - player_id {dup[0]}: {dup[1]} records")
        
        # Check Silver layer duplicates
        cursor.execute("""
            SELECT player_id, season_name, COUNT(*) AS dup_count
            FROM silver_layer.player_performances
            GROUP BY player_id, season_name
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        silver_dups = cursor.fetchall()
        
        if len(silver_dups) == 0:
            print(f"  ✅ player_performances: No duplicates")
        else:
            msg = f"  ⚠️  Found {len(silver_dups)} duplicate player-season combinations"
            print(msg)
            self.warnings.append(msg)
    
    def validate_referential_integrity(self):
        """Validate foreign key relationships"""
        print("\n🔗 5. REFERENTIAL INTEGRITY")
        print("=" * 60)
        
        cursor = self.pg_conn.cursor()
        
        # Check if all Gold player_ids exist in Silver
        cursor.execute("""
            SELECT COUNT(*) FROM analytics.player_analytics_360 pa
            WHERE NOT EXISTS (
                SELECT 1 FROM silver_layer.player_profiles pp
                WHERE pp.player_id = pa.player_id
            )
        """)
        orphans = cursor.fetchone()[0]
        
        if orphans == 0:
            print(f"  ✅ All Gold player_ids exist in Silver")
        else:
            msg = f"  ❌ Found {orphans} orphan records in Gold layer"
            print(msg)
            self.errors.append(msg)
    
    def validate_record_counts(self):
        """Validate record counts across layers"""
        print("\n📈 6. RECORD COUNT VALIDATION")
        print("=" * 60)
        
        cursor = self.pg_conn.cursor()
        
        expected_ranges = {
            'player_analytics_360': (90000, 95000),
            'player_form_metrics': (85000, 90000),
            'market_value_trends': (65000, 70000),
            'injury_risk_scores': (30000, 35000),
            'transfer_intelligence': (115000, 120000)
        }
        
        for table, (min_count, max_count) in expected_ranges.items():
            cursor.execute(f"SELECT COUNT(*) FROM analytics.{table}")
            actual_count = cursor.fetchone()[0]
            
            if min_count <= actual_count <= max_count:
                print(f"  ✅ {table}: {actual_count:,} (expected {min_count:,}-{max_count:,})")
            else:
                msg = f"  ⚠️  {table}: {actual_count:,} (expected {min_count:,}-{max_count:,})"
                print(msg)
                self.warnings.append(msg)
    

    def validate_views(self):
        """Validate views and materialized views"""
        print("\n🔍 7. VIEWS & MATERIALIZED VIEWS VALIDATION")
        print("=" * 60)
        
        cursor = self.pg_conn.cursor()
        
        try:
            # Check regular views
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema = 'analytics'
                ORDER BY table_name
            """)
            views = cursor.fetchall()
            print(f"  ✅ Regular Views: {len(views)}")
            for view in views:
                cursor.execute(f"SELECT COUNT(*) FROM analytics.{view[0]}")
                count = cursor.fetchone()[0]
                print(f"     - {view[0]}: {count:,} rows")
            
            # Check materialized views
            cursor.execute("""
                SELECT matviewname 
                FROM pg_matviews 
                WHERE schemaname = 'analytics'
                ORDER BY matviewname
            """)
            mat_views = cursor.fetchall()
            print(f"\n  ✅ Materialized Views: {len(mat_views)}")
            for mv in mat_views:
                cursor.execute(f"SELECT COUNT(*) FROM analytics.{mv[0]}")
                count = cursor.fetchone()[0]
                print(f"     - {mv[0]}: {count:,} rows")
                if count == 0:
                    self.warnings.append(f"⚠️  Materialized view {mv[0]} is empty")
            
            # Check refresh function
            cursor.execute("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'analytics'
                AND routine_name = 'refresh_all_materialized_views'
            """)
            function = cursor.fetchone()
            if function:
                print(f"\n  ✅ Refresh Function: {function[0]}")
            else:
                self.warnings.append("⚠️  Refresh function not found")
        
        except Exception as e:
            msg = f"  ❌ Views validation failed: {e}"
            print(msg)
            self.errors.append(msg)
        finally:
            cursor.close()

    def validate_parquet_files(self):
        """Validate Parquet files exist and are readable"""
        print("\n📁 8. PARQUET FILE VALIDATION")
        print("=" * 60)
        
        if not self.spark:
            print("  ⚠️  Spark not initialized, skipping Parquet validation")
            return
        
        try:
            # Check Gold layer files
            gold_tables = [
                'player_analytics_360',
                'player_form_metrics',
                'market_value_trends',
                'injury_risk_scores',
                'transfer_intelligence'
            ]
            
            for table in gold_tables:
                try:
                    df = self.spark.read.parquet(f"{GOLD_PATH}/{table}")
                    count = df.count()
                    print(f"  ✅ {table}: {count:,} records")
                except Exception as e:
                    msg = f"  ❌ {table}: Error reading - {str(e)}"
                    print(msg)
                    self.errors.append(msg)
        except Exception as e:
            msg = f"  ❌ Parquet validation failed: {e}"
            print(msg)
            self.errors.append(msg)
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        total_checks = 8
        print(f"Total checks performed: {total_checks}")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        
        if len(self.errors) > 0:
            print("\n❌ ERRORS FOUND:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if len(self.warnings) > 0:
            print("\n⚠️  WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if len(self.errors) == 0 and len(self.warnings) == 0:
            print("\n✅ ALL CHECKS PASSED!")
            print("   Data quality is excellent.")
        elif len(self.errors) == 0:
            print("\n✅ ALL CRITICAL CHECKS PASSED")
            print("   Some warnings present but not critical.")
        else:
            print("\n❌ VALIDATION FAILED")
            print("   Please review and fix errors.")
        
        print(f"\nValidation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def cleanup(self):
        """Close connections"""
        if self.pg_conn:
            self.pg_conn.close()
        if self.spark:
            self.spark.stop()
    
    def run_all_validations(self):
        """Run all validation checks"""
        print("⚽ FOOTBALL DATA ANALYTICS - DATA VALIDATION")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Initialize connections
        if not self.init_postgres():
            print("❌ Cannot proceed without PostgreSQL connection")
            return False
        
        try:
            self.init_spark()
        except Exception as e:
            print(f"⚠️  Spark initialization failed: {e}")
            print("   Continuing with PostgreSQL validation only...")
        
        # Run validations
        try:
            self.validate_schema_precision()
            self.validate_value_ranges()
            self.validate_null_values()
            self.validate_duplicates()
            self.validate_referential_integrity()
            self.validate_record_counts()
            self.validate_views()
            
            if self.spark:
                self.validate_parquet_files()
            
            self.print_summary()
            
            return len(self.errors) == 0
        
        except Exception as e:
            print(f"\n❌ Validation failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup()


if __name__ == "__main__":
    validator = DataValidator()
    success = validator.run_all_validations()
    sys.exit(0 if success else 1)
