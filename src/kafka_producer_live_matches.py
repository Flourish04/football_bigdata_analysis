"""
Kafka Producer for Football Live Match Data
Fetches data from Football-Data.org API and publishes to Kafka
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configuration
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
KAFKA_TOPIC_MATCHES = 'live-matches'
FOOTBALL_API_URL = 'https://api.football-data.org/v4'
FOOTBALL_API_KEY = 'YOUR_API_KEY_HERE'  # Replace with actual key

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FootballDataProducer:
    """Producer for football live match data"""
    
    def __init__(self, bootstrap_servers: List[str], api_key: str):
        """Initialize the producer"""
        self.api_key = api_key
        self.headers = {'X-Auth-Token': api_key}
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            compression_type='lz4',
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=5,
            enable_idempotence=True
        )
        logger.info("Kafka producer initialized")
    
    def fetch_live_matches(self) -> Optional[List[Dict]]:
        """Fetch live matches from Football-Data API"""
        try:
            # Get today's matches
            url = f'{FOOTBALL_API_URL}/matches'
            params = {
                'status': 'LIVE,IN_PLAY',
                'dateFrom': datetime.now().strftime('%Y-%m-%d'),
                'dateTo': datetime.now().strftime('%Y-%m-%d')
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            matches = data.get('matches', [])
            logger.info(f"Fetched {len(matches)} live matches")
            return matches
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching matches: {e}")
            return None
    
    def fetch_match_details(self, match_id: int) -> Optional[Dict]:
        """Fetch detailed match information"""
        try:
            url = f'{FOOTBALL_API_URL}/matches/{match_id}'
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching match details for {match_id}: {e}")
            return None
    
    def enrich_match_data(self, match: Dict) -> Dict:
        """Enrich match data with additional information"""
        enriched = {
            'match_id': match.get('id'),
            'status': match.get('status'),
            'minute': match.get('minute'),
            'timestamp': datetime.now().isoformat(),
            'competition': {
                'id': match.get('competition', {}).get('id'),
                'name': match.get('competition', {}).get('name'),
                'code': match.get('competition', {}).get('code')
            },
            'home_team': {
                'id': match.get('homeTeam', {}).get('id'),
                'name': match.get('homeTeam', {}).get('name'),
                'crest': match.get('homeTeam', {}).get('crest')
            },
            'away_team': {
                'id': match.get('awayTeam', {}).get('id'),
                'name': match.get('awayTeam', {}).get('name'),
                'crest': match.get('awayTeam', {}).get('crest')
            },
            'score': {
                'home': match.get('score', {}).get('fullTime', {}).get('home'),
                'away': match.get('score', {}).get('fullTime', {}).get('away'),
                'winner': match.get('score', {}).get('winner')
            },
            'referees': match.get('referees', []),
            'utc_date': match.get('utcDate')
        }
        return enriched
    
    def publish_to_kafka(self, topic: str, key: str, data: Dict):
        """Publish data to Kafka topic"""
        try:
            future = self.producer.send(
                topic,
                key=key,
                value=data
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            logger.info(
                f"Published to {record_metadata.topic} "
                f"partition {record_metadata.partition} "
                f"offset {record_metadata.offset}"
            )
            
        except KafkaError as e:
            logger.error(f"Failed to publish to Kafka: {e}")
    
    def run(self, interval: int = 10):
        """Run the producer continuously"""
        logger.info(f"Starting producer (fetching every {interval}s)")
        
        try:
            while True:
                # Fetch live matches
                matches = self.fetch_live_matches()
                
                if matches:
                    for match in matches:
                        # Enrich match data
                        enriched_match = self.enrich_match_data(match)
                        
                        # Publish to Kafka
                        match_key = f"match_{match['id']}"
                        self.publish_to_kafka(
                            KAFKA_TOPIC_MATCHES,
                            match_key,
                            enriched_match
                        )
                        
                        logger.info(
                            f"Published match: {enriched_match['home_team']['name']} vs "
                            f"{enriched_match['away_team']['name']} "
                            f"({enriched_match['score']['home']}-{enriched_match['score']['away']})"
                        )
                
                # Wait before next fetch
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Shutting down producer...")
        finally:
            self.producer.close()


def main():
    """Main entry point"""
    # Check if API key is set
    if FOOTBALL_API_KEY == 'YOUR_API_KEY_HERE':
        logger.error("Please set your Football-Data API key!")
        logger.info("Get your free API key at: https://www.football-data.org/")
        return
    
    # Create and run producer
    producer = FootballDataProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        api_key=FOOTBALL_API_KEY
    )
    
    producer.run(interval=10)


if __name__ == '__main__':
    main()
