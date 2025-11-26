#!/usr/bin/env python3
"""
Data Quality Check & Cleaning Script
Kiểm tra và làm sạch dữ liệu từ CSV files trước khi chạy ETL pipeline
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataQualityChecker:
    """Kiểm tra chất lượng dữ liệu từ Transfermarkt dataset"""
    
    def __init__(self, data_path: str = "football-datasets/datalake/transfermarkt"):
        self.data_path = Path(data_path)
        self.report = defaultdict(dict)
        self.issues = defaultdict(list)
        
    def check_file_exists(self, table_name: str) -> bool:
        """Kiểm tra file CSV có tồn tại không"""
        file_path = self.data_path / table_name / f"{table_name}.csv"
        exists = file_path.exists()
        
        if exists:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ {table_name}.csv - {size_mb:.2f} MB")
            self.report[table_name]['file_size_mb'] = round(size_mb, 2)
        else:
            logger.error(f"❌ {table_name}.csv - NOT FOUND")
            self.issues[table_name].append("File not found")
        
        return exists
    
    def load_sample(self, table_name: str, nrows: int = 1000) -> pd.DataFrame:
        """Load sample data để kiểm tra nhanh"""
        file_path = self.data_path / table_name / f"{table_name}.csv"
        try:
            df = pd.read_csv(file_path, nrows=nrows)
            logger.info(f"📊 Loaded {len(df)} sample rows from {table_name}")
            return df
        except Exception as e:
            logger.error(f"❌ Error loading {table_name}: {e}")
            self.issues[table_name].append(f"Load error: {str(e)}")
            return pd.DataFrame()
    
    def analyze_columns(self, df: pd.DataFrame, table_name: str) -> Dict:
        """Phân tích cấu trúc columns"""
        analysis = {
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'missing_percentage': (df.isnull().sum() / len(df) * 100).round(2).to_dict()
        }
        
        # Tìm columns có nhiều missing values
        high_missing = {col: pct for col, pct in analysis['missing_percentage'].items() 
                       if pct > 50}
        if high_missing:
            self.issues[table_name].append(f"High missing values: {high_missing}")
        
        return analysis
    
    def check_duplicates(self, df: pd.DataFrame, table_name: str, key_columns: List[str]) -> int:
        """Kiểm tra duplicate records"""
        if not key_columns or not all(col in df.columns for col in key_columns):
            logger.warning(f"⚠️  {table_name}: Cannot check duplicates - key columns not found")
            return 0
        
        duplicates = df.duplicated(subset=key_columns, keep=False).sum()
        if duplicates > 0:
            logger.warning(f"⚠️  {table_name}: Found {duplicates} duplicate records")
            self.issues[table_name].append(f"Duplicates: {duplicates}")
        else:
            logger.info(f"✅ {table_name}: No duplicates found")
        
        return duplicates
    
    def check_data_types(self, df: pd.DataFrame, table_name: str, 
                        expected_types: Dict[str, str]) -> List[str]:
        """Kiểm tra data types có đúng schema không"""
        type_issues = []
        
        for col, expected_type in expected_types.items():
            if col not in df.columns:
                type_issues.append(f"Missing column: {col}")
                continue
            
            actual_type = str(df[col].dtype)
            
            # Check type compatibility
            if expected_type == 'int' and 'int' not in actual_type:
                type_issues.append(f"{col}: expected int, got {actual_type}")
            elif expected_type == 'float' and 'float' not in actual_type and 'int' not in actual_type:
                type_issues.append(f"{col}: expected float, got {actual_type}")
            elif expected_type == 'date' and actual_type != 'object':
                # Dates usually loaded as object/string first
                pass
        
        if type_issues:
            self.issues[table_name].extend(type_issues)
        
        return type_issues
    
    def check_player_profiles(self):
        """Kiểm tra player_profiles table"""
        logger.info("\n" + "="*60)
        logger.info("🔍 Checking: PLAYER_PROFILES")
        logger.info("="*60)
        
        table_name = "player_profiles"
        if not self.check_file_exists(table_name):
            return
        
        df = self.load_sample(table_name, nrows=5000)
        if df.empty:
            return
        
        # Analyze structure
        analysis = self.analyze_columns(df, table_name)
        self.report[table_name]['row_count'] = len(df)
        self.report[table_name]['columns'] = analysis['columns']
        
        # Check key columns
        required_cols = ['player_id', 'player_slug', 'player_name']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"❌ Missing required columns: {missing_cols}")
            self.issues[table_name].append(f"Missing columns: {missing_cols}")
        
        # Check duplicates on player_id (PK)
        self.check_duplicates(df, table_name, ['player_id'])
        
        # Check data quality
        if 'height' in df.columns:
            invalid_heights = df[df['height'] < 140].shape[0]  # height < 140cm unusual
            if invalid_heights > 0:
                logger.warning(f"⚠️  Found {invalid_heights} unusual heights")
        
        if 'date_of_birth' in df.columns:
            # Check for future dates or very old dates
            try:
                df['dob_parsed'] = pd.to_datetime(df['date_of_birth'], errors='coerce')
                future_dates = df[df['dob_parsed'] > pd.Timestamp.now()].shape[0]
                very_old = df[df['dob_parsed'] < pd.Timestamp('1930-01-01')].shape[0]
                
                if future_dates > 0:
                    logger.warning(f"⚠️  Found {future_dates} future birth dates")
                if very_old > 0:
                    logger.warning(f"⚠️  Found {very_old} very old birth dates (before 1930)")
            except Exception as e:
                logger.warning(f"⚠️  Cannot parse dates: {e}")
        
        logger.info(f"✅ player_profiles check complete - {len(df)} rows analyzed")
    
    def check_player_performances(self):
        """Kiểm tra player_performances table"""
        logger.info("\n" + "="*60)
        logger.info("🔍 Checking: PLAYER_PERFORMANCES")
        logger.info("="*60)
        
        table_name = "player_performances"
        if not self.check_file_exists(table_name):
            return
        
        df = self.load_sample(table_name, nrows=10000)
        if df.empty:
            return
        
        analysis = self.analyze_columns(df, table_name)
        self.report[table_name]['row_count'] = len(df)
        
        # Check for negative values in stats
        numeric_cols = ['goals', 'assists', 'minutes_played', 'yellow_cards', 'red_cards']
        for col in numeric_cols:
            if col in df.columns:
                negative_count = df[df[col] < 0].shape[0]
                if negative_count > 0:
                    logger.warning(f"⚠️  {col}: Found {negative_count} negative values")
                    self.issues[table_name].append(f"{col} has negative values")
        
        # Check logical constraints
        if 'goals' in df.columns and 'penalty_goals' in df.columns:
            invalid = df[df['penalty_goals'] > df['goals']].shape[0]
            if invalid > 0:
                logger.warning(f"⚠️  {invalid} records: penalty_goals > total goals")
        
        if 'yellow_cards' in df.columns and 'second_yellow_cards' in df.columns:
            invalid = df[df['second_yellow_cards'] > df['yellow_cards']].shape[0]
            if invalid > 0:
                logger.warning(f"⚠️  {invalid} records: second_yellow > yellow_cards")
        
        logger.info(f"✅ player_performances check complete")
    
    def check_player_market_values(self):
        """Kiểm tra player_market_value table"""
        logger.info("\n" + "="*60)
        logger.info("🔍 Checking: PLAYER_MARKET_VALUE")
        logger.info("="*60)
        
        table_name = "player_market_value"
        if not self.check_file_exists(table_name):
            return
        
        df = self.load_sample(table_name, nrows=10000)
        if df.empty:
            return
        
        analysis = self.analyze_columns(df, table_name)
        self.report[table_name]['row_count'] = len(df)
        
        # Check market values
        if 'value' in df.columns:
            zero_values = df[df['value'] == 0].shape[0]
            negative_values = df[df['value'] < 0].shape[0]
            
            if zero_values > len(df) * 0.5:
                logger.warning(f"⚠️  {zero_values} records with zero market value ({zero_values/len(df)*100:.1f}%)")
            
            if negative_values > 0:
                logger.error(f"❌ {negative_values} records with negative market value")
                self.issues[table_name].append("Negative market values found")
            
            # Show value distribution
            logger.info(f"📊 Market value stats: min={df['value'].min():,.0f}, max={df['value'].max():,.0f}, mean={df['value'].mean():,.0f}")
        
        logger.info(f"✅ player_market_value check complete")
    
    def check_player_injuries(self):
        """Kiểm tra player_injuries table"""
        logger.info("\n" + "="*60)
        logger.info("🔍 Checking: PLAYER_INJURIES")
        logger.info("="*60)
        
        table_name = "player_injuries"
        if not self.check_file_exists(table_name):
            return
        
        df = self.load_sample(table_name, nrows=10000)
        if df.empty:
            return
        
        analysis = self.analyze_columns(df, table_name)
        self.report[table_name]['row_count'] = len(df)
        
        # Check date logic
        if 'from_date' in df.columns and 'end_date' in df.columns:
            try:
                df['from_parsed'] = pd.to_datetime(df['from_date'], errors='coerce')
                df['end_parsed'] = pd.to_datetime(df['end_date'], errors='coerce')
                
                invalid_dates = df[df['end_parsed'] < df['from_parsed']].shape[0]
                if invalid_dates > 0:
                    logger.warning(f"⚠️  {invalid_dates} records: end_date < from_date")
                    self.issues[table_name].append("Invalid date ranges")
            except Exception as e:
                logger.warning(f"⚠️  Cannot parse dates: {e}")
        
        # Check days_missed vs games_missed
        if 'days_missed' in df.columns:
            negative_days = df[df['days_missed'] < 0].shape[0]
            if negative_days > 0:
                logger.warning(f"⚠️  {negative_days} records with negative days_missed")
        
        logger.info(f"✅ player_injuries check complete")
    
    def check_transfer_history(self):
        """Kiểm tra transfer_history table"""
        logger.info("\n" + "="*60)
        logger.info("🔍 Checking: TRANSFER_HISTORY")
        logger.info("="*60)
        
        table_name = "transfer_history"
        if not self.check_file_exists(table_name):
            return
        
        df = self.load_sample(table_name, nrows=10000)
        if df.empty:
            return
        
        analysis = self.analyze_columns(df, table_name)
        self.report[table_name]['row_count'] = len(df)
        
        # Check transfer logic
        if 'from_team_id' in df.columns and 'to_team_id' in df.columns:
            same_team = df[df['from_team_id'] == df['to_team_id']].shape[0]
            if same_team > 0:
                logger.warning(f"⚠️  {same_team} records: from_team = to_team")
        
        # Check transfer fees
        if 'transfer_fee' in df.columns:
            negative_fees = df[df['transfer_fee'] < 0].shape[0]
            if negative_fees > 0:
                logger.warning(f"⚠️  {negative_fees} records with negative transfer_fee")
            
            free_transfers = df[df['transfer_fee'] == 0].shape[0]
            logger.info(f"📊 Free transfers: {free_transfers} ({free_transfers/len(df)*100:.1f}%)")
        
        logger.info(f"✅ transfer_history check complete")
    
    def check_team_details(self):
        """Kiểm tra team_details table"""
        logger.info("\n" + "="*60)
        logger.info("🔍 Checking: TEAM_DETAILS")
        logger.info("="*60)
        
        table_name = "team_details"
        if not self.check_file_exists(table_name):
            return
        
        df = self.load_sample(table_name, nrows=5000)
        if df.empty:
            return
        
        analysis = self.analyze_columns(df, table_name)
        self.report[table_name]['row_count'] = len(df)
        
        # Check duplicates on club_id (PK)
        self.check_duplicates(df, table_name, ['club_id'])
        
        # Show country distribution
        if 'country_name' in df.columns:
            top_countries = df['country_name'].value_counts().head(10)
            logger.info(f"📊 Top 10 countries:\n{top_countries}")
        
        logger.info(f"✅ team_details check complete")
    
    def generate_report(self) -> str:
        """Tạo báo cáo tổng hợp"""
        logger.info("\n" + "="*60)
        logger.info("📋 GENERATING DATA QUALITY REPORT")
        logger.info("="*60)
        
        report_lines = []
        report_lines.append("="*80)
        report_lines.append("DATA QUALITY REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("="*80)
        report_lines.append("")
        
        # Summary
        total_tables = len(self.report)
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        report_lines.append(f"📊 SUMMARY:")
        report_lines.append(f"  - Tables checked: {total_tables}")
        report_lines.append(f"  - Total issues found: {total_issues}")
        report_lines.append("")
        
        # Table details
        for table, data in self.report.items():
            report_lines.append(f"\n📁 {table.upper()}")
            report_lines.append("-" * 60)
            
            if 'file_size_mb' in data:
                report_lines.append(f"  File size: {data['file_size_mb']:.2f} MB")
            if 'row_count' in data:
                report_lines.append(f"  Sample rows: {data['row_count']:,}")
            if 'columns' in data:
                report_lines.append(f"  Columns: {len(data['columns'])}")
                report_lines.append(f"  Column names: {', '.join(data['columns'][:10])}{'...' if len(data['columns']) > 10 else ''}")
            
            # Issues
            if table in self.issues and self.issues[table]:
                report_lines.append(f"\n  ⚠️  ISSUES FOUND:")
                for issue in self.issues[table]:
                    report_lines.append(f"    - {issue}")
            else:
                report_lines.append(f"  ✅ No major issues detected")
        
        report_lines.append("\n" + "="*80)
        report_lines.append("END OF REPORT")
        report_lines.append("="*80)
        
        report_text = "\n".join(report_lines)
        
        # Save to file in reports directory
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = report_dir / f"data_quality_report_{timestamp}.txt"
        report_path.write_text(report_text)
        logger.info(f"💾 Report saved to: {report_path.absolute()}")
        
        return report_text
    
    def run_full_check(self):
        """Chạy kiểm tra đầy đủ tất cả tables"""
        logger.info("🚀 Starting full data quality check...")
        logger.info(f"📂 Data path: {self.data_path.absolute()}")
        
        try:
            self.check_player_profiles()
            self.check_player_performances()
            self.check_player_market_values()
            self.check_player_injuries()
            self.check_transfer_history()
            self.check_team_details()
            
            # Generate final report
            report = self.generate_report()
            print("\n" + report)
            
            logger.info("\n✅ Data quality check complete!")
            
            # Summary of issues
            total_issues = sum(len(issues) for issues in self.issues.values())
            if total_issues > 0:
                logger.warning(f"⚠️  Total {total_issues} issues found - please review report")
            else:
                logger.info("🎉 No critical issues found - data quality looks good!")
            
        except Exception as e:
            logger.error(f"❌ Error during quality check: {e}")
            raise


def main():
    """Main entry point"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║         DATA QUALITY CHECK & CLEANING                      ║
    ║         Football Transfermarkt Dataset                     ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize checker
    checker = DataQualityChecker()
    
    # Run full check
    checker.run_full_check()


if __name__ == "__main__":
    main()
