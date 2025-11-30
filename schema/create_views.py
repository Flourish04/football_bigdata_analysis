#!/usr/bin/env python3
"""
Create Views and Materialized Views in PostgreSQL
Executes analytics_schema.sql to create all views and materialized views
"""

import psycopg2
import logging
import sys
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ViewCreator:
    """Creates views and materialized views in PostgreSQL"""
    
    def __init__(self):
        """Initialize database connection"""
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                database="football_analytics",
                user="postgres",
                password=os.getenv('POSTGRES_PASSWORD', 'your_password')
            )
            self.cursor = self.conn.cursor()
            logger.info("[SUCCESS] Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to connect to database: {e}")
            return False
    
    def execute_sql_file(self, sql_file_path: str):
        """
        Execute SQL file to create views and materialized views
        
        Args:
            sql_file_path: Path to SQL file
        """
        try:
            sql_path = Path(sql_file_path)
            if not sql_path.exists():
                logger.error(f"[ERROR] SQL file not found: {sql_file_path}")
                return False
            
            logger.info(f"[FILE] Reading SQL file: {sql_file_path}")
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            logger.info("[SETUP] Executing SQL commands...")
            self.cursor.execute(sql_content)
            self.conn.commit()
            
            logger.info("[SUCCESS] SQL file executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to execute SQL file: {e}")
            self.conn.rollback()
            return False
    
    def verify_views(self):
        """Verify that views and materialized views were created"""
        try:
            logger.info("\n[DATA] Verifying created objects...")
            
            # Check regular views
            self.cursor.execute("""
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema = 'analytics'
                ORDER BY table_name
            """)
            views = self.cursor.fetchall()
            
            logger.info(f"\n[SUCCESS] Regular Views ({len(views)}):")
            for view in views:
                logger.info(f"   - {view[0]}")
            
            # Check materialized views
            self.cursor.execute("""
                SELECT matviewname 
                FROM pg_matviews 
                WHERE schemaname = 'analytics'
                ORDER BY matviewname
            """)
            mat_views = self.cursor.fetchall()
            
            logger.info(f"\n[SUCCESS] Materialized Views ({len(mat_views)}):")
            for mv in mat_views:
                logger.info(f"   - {mv[0]}")
            
            # Check refresh function
            self.cursor.execute("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'analytics'
                AND routine_name = 'refresh_all_materialized_views'
            """)
            function = self.cursor.fetchone()
            
            if function:
                logger.info(f"\n[SUCCESS] Refresh Function: {function[0]}")
            
            return len(views) > 0 or len(mat_views) > 0
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to verify views: {e}")
            return False
    
    def refresh_materialized_views(self):
        """Refresh all materialized views"""
        try:
            logger.info("\n[PROCESS] Refreshing materialized views...")
            self.cursor.execute("SELECT analytics.refresh_all_materialized_views()")
            self.conn.commit()
            
            # Get row counts
            self.cursor.execute("""
                SELECT 
                    'mvw_position_statistics' as view_name,
                    COUNT(*) as row_count 
                FROM analytics.mvw_position_statistics
                UNION ALL
                SELECT 
                    'mvw_age_group_analysis',
                    COUNT(*) 
                FROM analytics.mvw_age_group_analysis
            """)
            results = self.cursor.fetchall()
            
            logger.info("\n[DATA] Materialized View Row Counts:")
            for view_name, row_count in results:
                logger.info(f"   - {view_name}: {row_count:,} rows")
            
            logger.info("[SUCCESS] Materialized views refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to refresh materialized views: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("[CONNECT] Database connection closed")


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("  CREATE VIEWS AND MATERIALIZED VIEWS")
    logger.info("=" * 80)
    
    # Get SQL file path
    script_dir = Path(__file__).parent
    sql_file = script_dir / "create_views_only.sql"
    
    # Create views
    creator = ViewCreator()
    
    try:
        # Connect to database
        if not creator.connect():
            sys.exit(1)
        
        # Execute SQL file
        if not creator.execute_sql_file(str(sql_file)):
            sys.exit(1)
        
        # Verify views were created
        if not creator.verify_views():
            logger.warning("[WARNING]  No views found - check SQL file")
        
        # Refresh materialized views
        if not creator.refresh_materialized_views():
            logger.warning("[WARNING]  Failed to refresh materialized views")
        
        logger.info("\n" + "=" * 80)
        logger.info("[COMPLETE] VIEWS CREATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)
    finally:
        creator.close()


if __name__ == "__main__":
    main()
