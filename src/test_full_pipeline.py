"""
Test Full ETL Pipeline: Bronze → Silver → Gold
Tests the complete data flow with actual column mappings
"""

import logging
import sys
from datetime import datetime
from bronze_layer import BronzeLayer
from silver_layer import SilverLayer
from gold_layer import GoldLayer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_bronze_layer():
    """Test Bronze layer ingestion"""
    logger.info("\n" + "="*90)
    logger.info("🥉 TESTING BRONZE LAYER")
    logger.info("="*90)
    
    try:
        bronze = BronzeLayer()
        bronze.ingest_all_tables()
        bronze.stop()
        logger.info("✅ Bronze layer test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Bronze layer test FAILED: {str(e)}")
        return False


def test_silver_layer():
    """Test Silver layer cleaning"""
    logger.info("\n" + "="*90)
    logger.info("🥈 TESTING SILVER LAYER")
    logger.info("="*90)
    
    try:
        silver = SilverLayer()
        silver.process_all_tables()  # Changed from clean_all_tables
        silver.stop()
        logger.info("✅ Silver layer test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Silver layer test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_gold_layer():
    """Test Gold layer analytics"""
    logger.info("\n" + "="*90)
    logger.info("🥇 TESTING GOLD LAYER")
    logger.info("="*90)
    
    try:
        gold = GoldLayer()
        gold.process_all_analytics(write_to_db=False)
        gold.stop()
        logger.info("✅ Gold layer test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Gold layer test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run full pipeline test"""
    logger.info("\n" + "="*90)
    logger.info("⚽ FOOTBALL ANALYTICS - FULL PIPELINE TEST")
    logger.info("="*90)
    
    start_time = datetime.now()
    results = {}
    
    # Test each layer
    results['bronze'] = test_bronze_layer()
    
    if results['bronze']:
        results['silver'] = test_silver_layer()
    else:
        logger.error("⏭️  Skipping Silver layer (Bronze failed)")
        results['silver'] = False
    
    if results['silver']:
        results['gold'] = test_gold_layer()
    else:
        logger.error("⏭️  Skipping Gold layer (Silver failed)")
        results['gold'] = False
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "="*90)
    logger.info("📊 PIPELINE TEST SUMMARY")
    logger.info("="*90)
    logger.info(f"🥉 Bronze Layer: {'✅ PASSED' if results['bronze'] else '❌ FAILED'}")
    logger.info(f"🥈 Silver Layer: {'✅ PASSED' if results['silver'] else '❌ FAILED'}")
    logger.info(f"🥇 Gold Layer:   {'✅ PASSED' if results['gold'] else '❌ FAILED'}")
    logger.info(f"⏱️  Total Duration: {duration:.2f} seconds")
    logger.info("="*90)
    
    # Exit code
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
