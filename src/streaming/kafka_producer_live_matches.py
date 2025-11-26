"""
Kafka Producer for Live Football Matches
Polls API-Football API and publishes to Kafka topics
"""

import json
import time
import requests
import logging
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FootballAPIClient:
    """Client for API-Football"""
    
    def __init__(self):
        self.api_key = os.getenv('RAPID_API_KEY', 'YOUR_API_KEY_HERE')
        self.base_url = 'https://api-football-v1.p.rapidapi.com/v3'
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'
        }
        
    def get_live_matches(self):
        """Get all live matches"""
        endpoint = f"{self.base_url}/fixtures"
        params = {'live': 'all'}
        
        try:
            response = requests.get(
                endpoint, 
                headers=self.headers, 
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('response'):
                return data['response']
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching live matches: {e}")
            return []
    
    def get_match_events(self, fixture_id):
        """Get events for a specific match"""
        endpoint = f"{self.base_url}/fixtures/events"
        params = {'fixture': fixture_id}
        
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('response'):
                return data['response']
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching match events for {fixture_id}: {e}")
            return []
    
    def get_match_statistics(self, fixture_id):
        """Get live statistics for a match"""
        endpoint = f"{self.base_url}/fixtures/statistics"
        params = {'fixture': fixture_id}
        
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('response'):
                return data['response']
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching statistics for {fixture_id}: {e}")
            return []


class LiveMatchProducer:
    """Kafka producer for live match data"""
    
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.api_client = FootballAPIClient()
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8') if k else None,
            compression_type='gzip',
            acks='all',
            retries=3
        )
        
        self.topics = {
            'matches': 'live-matches',
            'events': 'match-events',
            'stats': 'match-stats'
        }
        
        logger.info("Kafka producer initialized")
    
    def transform_match_data(self, match):
        """Transform API response to our schema"""
        try:
            fixture = match.get('fixture', {})
            teams = match.get('teams', {})
            goals = match.get('goals', {})
            league = match.get('league', {})
            
            return {
                'match_id': fixture.get('id'),
                'timestamp': datetime.utcnow().isoformat(),
                'competition': league.get('name'),
                'competition_id': league.get('id'),
                'country': league.get('country'),
                'season': match.get('league', {}).get('season'),
                'home_team': teams.get('home', {}).get('name'),
                'home_team_id': teams.get('home', {}).get('id'),
                'away_team': teams.get('away', {}).get('name'),
                'away_team_id': teams.get('away', {}).get('id'),
                'home_score': goals.get('home'),
                'away_score': goals.get('away'),
                'status': fixture.get('status', {}).get('long'),
                'status_short': fixture.get('status', {}).get('short'),
                'minute': fixture.get('status', {}).get('elapsed'),
                'venue': fixture.get('venue', {}).get('name'),
                'referee': fixture.get('referee')
            }
        except Exception as e:
            logger.error(f"Error transforming match data: {e}")
            return None
    
    def transform_event_data(self, event, match_id):
        """Transform event data"""
        try:
            return {
                'match_id': match_id,
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event.get('type'),
                'detail': event.get('detail'),
                'minute': event.get('time', {}).get('elapsed'),
                'extra_time': event.get('time', {}).get('extra'),
                'team': event.get('team', {}).get('name'),
                'team_id': event.get('team', {}).get('id'),
                'player_id': event.get('player', {}).get('id'),
                'player_name': event.get('player', {}).get('name'),
                'assist_player_id': event.get('assist', {}).get('id'),
                'assist_player_name': event.get('assist', {}).get('name'),
                'comments': event.get('comments')
            }
        except Exception as e:
            logger.error(f"Error transforming event data: {e}")
            return None
    
    def publish_match(self, match_data):
        """Publish match data to Kafka"""
        try:
            future = self.producer.send(
                self.topics['matches'],
                key=match_data['match_id'],
                value=match_data
            )
            
            # Wait for confirmation (optional)
            record_metadata = future.get(timeout=10)
            logger.debug(
                f"Published match {match_data['match_id']} to "
                f"{record_metadata.topic} partition {record_metadata.partition}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish match: {e}")
            return False
    
    def publish_event(self, event_data):
        """Publish match event to Kafka"""
        try:
            future = self.producer.send(
                self.topics['events'],
                key=event_data['match_id'],
                value=event_data
            )
            future.get(timeout=10)
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    def run(self, poll_interval=60):
        """Main loop - poll API and publish to Kafka"""
        logger.info(f"Starting live match producer (poll interval: {poll_interval}s)")
        
        processed_events = set()  # Track processed events to avoid duplicates
        
        try:
            while True:
                logger.info("Fetching live matches...")
                matches = self.api_client.get_live_matches()
                
                if not matches:
                    logger.info("No live matches found")
                else:
                    logger.info(f"Found {len(matches)} live matches")
                    
                    for match in matches:
                        # Publish match data
                        match_data = self.transform_match_data(match)
                        if match_data:
                            self.publish_match(match_data)
                            match_id = match_data['match_id']
                            
                            # Fetch and publish events for this match
                            events = self.api_client.get_match_events(match_id)
                            for event in events:
                                event_data = self.transform_event_data(event, match_id)
                                if event_data:
                                    # Create unique event key
                                    event_key = (
                                        match_id,
                                        event_data['minute'],
                                        event_data['event_type'],
                                        event_data['player_name']
                                    )
                                    
                                    # Only publish if not already processed
                                    if event_key not in processed_events:
                                        self.publish_event(event_data)
                                        processed_events.add(event_key)
                
                # Flush producer
                self.producer.flush()
                
                logger.info(f"Sleeping for {poll_interval} seconds...")
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Shutting down producer...")
        finally:
            self.producer.close()
            logger.info("Producer closed")


def main():
    """Entry point"""
    # Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 60))  # seconds
    
    # Create and run producer
    producer = LiveMatchProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    producer.run(poll_interval=POLL_INTERVAL)


if __name__ == '__main__':
    main()
