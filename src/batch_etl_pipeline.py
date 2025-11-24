"""
Batch ETL Pipeline for Football Data
Loads historical data from CSV and processes using PySpark
"""

import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, avg, sum as spark_sum, count, 
    datediff, current_date, lag, lead, row_number,
    dense_rank, year, month, dayofmonth
)
from pyspark.sql.window import Window

# Configuration
DATA_PATH = '/home/hung/Downloads/bigdata/football_project/football-datasets/datalake/transfermarkt'
OUTPUT_PATH = '/tmp/football_processed'
POSTGRES_URL = 'jdbc:postgresql://localhost:5432/football_analytics'
POSTGRES_USER = 'football_user'
POSTGRES_PASSWORD = 'football_pass'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session for batch processing"""
    spark = SparkSession.builder \
        .appName("Football Analytics Batch ETL") \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.executor.memory", "4g") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info("Spark session created for batch processing")
    return spark


def load_player_profiles(spark):
    """Load player profiles data"""
    df = spark.read.csv(
        f'{DATA_PATH}/player_profiles/player_profiles.csv',
        header=True,
        inferSchema=True
    )
    logger.info(f"Loaded {df.count()} player profiles")
    return df


def load_player_performances(spark):
    """Load player performances data"""
    df = spark.read.csv(
        f'{DATA_PATH}/player_performances/player_performances.csv',
        header=True,
        inferSchema=True
    )
    logger.info(f"Loaded {df.count()} player performances")
    return df


def load_player_market_values(spark):
    """Load player market values"""
    df = spark.read.csv(
        f'{DATA_PATH}/player_market_value/player_market_value.csv',
        header=True,
        inferSchema=True
    )
    logger.info(f"Loaded {df.count()} market value records")
    return df


def load_transfer_history(spark):
    """Load transfer history"""
    df = spark.read.csv(
        f'{DATA_PATH}/transfer_history/transfer_history.csv',
        header=True,
        inferSchema=True
    )
    logger.info(f"Loaded {df.count()} transfer records")
    return df


def load_injuries(spark):
    """Load injury history"""
    df = spark.read.csv(
        f'{DATA_PATH}/player_injuries/player_injuries.csv',
        header=True,
        inferSchema=True
    )
    logger.info(f"Loaded {df.count()} injury records")
    return df


def clean_player_profiles(df):
    """Clean and transform player profiles"""
    cleaned_df = df \
        .dropDuplicates(['player_id']) \
        .na.fill({
            'height': '0',
            'position': 'Unknown',
            'foot': 'Unknown'
        })
    
    logger.info("Player profiles cleaned")
    return cleaned_df


def calculate_player_form(performances_df):
    """Calculate player form (last 5 games average)"""
    window_spec = Window.partitionBy('player_id').orderBy('season')
    
    form_df = performances_df \
        .withColumn('goals_int', col('goals').cast('int')) \
        .withColumn('assists_int', col('assists').cast('int')) \
        .withColumn('row_num', row_number().over(window_spec)) \
        .groupBy('player_id') \
        .agg(
            avg('goals_int').alias('avg_goals'),
            avg('assists_int').alias('avg_assists'),
            spark_sum('goals_int').alias('total_goals'),
            spark_sum('assists_int').alias('total_assists'),
            count('*').alias('matches_played')
        )
    
    logger.info("Player form calculated")
    return form_df


def calculate_market_value_trends(market_values_df):
    """Calculate market value trends"""
    window_spec = Window.partitionBy('player_id').orderBy('date_unix')
    
    trends_df = market_values_df \
        .withColumn('prev_value', lag('value').over(window_spec)) \
        .withColumn('value_change', col('value') - col('prev_value')) \
        .withColumn('value_change_pct', 
                   (col('value_change') / col('prev_value')) * 100) \
        .withColumn('trend', 
                   when(col('value_change') > 0, 'increasing')
                   .when(col('value_change') < 0, 'decreasing')
                   .otherwise('stable'))
    
    logger.info("Market value trends calculated")
    return trends_df


def calculate_injury_risk(injuries_df):
    """Calculate injury risk scores"""
    risk_df = injuries_df \
        .withColumn('days_missed_int', col('days_missed').cast('int')) \
        .withColumn('games_missed_int', col('games_missed').cast('int')) \
        .groupBy('player_id') \
        .agg(
            count('*').alias('total_injuries'),
            spark_sum('days_missed_int').alias('total_days_missed'),
            spark_sum('games_missed_int').alias('total_games_missed'),
            avg('days_missed_int').alias('avg_days_missed')
        ) \
        .withColumn('injury_risk_score',
                   (col('total_injuries') * 10 + 
                    col('total_days_missed') / 10) / 100)
    
    logger.info("Injury risk scores calculated")
    return risk_df


def create_player_analytics(profiles_df, form_df, market_df, injury_df):
    """Create comprehensive player analytics"""
    analytics_df = profiles_df \
        .join(form_df, 'player_id', 'left') \
        .join(
            market_df.groupBy('player_id').agg(
                avg('value').alias('avg_market_value'),
                max('value').alias('max_market_value')
            ),
            'player_id',
            'left'
        ) \
        .join(injury_df, 'player_id', 'left') \
        .select(
            'player_id',
            'player_name',
            col('Date of birth').alias('date_of_birth'),
            'Position',
            'Citizenship',
            'avg_goals',
            'avg_assists',
            'total_goals',
            'total_assists',
            'matches_played',
            'avg_market_value',
            'max_market_value',
            'total_injuries',
            'injury_risk_score'
        )
    
    logger.info("Player analytics created")
    return analytics_df


def write_to_postgres(df, table_name):
    """Write DataFrame to PostgreSQL"""
    try:
        df.write \
            .format("jdbc") \
            .option("url", POSTGRES_URL) \
            .option("dbtable", table_name) \
            .option("user", POSTGRES_USER) \
            .option("password", POSTGRES_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .mode("overwrite") \
            .save()
        
        logger.info(f"Data written to PostgreSQL table: {table_name}")
    except Exception as e:
        logger.error(f"Error writing to PostgreSQL: {e}")


def write_to_parquet(df, table_name):
    """Write DataFrame to Parquet files"""
    output_path = f"{OUTPUT_PATH}/{table_name}"
    
    df.write \
        .mode("overwrite") \
        .parquet(output_path)
    
    logger.info(f"Data written to Parquet: {output_path}")


def main():
    """Main ETL pipeline"""
    start_time = datetime.now()
    logger.info("Starting batch ETL pipeline")
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Load data
        logger.info("Loading data from CSV files...")
        profiles_df = load_player_profiles(spark)
        performances_df = load_player_performances(spark)
        market_values_df = load_player_market_values(spark)
        transfer_history_df = load_transfer_history(spark)
        injuries_df = load_injuries(spark)
        
        # Clean data
        logger.info("Cleaning data...")
        profiles_clean = clean_player_profiles(profiles_df)
        
        # Calculate metrics
        logger.info("Calculating metrics...")
        form_df = calculate_player_form(performances_df)
        market_trends_df = calculate_market_value_trends(market_values_df)
        injury_risk_df = calculate_injury_risk(injuries_df)
        
        # Create analytics
        logger.info("Creating player analytics...")
        player_analytics = create_player_analytics(
            profiles_clean,
            form_df,
            market_trends_df,
            injury_risk_df
        )
        
        # Show sample
        logger.info("Sample player analytics:")
        player_analytics.show(10, truncate=False)
        
        # Write outputs
        logger.info("Writing outputs...")
        write_to_parquet(player_analytics, "player_analytics")
        write_to_parquet(form_df, "player_form")
        write_to_parquet(market_trends_df, "market_value_trends")
        write_to_parquet(injury_risk_df, "injury_risk")
        
        # Optionally write to PostgreSQL
        # write_to_postgres(player_analytics, "player_analytics")
        
        # Success
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"ETL pipeline completed successfully in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
