"""
Quick test script to read messages from Confluent Cloud Kafka topic using kafka-python.
This is a simpler alternative to Spark for testing.

Usage:
    python src/streaming/test_kafka_simple.py
    
Install dependencies:
    pip install kafka-python
"""

import os
from kafka import KafkaConsumer
import json

def main():
    # Load from environment
    kafka_bootstrap = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'pkc-312o0.ap-southeast-1.aws.confluent.cloud:9092')
    kafka_api_key = os.environ.get('KAFKA_API_KEY', 'YXERA5PFM2TMAU6Z')
    kafka_api_secret = os.environ.get('KAFKA_API_SECRET', 'cfltpKodnfC/24wU7Amhzs/9yCcAFprLKnIj93/KgyYb1aV8NzefOCuvvnwXkKgg')
    kafka_topic = os.environ.get('KAFKA_TOPIC', 'live-match-events')
    
    print(f"🔗 Connecting to Kafka:")
    print(f"   Bootstrap: {kafka_bootstrap}")
    print(f"   Topic: {kafka_topic}")
    print(f"   API Key: {kafka_api_key[:10]}...")
    print()
    
    try:
        # Create consumer
        consumer = KafkaConsumer(
            kafka_topic,
            bootstrap_servers=kafka_bootstrap,
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=kafka_api_key,
            sasl_plain_password=kafka_api_secret,
            auto_offset_reset='earliest',  # Read from beginning
            enable_auto_commit=False,
            consumer_timeout_ms=10000,  # Stop after 10s of no messages
            value_deserializer=lambda m: m.decode('utf-8')
        )
        
        print("✅ Connected to Kafka topic")
        print(f"📊 Fetching messages from topic '{kafka_topic}'...")
        print("="*80)
        print()
        
        message_count = 0
        
        # Read messages
        for message in consumer:
            message_count += 1
            
            print(f"📨 Message #{message_count}")
            print(f"   Partition: {message.partition}")
            print(f"   Offset: {message.offset}")
            print(f"   Timestamp: {message.timestamp}")
            print(f"   Key: {message.key.decode('utf-8') if message.key else 'None'}")
            print()
            
            # Try to parse and pretty print JSON
            try:
                data = json.loads(message.value)
                print("   Value (JSON):")
                print(json.dumps(data, indent=4, ensure_ascii=False))
            except:
                print(f"   Value (raw): {message.value}")
            
            print()
            print("-"*80)
            print()
            
            # Limit to first 5 messages
            if message_count >= 5:
                print(f"💡 Showing first 5 messages only. Total messages processed: {message_count}")
                break
        
        if message_count == 0:
            print("⚠️  No messages found in topic")
        else:
            print(f"\n✅ Test completed! Total messages read: {message_count}")
        
        consumer.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
