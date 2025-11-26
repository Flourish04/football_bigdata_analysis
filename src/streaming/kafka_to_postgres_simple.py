"""
Simple Kafka to Postgres upsert script (without Spark).
Reads messages from Confluent Cloud Kafka and upserts into Postgres.

This is a simplified version for testing the full pipeline:
Kafka → Python Consumer → Postgres Upsert

Usage:
    python src/streaming/kafka_to_postgres_simple.py
    
Dependencies:
    pip install kafka-python psycopg2-binary
"""

import os
import json
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import Json
from datetime import datetime

def get_kafka_consumer():
    """Create Kafka consumer"""
    kafka_bootstrap = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'pkc-312o0.ap-southeast-1.aws.confluent.cloud:9092')
    kafka_api_key = os.environ.get('KAFKA_API_KEY', 'YXERA5PFM2TMAU6Z')
    kafka_api_secret = os.environ.get('KAFKA_API_SECRET', 'cfltpKodnfC/24wU7Amhzs/9yCcAFprLKnIj93/KgyYb1aV8NzefOCuvvnwXkKgg')
    kafka_topic = os.environ.get('KAFKA_TOPIC', 'live-match-events')
    
    return KafkaConsumer(
        kafka_topic,
        bootstrap_servers=kafka_bootstrap,
        security_protocol='SASL_SSL',
        sasl_mechanism='PLAIN',
        sasl_plain_username=kafka_api_key,
        sasl_plain_password=kafka_api_secret,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='python-upsert-consumer',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

def get_postgres_connection():
    """Create Postgres connection"""
    return psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'localhost'),
        port=os.environ.get('POSTGRES_PORT', '5432'),
        database=os.environ.get('POSTGRES_DB', 'football_analytics'),
        user=os.environ.get('POSTGRES_USER', 'postgres'),
        password=os.environ.get('POSTGRES_PASSWORD', '9281746356')
    )

def parse_datetime(dt_str):
    """Parse ISO datetime string"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return None

def upsert_match(conn, match_data):
    """Upsert a single match into Postgres"""
    cursor = conn.cursor()
    
    # Extract fields
    match_id = match_data.get('id')
    utc_date = parse_datetime(match_data.get('utcDate'))
    status = match_data.get('status')
    matchday = match_data.get('matchday')
    stage = match_data.get('stage')
    last_updated = parse_datetime(match_data.get('lastUpdated'))
    
    # Extract nested JSON objects
    area = Json(match_data.get('area', {}))
    competition = Json(match_data.get('competition', {}))
    season = Json(match_data.get('season', {}))
    home_team = Json(match_data.get('homeTeam', {}))
    away_team = Json(match_data.get('awayTeam', {}))
    
    # Extract score details
    score = match_data.get('score', {})
    winner = score.get('winner')
    duration = score.get('duration')
    full_time = score.get('fullTime', {})
    half_time = score.get('halfTime', {})
    
    ft_home_goals = full_time.get('home')
    ft_away_goals = full_time.get('away')
    ht_home_goals = half_time.get('home')
    ht_away_goals = half_time.get('away')
    
    # Store full raw JSON
    raw = Json(match_data)
    
    # Upsert query
    upsert_sql = """
    INSERT INTO public.football_matches 
        (match_id, utc_date, status, matchday, stage, last_updated, 
         area, competition, season, home_team, away_team, 
         winner, duration, ft_home_goals, ft_away_goals, 
         ht_home_goals, ht_away_goals, raw, processing_ts)
    VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
    ON CONFLICT (match_id) DO UPDATE SET
        utc_date = EXCLUDED.utc_date,
        status = EXCLUDED.status,
        matchday = EXCLUDED.matchday,
        stage = EXCLUDED.stage,
        last_updated = EXCLUDED.last_updated,
        area = EXCLUDED.area,
        competition = EXCLUDED.competition,
        season = EXCLUDED.season,
        home_team = EXCLUDED.home_team,
        away_team = EXCLUDED.away_team,
        winner = EXCLUDED.winner,
        duration = EXCLUDED.duration,
        ft_home_goals = EXCLUDED.ft_home_goals,
        ft_away_goals = EXCLUDED.ft_away_goals,
        ht_home_goals = EXCLUDED.ht_home_goals,
        ht_away_goals = EXCLUDED.ht_away_goals,
        raw = EXCLUDED.raw,
        processing_ts = now();
    """
    
    try:
        cursor.execute(upsert_sql, (
            match_id, utc_date, status, matchday, stage, last_updated,
            area, competition, season, home_team, away_team,
            winner, duration, ft_home_goals, ft_away_goals,
            ht_home_goals, ht_away_goals, raw
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error upserting match {match_id}: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

def main():
    print("🚀 Starting Kafka to Postgres pipeline...")
    print()
    
    # Connect to Kafka
    print("🔗 Connecting to Kafka...")
    consumer = get_kafka_consumer()
    print("✅ Connected to Kafka")
    
    # Connect to Postgres
    print("🔗 Connecting to Postgres...")
    conn = get_postgres_connection()
    print("✅ Connected to Postgres")
    print()
    
    print("📊 Reading messages from Kafka and upserting to Postgres...")
    print("Press Ctrl+C to stop")
    print("="*80)
    print()
    
    message_count = 0
    upsert_count = 0
    
    try:
        for message in consumer:
            message_count += 1
            match_data = message.value
            match_id = match_data.get('id')
            status = match_data.get('status')
            home_team = match_data.get('homeTeam', {}).get('name', 'Unknown')
            away_team = match_data.get('awayTeam', {}).get('name', 'Unknown')
            
            print(f"📨 Message #{message_count}: Match {match_id}")
            print(f"   {home_team} vs {away_team} ({status})")
            
            # Upsert to Postgres
            if upsert_match(conn, match_data):
                upsert_count += 1
                print(f"   ✅ Upserted successfully")
            else:
                print(f"   ❌ Failed to upsert")
            
            print()
            
            # Stop after 10 messages for testing
            if message_count >= 10:
                print(f"💡 Processed {message_count} messages for testing")
                break
                
    except KeyboardInterrupt:
        print("\n⚠️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        consumer.close()
        conn.close()
        print()
        print(f"📊 Summary:")
        print(f"   Total messages: {message_count}")
        print(f"   Successful upserts: {upsert_count}")
        print()
        print("✅ Pipeline completed!")

if __name__ == '__main__':
    main()
