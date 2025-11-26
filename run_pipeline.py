#!/usr/bin/env python3
"""
Football Analytics ETL Pipeline Orchestrator
Chạy toàn bộ pipeline: Bronze → Silver → Gold → PostgreSQL → Validation
"""

import sys
import time
from datetime import datetime


def print_header(title: str):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_success(message: str, elapsed: float):
    """Print success message with timing"""
    print(f"\n✅ {message} ({elapsed:.2f}s)")


def print_error(message: str, error: Exception):
    """Print error message"""
    print(f"\n❌ {message}")
    print(f"   Error: {str(error)}")


def run_bronze_layer():
    """Step 1: Load CSV → Parquet (Bronze)"""
    print_header("🥉 BRONZE LAYER: CSV → Parquet")
    start = time.time()
    
    from src.bronze_layer import BronzeLayer
    bronze = BronzeLayer()
    bronze.ingest_all_tables()
    bronze.stop()
    
    elapsed = time.time() - start
    print_success("Bronze layer completed", elapsed)
    return elapsed


def run_silver_layer():
    """Step 2: Clean & Standardize (Silver)"""
    print_header("🥈 SILVER LAYER: Data Cleaning & Standardization")
    start = time.time()
    
    from src.silver_layer import SilverLayer
    silver = SilverLayer()
    silver.process_all_tables()
    silver.stop()
    
    elapsed = time.time() - start
    print_success("Silver layer completed", elapsed)
    return elapsed


def run_gold_layer():
    """Step 3: Analytics Aggregation (Gold)"""
    print_header("🥇 GOLD LAYER: Analytics Aggregation")
    start = time.time()
    
    from src.gold_layer import GoldLayer
    gold = GoldLayer()
    gold.process_all_analytics()
    gold.stop()
    
    elapsed = time.time() - start
    print_success("Gold layer completed", elapsed)
    return elapsed


def load_silver_to_postgres():
    """Step 4: Load Silver to PostgreSQL"""
    print_header("📊 LOAD SILVER TO POSTGRESQL")
    start = time.time()
    
    # Run the loader script as a subprocess to ensure JDBC driver is loaded in a fresh process
    import subprocess
    cmd = ['python', 'schema/load_silver_to_postgres.py', '--mode', 'recommended']
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise Exception('Silver to Postgres loader failed')
    
    elapsed = time.time() - start
    print_success("Silver data loaded to PostgreSQL", elapsed)
    return elapsed


def load_gold_to_postgres():
    """Step 5: Load Gold to PostgreSQL"""
    print_header("📊 LOAD GOLD TO POSTGRESQL")
    start = time.time()
    
    # Run the gold loader script as a subprocess (it handles its own Spark/JDBC setup)
    import subprocess
    cmd = ['python', 'schema/load_gold_to_postgres.py']
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise Exception('Gold to Postgres loader failed')
    
    elapsed = time.time() - start
    print_success("Gold data loaded to PostgreSQL", elapsed)
    return elapsed


def create_views():
    """Step 6: Create Views and Materialized Views"""
    print_header("🔍 CREATE VIEWS & MATERIALIZED VIEWS")
    start = time.time()
    
    import subprocess
    cmd = ['python', 'schema/create_views.py']
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise Exception('Views creation failed')
    
    elapsed = time.time() - start
    print_success("Views and materialized views created", elapsed)
    return elapsed


def run_validation():
    """Step 6: Data Quality Validation"""
    print_header("✅ DATA QUALITY VALIDATION")
    start = time.time()
    
    import subprocess
    result = subprocess.run(
        ['python', 'validate_data.py'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    elapsed = time.time() - start
    
    if result.returncode == 0:
        print_success("Data validation completed", elapsed)
    else:
        print_error("Data validation failed", Exception(f"Exit code: {result.returncode}"))
    
    return elapsed


def main():
    """Run full ETL pipeline"""
    pipeline_start = time.time()
    
    print("\n" + "🚀" * 40)
    print("  FOOTBALL ANALYTICS ETL PIPELINE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀" * 40)
    
    timings = {}
    
    try:
        # Step 1: Bronze Layer
        timings['bronze'] = run_bronze_layer()
        
        # Step 2: Silver Layer
        timings['silver'] = run_silver_layer()
        
        # Step 3: Gold Layer
        timings['gold'] = run_gold_layer()
        
        # Step 4: Load Silver to PostgreSQL
        timings['load_silver'] = load_silver_to_postgres()
        
        # Step 5: Load Gold to PostgreSQL
        timings['load_gold'] = load_gold_to_postgres()
        
        # Step 6: Create Views and Materialized Views
        timings['create_views'] = create_views()
        
        # Step 7: Data Validation
        timings['validation'] = run_validation()
        
        # Summary
        total_elapsed = time.time() - pipeline_start
        
        print("\n" + "=" * 80)
        print("  📈 PIPELINE SUMMARY")
        print("=" * 80)
        print(f"  Bronze Layer:       {timings['bronze']:>8.2f}s")
        print(f"  Silver Layer:       {timings['silver']:>8.2f}s")
        print(f"  Gold Layer:         {timings['gold']:>8.2f}s")
        print(f"  Load Silver:        {timings['load_silver']:>8.2f}s")
        print(f"  Load Gold:          {timings['load_gold']:>8.2f}s")
        print(f"  Create Views:       {timings['create_views']:>8.2f}s")
        print(f"  Validation:         {timings['validation']:>8.2f}s")
        print("  " + "-" * 76)
        print(f"  TOTAL:              {total_elapsed:>8.2f}s")
        print("=" * 80)
        
        print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        return 1
        
    except Exception as e:
        print("\n\n❌ PIPELINE FAILED")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
