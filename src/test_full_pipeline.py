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
    logger.info("[BRONZE] TESTING BRONZE LAYER")
    logger.info("="*90)
    
    try:
        bronze = BronzeLayer()
        bronze.ingest_all_tables()
        bronze.stop()
        logger.info("[SUCCESS] Bronze layer test PASSED")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Bronze layer test FAILED: {str(e)}")
        return False


def test_silver_layer():
    """Test Silver layer cleaning"""
    logger.info("\n" + "="*90)
    logger.info("[SILVER] TESTING SILVER LAYER")
    logger.info("="*90)
    
    try:
        silver = SilverLayer()
        silver.process_all_tables()  # Changed from clean_all_tables
        silver.stop()
        logger.info("[SUCCESS] Silver layer test PASSED")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Silver layer test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_gold_layer():
    """Test Gold layer analytics"""
    logger.info("\n" + "="*90)
    logger.info("[GOLD] TESTING GOLD LAYER")
    logger.info("="*90)
    
    try:
        gold = GoldLayer()
        gold.process_all_analytics(write_to_db=False)
        gold.stop()
        logger.info("[SUCCESS] Gold layer test PASSED")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Gold layer test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run full pipeline test"""
    logger.info("\n" + "="*90)
    logger.info("[FOOTBALL] FOOTBALL ANALYTICS - FULL PIPELINE TEST")
    logger.info("="*90)
    
    start_time = datetime.now()
    results = {}
    
    # Test each layer
    results['bronze'] = test_bronze_layer()
    
    if results['bronze']:
        results['silver'] = test_silver_layer()
    else:
        logger.error("[SKIP]  Skipping Silver layer (Bronze failed)")
        results['silver'] = False
    
    if results['silver']:
        results['gold'] = test_gold_layer()
    else:
        logger.error("[SKIP]  Skipping Gold layer (Silver failed)")
        results['gold'] = False
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "="*90)
    logger.info("[DATA] PIPELINE TEST SUMMARY")
    logger.info("="*90)
    logger.info(f"[BRONZE] Bronze Layer: {'[SUCCESS] PASSED' if results['bronze'] else '[ERROR] FAILED'}")
    logger.info(f"[SILVER] Silver Layer: {'[SUCCESS] PASSED' if results['silver'] else '[ERROR] FAILED'}")
    logger.info(f"[GOLD] Gold Layer:   {'[SUCCESS] PASSED' if results['gold'] else '[ERROR] FAILED'}")
    logger.info(f"[TIME]  Total Duration: {duration:.2f} seconds")
    logger.info("="*90)
    
    # Exit code
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n[COMPLETE] ALL TESTS PASSED!")
        return 0
    else:
        logger.error("\n[ERROR] SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
