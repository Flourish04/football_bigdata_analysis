#!/usr/bin/env python3
"""
Football Events Layer
Processes match events dataset: goals, shots, cards, substitutions
Integrates with existing player/team data
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, trim, lower, regexp_replace,
    count, sum as _sum, avg, max as _max, min as _min,
    to_timestamp, year, month, dayofmonth, to_date
)
from pyspark.sql.types import *
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventsLayer:
    """Process football match events data"""
    
    def __init__(self):
        """Initialize Spark session"""
        self.spark = SparkSession.builder \
            .appName('FootballEventsLayer') \
            .config('spark.driver.memory', '4g') \
            .config('spark.executor.memory', '4g') \
            .config('spark.sql.legacy.timeParserPolicy', 'LEGACY') \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel('WARN')
        
        # Paths
        self.events_csv_path = 'football-datasets/datalake/transfermarkt/football_events/events.csv'
        self.ginf_csv_path = 'football-datasets/datalake/transfermarkt/football_events/ginf.csv'
        self.output_path = '/tmp/football_datalake/events'
        
        logger.info("✅ Spark session initialized for Events Layer")
    
    def load_match_info(self):
        """Load match general information (ginf.csv)"""
        logger.info("📖 Loading match general information...")
        
        ginf_schema = StructType([
            StructField("id_odsp", StringType(), False),
            StructField("link_odsp", StringType(), True),
            StructField("adv_stats", BooleanType(), True),
            StructField("date", StringType(), True),
            StructField("league", StringType(), True),
            StructField("season", StringType(), True),
            StructField("country", StringType(), True),
            StructField("ht", StringType(), True),  # home team
            StructField("at", StringType(), True),  # away team
            StructField("fthg", IntegerType(), True),  # full time home goals
            StructField("ftag", IntegerType(), True),  # full time away goals
            StructField("odd_h", DoubleType(), True),  # home win odds
            StructField("odd_d", DoubleType(), True),  # draw odds
            StructField("odd_a", DoubleType(), True),  # away win odds
            StructField("odd_over", DoubleType(), True),
            StructField("odd_under", DoubleType(), True),
            StructField("odd_bts", DoubleType(), True),
            StructField("odd_bts_n", DoubleType(), True)
        ])
        
        df = self.spark.read \
            .option("header", "true") \
            .schema(ginf_schema) \
            .csv(self.ginf_csv_path)
        
        # Clean and transform
        df_clean = df \
            .withColumn("match_id", col("id_odsp")) \
            .withColumn("match_date", to_date(col("date"))) \
            .withColumn("home_team", trim(col("ht"))) \
            .withColumn("away_team", trim(col("at"))) \
            .withColumn("home_goals", col("fthg")) \
            .withColumn("away_goals", col("ftag")) \
            .withColumn("total_goals", col("fthg") + col("ftag")) \
            .withColumn("match_result",
                when(col("fthg") > col("ftag"), "HOME_WIN")
                .when(col("fthg") < col("ftag"), "AWAY_WIN")
                .otherwise("DRAW")
            ) \
            .withColumn("year", year("match_date")) \
            .withColumn("month", month("match_date")) \
            .select(
                "match_id", "match_date", "year", "month",
                "country", "league", "season",
                "home_team", "away_team",
                "home_goals", "away_goals", "total_goals", "match_result",
                "odd_h", "odd_d", "odd_a"
            )
        
        logger.info(f"✅ Loaded {df_clean.count():,} matches")
        return df_clean
    
    def load_match_events(self):
        """Load detailed match events (events.csv)"""
        logger.info("📖 Loading match events...")
        
        events_schema = StructType([
            StructField("id_odsp", StringType(), False),
            StructField("id_event", StringType(), True),
            StructField("sort_order", IntegerType(), True),
            StructField("time", IntegerType(), True),
            StructField("text", StringType(), True),
            StructField("event_type", IntegerType(), True),
            StructField("event_type2", IntegerType(), True),
            StructField("side", IntegerType(), True),
            StructField("event_team", StringType(), True),
            StructField("opponent", StringType(), True),
            StructField("player", StringType(), True),
            StructField("player2", StringType(), True),
            StructField("player_in", StringType(), True),
            StructField("player_out", StringType(), True),
            StructField("shot_place", IntegerType(), True),
            StructField("shot_outcome", IntegerType(), True),
            StructField("is_goal", IntegerType(), True),
            StructField("location", IntegerType(), True),
            StructField("bodypart", IntegerType(), True),
            StructField("assist_method", IntegerType(), True),
            StructField("situation", IntegerType(), True),
            StructField("fast_break", IntegerType(), True)
        ])
        
        df = self.spark.read \
            .option("header", "true") \
            .schema(events_schema) \
            .csv(self.events_csv_path)
        
        # Map event types to readable names
        df_clean = df \
            .withColumn("match_id", col("id_odsp")) \
            .withColumn("event_id", col("id_event")) \
            .withColumn("minute", col("time")) \
            .withColumn("event_type_name",
                when(col("event_type") == 0, "Announcement")
                .when(col("event_type") == 1, "Attempt")
                .when(col("event_type") == 2, "Corner")
                .when(col("event_type") == 3, "Foul")
                .when(col("event_type") == 4, "Yellow card")
                .when(col("event_type") == 5, "Second yellow")
                .when(col("event_type") == 6, "Red card")
                .when(col("event_type") == 7, "Substitution")
                .when(col("event_type") == 8, "Free kick won")
                .when(col("event_type") == 9, "Offside")
                .when(col("event_type") == 10, "Hand ball")
                .when(col("event_type") == 11, "Penalty")
                .otherwise("Unknown")
            ) \
            .withColumn("team_side",
                when(col("side") == 1, "HOME")
                .when(col("side") == 2, "AWAY")
                .otherwise("UNKNOWN")
            ) \
            .withColumn("shot_outcome_name",
                when(col("shot_outcome") == 1, "On target")
                .when(col("shot_outcome") == 2, "Off target")
                .when(col("shot_outcome") == 3, "Blocked")
                .when(col("shot_outcome") == 4, "Hit the bar")
                .otherwise(None)
            ) \
            .withColumn("bodypart_name",
                when(col("bodypart") == 1, "Right foot")
                .when(col("bodypart") == 2, "Left foot")
                .when(col("bodypart") == 3, "Head")
                .otherwise(None)
            ) \
            .withColumn("is_goal_flag", col("is_goal") == 1) \
            .withColumn("player_name", lower(trim(col("player")))) \
            .withColumn("assist_player", lower(trim(col("player2")))) \
            .select(
                "match_id", "event_id", "sort_order", "minute",
                "event_type", "event_type_name", "event_type2",
                "team_side", "event_team", "opponent",
                "player_name", "assist_player",
                "player_in", "player_out",
                "shot_place", "shot_outcome", "shot_outcome_name",
                "is_goal_flag", "location", "bodypart", "bodypart_name",
                "assist_method", "situation", "fast_break", "text"
            )
        
        logger.info(f"✅ Loaded {df_clean.count():,} events")
        return df_clean
    
    def aggregate_match_statistics(self, events_df):
        """Aggregate events by match to compute statistics"""
        logger.info("📊 Computing match-level statistics...")
        
        match_stats = events_df.groupBy("match_id").agg(
            # Goals
            _sum(when(col("is_goal_flag"), 1).otherwise(0)).alias("total_goals"),
            
            # Shots
            count(when(col("event_type") == 1, 1)).alias("total_shots"),
            count(when((col("event_type") == 1) & (col("shot_outcome") == 1), 1)).alias("shots_on_target"),
            count(when((col("event_type") == 1) & (col("shot_outcome") == 2), 1)).alias("shots_off_target"),
            count(when((col("event_type") == 1) & (col("shot_outcome") == 3), 1)).alias("shots_blocked"),
            
            # Set pieces
            count(when(col("event_type") == 2, 1)).alias("total_corners"),
            count(when(col("event_type") == 8, 1)).alias("free_kicks_won"),
            
            # Discipline
            count(when(col("event_type") == 4, 1)).alias("yellow_cards"),
            count(when(col("event_type") == 6, 1)).alias("red_cards"),
            count(when(col("event_type") == 3, 1)).alias("fouls"),
            
            # Other
            count(when(col("event_type") == 7, 1)).alias("substitutions"),
            count(when(col("event_type") == 9, 1)).alias("offsides")
        )
        
        # Calculate shooting accuracy
        match_stats = match_stats.withColumn(
            "shot_accuracy",
            when(col("total_shots") > 0,
                (col("shots_on_target") / col("total_shots") * 100).cast("decimal(5,2)")
            ).otherwise(0.0)
        )
        
        logger.info(f"✅ Computed statistics for {match_stats.count():,} matches")
        return match_stats
    
    def aggregate_player_statistics(self, events_df):
        """Aggregate events by player"""
        logger.info("📊 Computing player-level statistics from events...")
        
        player_stats = events_df \
            .filter(col("player_name").isNotNull()) \
            .groupBy("player_name").agg(
                # Appearances (matches played)
                count("match_id").alias("match_appearances"),
                
                # Goals
                _sum(when(col("is_goal_flag"), 1).otherwise(0)).alias("goals_scored"),
                
                # Assists
                count(when(col("assist_player").isNotNull(), 1)).alias("assists_provided"),
                
                # Shots
                count(when(col("event_type") == 1, 1)).alias("total_shots"),
                count(when((col("event_type") == 1) & (col("shot_outcome") == 1), 1)).alias("shots_on_target"),
                
                # Discipline
                count(when(col("event_type") == 4, 1)).alias("yellow_cards"),
                count(when(col("event_type") == 6, 1)).alias("red_cards"),
                count(when(col("event_type") == 3, 1)).alias("fouls_committed"),
                
                # Other
                count(when(col("event_type") == 9, 1)).alias("offsides")
            )
        
        # Calculate rates
        player_stats = player_stats \
            .withColumn("goals_per_match",
                when(col("match_appearances") > 0,
                    (col("goals_scored") / col("match_appearances")).cast("decimal(5,2)")
                ).otherwise(0.0)
            ) \
            .withColumn("shots_accuracy",
                when(col("total_shots") > 0,
                    (col("shots_on_target") / col("total_shots") * 100).cast("decimal(5,2)")
                ).otherwise(0.0)
            )
        
        logger.info(f"✅ Computed statistics for {player_stats.count():,} players")
        return player_stats
    
    def join_with_existing_players(self, events_player_stats):
        """Join event player stats with existing player profiles"""
        logger.info("🔗 Joining with existing player profiles...")
        
        # Load existing player profiles
        player_profiles = self.spark.read.parquet(
            "/tmp/football_datalake/silver/player_profiles"
        ).select(
            "player_id",
            "player_name",
            "position",
            "citizenship"
        )
        
        # Fuzzy match on player names (lowercase, trimmed)
        player_profiles = player_profiles.withColumn(
            "player_name_clean",
            lower(trim(col("player_name")))
        )
        
        events_player_stats = events_player_stats.withColumn(
            "player_name_clean",
            col("player_name")
        )
        
        joined = events_player_stats.join(
            player_profiles,
            on="player_name_clean",
            how="left"
        ).select(
            "player_id",
            "player_name",
            "position",
            "match_appearances",
            "goals_scored",
            "assists_provided",
            "total_shots",
            "shots_on_target",
            "shots_accuracy",
            "yellow_cards",
            "red_cards",
            "fouls_committed",
            "offsides",
            "goals_per_match"
        )
        
        matched = joined.filter(col("player_id").isNotNull()).count()
        total = joined.count()
        logger.info(f"✅ Matched {matched:,}/{total:,} players ({matched/total*100:.1f}%)")
        
        return joined
    
    def save_to_events_layer(self, match_info, match_stats, player_stats):
        """Save all processed data to Events layer"""
        logger.info("💾 Saving to Events layer...")
        
        # Match general info
        match_info.write \
            .mode('overwrite') \
            .parquet(f"{self.output_path}/match_info")
        logger.info(f"  ✅ match_info: {match_info.count():,} records")
        
        # Match statistics
        match_stats.write \
            .mode('overwrite') \
            .parquet(f"{self.output_path}/match_statistics")
        logger.info(f"  ✅ match_statistics: {match_stats.count():,} records")
        
        # Player statistics from events
        player_stats.write \
            .mode('overwrite') \
            .parquet(f"{self.output_path}/player_event_statistics")
        logger.info(f"  ✅ player_event_statistics: {player_stats.count():,} records")
        
        logger.info(f"✅ All data saved to {self.output_path}")
    
    def process_all(self):
        """Run complete Events layer processing"""
        start_time = datetime.now()
        
        logger.info("="*80)
        logger.info("  FOOTBALL EVENTS LAYER PROCESSING")
        logger.info("="*80)
        
        try:
            # 1. Load match info
            match_info = self.load_match_info()
            
            # 2. Load match events
            events = self.load_match_events()
            
            # 3. Aggregate match statistics
            match_stats = self.aggregate_match_statistics(events)
            
            # 4. Aggregate player statistics
            player_stats_raw = self.aggregate_player_statistics(events)
            
            # 5. Join with existing player data
            player_stats = self.join_with_existing_players(player_stats_raw)
            
            # 6. Save all to parquet
            self.save_to_events_layer(match_info, match_stats, player_stats)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info("="*80)
            logger.info("✅ EVENTS LAYER PROCESSING COMPLETED")
            logger.info(f"⏱️  Duration: {duration:.2f}s")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        logger.info("🛑 Spark session stopped")


def main():
    """Main execution"""
    events_layer = EventsLayer()
    try:
        events_layer.process_all()
    finally:
        events_layer.stop()


if __name__ == "__main__":
    main()
