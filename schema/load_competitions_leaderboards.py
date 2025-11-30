#!/usr/bin/env python3
"""
Load Competitions and Leaderboards JSON data to PostgreSQL
File: schema/load_competitions_leaderboards.py
Date: November 28, 2025
"""

import os
import json
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'football_analytics'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD')
}

# Data paths
BASE_PATH = Path(__file__).parent.parent
COMPETITIONS_FILE = BASE_PATH / 'football-datasets/datalake/transfermarkt/competitions/competitions.json'
LEADERBOARDS_DIR = BASE_PATH / 'football-datasets/datalake/transfermarkt/leaderboards'


def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        raise


def load_competitions(conn, file_path):
    """Load competitions data from JSON file"""
    print(f"\n📊 Loading competitions from {file_path}")
    
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return 0
    
    # Read JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    competitions = data.get('competitions', [])
    if not competitions:
        print("⚠️  No competitions found in file")
        return 0
    
    print(f"   Found {len(competitions)} competitions")
    
    # Prepare data for insertion
    competition_records = []
    for comp in competitions:
        area = comp.get('area', {})
        current_season = comp.get('currentSeason', {})
        
        record = (
            comp.get('id'),
            comp.get('name'),
            comp.get('code'),
            comp.get('type'),
            comp.get('emblem'),
            comp.get('plan'),
            # Area
            area.get('id'),
            area.get('name'),
            area.get('code'),
            area.get('flag'),
            # Current season
            current_season.get('id'),
            current_season.get('startDate'),
            current_season.get('endDate'),
            current_season.get('currentMatchday'),
            current_season.get('winner', {}).get('id') if current_season.get('winner') else None,
            current_season.get('winner', {}).get('name') if current_season.get('winner') else None,
            # Metadata
            comp.get('numberOfAvailableSeasons'),
            comp.get('lastUpdated')
        )
        competition_records.append(record)
    
    # Insert into database
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO streaming.competitions (
            competition_id, competition_name, competition_code, competition_type,
            emblem_url, plan,
            area_id, area_name, area_code, area_flag_url,
            current_season_id, season_start_date, season_end_date, current_matchday,
            season_winner_id, season_winner_name,
            number_of_available_seasons, last_updated
        ) VALUES %s
        ON CONFLICT (competition_id) DO UPDATE SET
            competition_name = EXCLUDED.competition_name,
            competition_code = EXCLUDED.competition_code,
            competition_type = EXCLUDED.competition_type,
            emblem_url = EXCLUDED.emblem_url,
            plan = EXCLUDED.plan,
            area_id = EXCLUDED.area_id,
            area_name = EXCLUDED.area_name,
            area_code = EXCLUDED.area_code,
            area_flag_url = EXCLUDED.area_flag_url,
            current_season_id = EXCLUDED.current_season_id,
            season_start_date = EXCLUDED.season_start_date,
            season_end_date = EXCLUDED.season_end_date,
            current_matchday = EXCLUDED.current_matchday,
            season_winner_id = EXCLUDED.season_winner_id,
            season_winner_name = EXCLUDED.season_winner_name,
            number_of_available_seasons = EXCLUDED.number_of_available_seasons,
            last_updated = EXCLUDED.last_updated,
            processed_at = CURRENT_TIMESTAMP
    """
    
    execute_values(cursor, insert_query, competition_records)
    conn.commit()
    
    rows_affected = cursor.rowcount
    cursor.close()
    
    print(f"✅ Loaded {rows_affected} competitions")
    return rows_affected


def load_leaderboards(conn, leaderboards_dir):
    """Load leaderboards data from JSON files"""
    print(f"\n📊 Loading leaderboards from {leaderboards_dir}")
    
    if not leaderboards_dir.exists():
        print(f"⚠️  Directory not found: {leaderboards_dir}")
        return 0
    
    # Find all leaderboard JSON files
    leaderboard_files = sorted(list(leaderboards_dir.glob('*.json')))
    
    if not leaderboard_files:
        print("⚠️  No leaderboard files found")
        return 0
    
    print(f"   Found {len(leaderboard_files)} leaderboard file(s)")
    
    total_records = 0
    cursor = conn.cursor()
    
    for file_path in leaderboard_files:
        print(f"   Processing {file_path.name}...")
        
        # Read JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        area = data.get('area', {})
        competition = data.get('competition', {})
        season = data.get('season', {})
        standings = data.get('standings', [])
        
        if not standings:
            print(f"      ⚠️  No standings found in {file_path.name}")
            continue
        
        # Prepare data for insertion
        leaderboard_records = []
        
        for standing in standings:
            stage = standing.get('stage')
            standing_type = standing.get('type')
            group_name = standing.get('group')
            table = standing.get('table', [])
            
            for entry in table:
                team = entry.get('team', {})
                
                # Skip entries with null team_id (placeholder data for future tournaments)
                team_id = team.get('id')
                if team_id is None:
                    continue
                
                record = (
                    # Competition
                    competition.get('id'),
                    competition.get('name'),
                    competition.get('code'),
                    competition.get('type'),
                    # Season
                    season.get('id'),
                    season.get('startDate'),
                    season.get('endDate'),
                    season.get('currentMatchday'),
                    # Area
                    area.get('id'),
                    area.get('name'),
                    area.get('code'),
                    # Standing details
                    stage,
                    standing_type,
                    group_name,
                    # Team position
                    entry.get('position'),
                    team_id,
                    team.get('name'),
                    team.get('shortName'),
                    team.get('tla'),
                    team.get('crest'),
                    # Statistics
                    entry.get('playedGames', 0),
                    entry.get('won', 0),
                    entry.get('draw', 0),
                    entry.get('lost', 0),
                    entry.get('points', 0),
                    entry.get('goalsFor', 0),
                    entry.get('goalsAgainst', 0),
                    entry.get('goalDifference', 0),
                    entry.get('form')
                )
                leaderboard_records.append(record)
        
        if not leaderboard_records:
            print(f"      ⚠️  No records extracted from {file_path.name}")
            continue
        
        # Insert into database
        insert_query = """
            INSERT INTO streaming.leaderboards (
                competition_id, competition_name, competition_code, competition_type,
                season_id, season_start_date, season_end_date, current_matchday,
                area_id, area_name, area_code,
                stage, standing_type, group_name,
                position, team_id, team_name, team_short_name, team_tla, team_crest_url,
                played_games, won, draw, lost, points,
                goals_for, goals_against, goal_difference, form
            ) VALUES %s
            ON CONFLICT (competition_id, season_id, stage, standing_type, team_id, COALESCE(group_name, ''))
            DO UPDATE SET
                position = EXCLUDED.position,
                team_name = EXCLUDED.team_name,
                team_short_name = EXCLUDED.team_short_name,
                team_tla = EXCLUDED.team_tla,
                team_crest_url = EXCLUDED.team_crest_url,
                played_games = EXCLUDED.played_games,
                won = EXCLUDED.won,
                draw = EXCLUDED.draw,
                lost = EXCLUDED.lost,
                points = EXCLUDED.points,
                goals_for = EXCLUDED.goals_for,
                goals_against = EXCLUDED.goals_against,
                goal_difference = EXCLUDED.goal_difference,
                form = EXCLUDED.form,
                current_matchday = EXCLUDED.current_matchday,
                processed_at = CURRENT_TIMESTAMP
        """
        
        execute_values(cursor, insert_query, leaderboard_records)
        conn.commit()
        
        rows_affected = cursor.rowcount
        total_records += rows_affected
        
        print(f"      ✅ Loaded {rows_affected} leaderboard entries from {file_path.name}")
    
    cursor.close()
    
    print(f"✅ Total loaded: {total_records} leaderboard entries")
    return total_records


def create_schema_if_not_exists(conn):
    """Create streaming schema and tables if they don't exist"""
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'streaming' 
        AND table_name IN ('competitions', 'leaderboards')
    """)
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    if 'competitions' in existing_tables and 'leaderboards' in existing_tables:
        print("✅ Schema and tables already exist, skipping creation")
    else:
        print(f"⚠️  Missing tables. Please run: psql -f schema/streaming_competitions_leaderboards.sql")
        print(f"   Existing tables: {existing_tables}")
    
    cursor.close()


def refresh_materialized_views(conn):
    """Refresh materialized views"""
    print("\n🔄 Refreshing materialized views...")
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT streaming.refresh_competition_rankings()")
        conn.commit()
        print("✅ Materialized views refreshed")
    except Exception as e:
        conn.rollback()  # Rollback failed refresh to allow subsequent queries
        print(f"⚠️  Error refreshing materialized views: {e}")
        print("   (This is expected if views haven't been created yet)")
    finally:
        cursor.close()


def print_summary(conn):
    """Print data summary"""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("📊 DATA SUMMARY")
    print("="*70)
    
    # Competitions count
    cursor.execute("SELECT COUNT(*) FROM streaming.competitions")
    comp_count = cursor.fetchone()[0]
    print(f"   Competitions: {comp_count}")
    
    # Leaderboards count
    cursor.execute("SELECT COUNT(*) FROM streaming.leaderboards")
    lead_count = cursor.fetchone()[0]
    print(f"   Leaderboard entries: {lead_count}")
    
    # Teams count
    cursor.execute("SELECT COUNT(DISTINCT team_id) FROM streaming.leaderboards")
    team_count = cursor.fetchone()[0]
    print(f"   Unique teams: {team_count}")
    
    # Competition list
    print("\n📋 Loaded Competitions:")
    cursor.execute("""
        SELECT competition_code, competition_name, competition_type, area_name, current_matchday
        FROM streaming.competitions
        ORDER BY competition_name
    """)
    
    for row in cursor.fetchall():
        code, name, comp_type, area, matchday = row
        print(f"   • [{code}] {name} ({comp_type}) - {area} - Matchday {matchday}")
    
    print("\n" + "="*70)
    
    cursor.close()


def main():
    """Main execution function"""
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "LOAD COMPETITIONS & LEADERBOARDS" + " "*21 + "║")
    print("╚" + "="*68 + "╝")
    print(f"\n📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Connect to database
        print("\n🔌 Connecting to PostgreSQL...")
        conn = get_db_connection()
        print(f"✅ Connected to {DB_CONFIG['database']}@{DB_CONFIG['host']}")
        
        # Create schema if needed
        create_schema_if_not_exists(conn)
        
        # Load competitions
        comp_count = load_competitions(conn, COMPETITIONS_FILE)
        
        # Load leaderboards
        lead_count = load_leaderboards(conn, LEADERBOARDS_DIR)
        
        # Commit all data changes before trying views
        conn.commit()
        
        # Refresh materialized views (optional, may not exist yet)
        if comp_count > 0 or lead_count > 0:
            refresh_materialized_views(conn)
        
        # Print summary
        print_summary(conn)
        
        # Close connection
        conn.close()
        
        print("\n✅ COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
