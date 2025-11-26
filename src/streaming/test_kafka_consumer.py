"""
Quick test script to read messages from Confluent Cloud Kafka topic.
This script reads from 'live-match-events' topic and displays the first few messages.

Usage:
    python src/streaming/test_kafka_consumer.py
    
Environment variables needed (from .env.example):
    - KAFKA_BOOTSTRAP_SERVERS
    - KAFKA_API_KEY
    - KAFKA_API_SECRET
    - KAFKA_TOPIC
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, expr
from pyspark.sql.types import StructType, StringType

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
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("test-kafka-consumer") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("✅ Spark session created")
    
    # Read from Kafka (batch mode for testing)
    try:
        df = spark.read.format('kafka') \
            .option('kafka.bootstrap.servers', kafka_bootstrap) \
            .option('subscribe', kafka_topic) \
            .option('startingOffsets', 'earliest') \
            .option('kafka.security.protocol', 'SASL_SSL') \
            .option('kafka.sasl.mechanism', 'PLAIN') \
            .option('kafka.sasl.jaas.config', 
                    f'org.apache.kafka.common.security.plain.PlainLoginModule required '
                    f'username="{kafka_api_key}" password="{kafka_api_secret}";') \
            .load()
        
        print("✅ Connected to Kafka topic")
        
        # Get message count
        total_count = df.count()
        print(f"\n📊 Total messages in topic: {total_count}")
        
        if total_count == 0:
            print("⚠️  No messages found in topic")
            return
        
        # Show first few messages (key + value as string)
        print("\n📨 Sample messages (first 5):")
        print("="*80)
        
        df_display = df.selectExpr(
            "CAST(key AS STRING) as key",
            "CAST(value AS STRING) as value",
            "topic",
            "partition",
            "offset",
            "timestamp"
        ).limit(5)
        
        df_display.show(5, truncate=False, vertical=True)
        
        # Try to parse JSON value
        print("\n🔍 Parsing JSON content:")
        print("="*80)
        
        df_json = df.selectExpr("CAST(value AS STRING) as json_str")
        
        # Show first message in pretty format
        first_msg = df_json.first()
        if first_msg:
            import json
            try:
                parsed = json.loads(first_msg['json_str'])
                print(json.dumps(parsed, indent=2, ensure_ascii=False))
            except:
                print(first_msg['json_str'])
        
        print("\n✅ Test completed successfully!")
        print(f"💡 Tip: To consume in streaming mode, use spark.readStream instead of spark.read")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == '__main__':
    main()
