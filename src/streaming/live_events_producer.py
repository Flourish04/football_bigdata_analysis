#!/usr/bin/env python3
"""
Live Match Events Producer
Fetches live match data from Football-Data.org API
Sends to Kafka topic for real-time processing
"""

import requests
import json
import time
import logging
import os
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "https://api.football-data.org/v4"
API_TOKEN = os.getenv('FOOTBALL_API_TOKEN', '798a49800fe84474bc7858ca06434966')
API_HEADERS = {"X-Auth-Token": API_TOKEN}

# Confluent Cloud Kafka Configuration
KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'pkc-xxxxx.region.provider.confluent.cloud:9092'),
    'sasl_mechanism': 'PLAIN',
    'security_protocol': 'SASL_SSL',
    'sasl_username': os.getenv('KAFKA_API_KEY', 'your-api-key'),
    'sasl_password': os.getenv('KAFKA_API_SECRET', 'your-api-secret'),
}
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'live-match-events')

# Polling intervals
LIVE_MATCH_INTERVAL = 30  # 30 seconds for live matches
SCHEDULED_MATCH_INTERVAL = 1800  # 30 minutes for scheduled matches
API_RATE_LIMIT_WAIT = 6  # 6 seconds between API calls (10 req/min = 1 per 6s)


class LiveMatchProducer:
    """Fetch live matches and produce to Kafka"""
    
    def __init__(self):
        """Initialize Kafka producer and API client for Confluent Cloud"""
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
            security_protocol=KAFKA_CONFIG['security_protocol'],
            sasl_mechanism=KAFKA_CONFIG['sasl_mechanism'],
            sasl_plain_username=KAFKA_CONFIG['sasl_username'],
            sasl_plain_password=KAFKA_CONFIG['sasl_password'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            compression_type='gzip',
            retries=3,
            acks='all'
        )
        logger.info("✅ Kafka producer initialized (Confluent Cloud)")
    
    def fetch_live_matches(self):
        """Fetch currently live matches from API"""
        try:
            url = f"{API_BASE_URL}/matches"
            params = {
                'status': 'IN_PLAY'  # Only live matches
            }
            
            response = requests.get(url, headers=API_HEADERS, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                logger.info(f"📡 Fetched {len(matches)} live matches")
                return matches
            elif response.status_code == 429:
                logger.warning("⚠️  Rate limit exceeded, waiting...")
                time.sleep(60)
                return []
            else:
                logger.error(f"❌ API error: {response.status_code} - {response.text}")
                return []
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return []
    
    def fetch_scheduled_matches(self):
        """Fetch scheduled matches for next 24 hours"""
        try:
            url = f"{API_BASE_URL}/matches"
            params = {
                'status': 'TIMED'  # Scheduled matches
            }
            
            response = requests.get(url, headers=API_HEADERS, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                logger.info(f"📅 Fetched {len(matches)} scheduled matches")
                return matches
            else:
                logger.warning(f"⚠️  Scheduled matches API: {response.status_code}")
                return []
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Scheduled matches request failed: {e}")
            return []
    
    def transform_match_data(self, match):
        """Transform API match data to our event format"""
        try:
            event = {
                'match_id': str(match.get('id')),
                'timestamp': datetime.utcnow().isoformat(),
                'status': match.get('status'),
                'utc_date': match.get('utcDate'),
                'minute': match.get('minute'),
                
                # Competition
                'competition_name': match.get('competition', {}).get('name'),
                'competition_code': match.get('competition', {}).get('code'),
                
                # Teams
                'home_team_id': match.get('homeTeam', {}).get('id'),
                'home_team_name': match.get('homeTeam', {}).get('name'),
                'home_team_short': match.get('homeTeam', {}).get('shortName'),
                'away_team_id': match.get('awayTeam', {}).get('id'),
                'away_team_name': match.get('awayTeam', {}).get('name'),
                'away_team_short': match.get('awayTeam', {}).get('shortName'),
                
                # Score
                'home_score': match.get('score', {}).get('fullTime', {}).get('home'),
                'away_score': match.get('score', {}).get('fullTime', {}).get('away'),
                'half_time_home': match.get('score', {}).get('halfTime', {}).get('home'),
                'half_time_away': match.get('score', {}).get('halfTime', {}).get('away'),
                
                # Venue
                'venue': match.get('venue'),
                
                # Referees
                'referees': [ref.get('name') for ref in match.get('referees', [])],
                
                # Raw data for later processing
                'raw_data': match
            }
            
            return event
        
        except Exception as e:
            logger.error(f"❌ Transform error: {e}")
            return None
    
    def send_to_kafka(self, events):
        """Send events to Kafka topic"""
        if not events:
            return
        
        sent_count = 0
        for event in events:
            try:
                match_id = event.get('match_id')
                
                future = self.producer.send(
                    KAFKA_TOPIC,
                    key=match_id,
                    value=event
                )
                
                # Wait for send confirmation
                record_metadata = future.get(timeout=10)
                sent_count += 1
                
                logger.debug(f"✅ Sent match {match_id} to topic {record_metadata.topic} "
                           f"partition {record_metadata.partition} offset {record_metadata.offset}")
            
            except KafkaError as e:
                logger.error(f"❌ Kafka send error: {e}")
        
        logger.info(f"📤 Sent {sent_count}/{len(events)} events to Kafka")
    
    def run(self):
        """Main polling loop"""
        logger.info("="*80)
        logger.info("  LIVE MATCH EVENTS PRODUCER")
        logger.info(f"  Kafka: Confluent Cloud ({KAFKA_CONFIG['bootstrap_servers']})")
        logger.info(f"  Topic: {KAFKA_TOPIC}")
        logger.info(f"  API: Football-Data.org")
        logger.info("="*80)
        
        last_scheduled_check = 0
        
        try:
            while True:
                start_time = time.time()
                
                # 1. Fetch live matches (every cycle)
                logger.info(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Checking live matches...")
                live_matches = self.fetch_live_matches()
                
                if live_matches:
                    events = [self.transform_match_data(m) for m in live_matches]
                    events = [e for e in events if e is not None]
                    self.send_to_kafka(events)
                else:
                    logger.info("   No live matches currently")
                
                # 2. Fetch scheduled matches (every 30 minutes)
                current_time = time.time()
                if current_time - last_scheduled_check > SCHEDULED_MATCH_INTERVAL:
                    logger.info("📅 Checking scheduled matches...")
                    time.sleep(API_RATE_LIMIT_WAIT)  # Rate limiting
                    
                    scheduled = self.fetch_scheduled_matches()
                    if scheduled:
                        events = [self.transform_match_data(m) for m in scheduled]
                        events = [e for e in events if e is not None]
                        self.send_to_kafka(events)
                    
                    last_scheduled_check = current_time
                
                # 3. Wait before next cycle
                elapsed = time.time() - start_time
                wait_time = max(LIVE_MATCH_INTERVAL - elapsed, API_RATE_LIMIT_WAIT)
                
                logger.info(f"⏳ Waiting {wait_time:.1f}s before next check...\n")
                time.sleep(wait_time)
        
        except KeyboardInterrupt:
            logger.info("\n🛑 Producer stopped by user")
        
        except Exception as e:
            logger.error(f"❌ Producer error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.close()
    
    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("✅ Kafka producer closed")


def main():
    """Main execution"""
    producer = LiveMatchProducer()
    producer.run()


if __name__ == "__main__":
    main()
