"""
Spark Structured Streaming skeleton to read `football-matches` topic and upsert into Postgres.

Usage (example):
  export KAFKA_BOOTSTRAP=pkc-...:9092
  export KAFKA_API_KEY=your_key
  export KAFKA_API_SECRET=your_secret
  export POSTGRES_URL=jdbc:postgresql://host:5432/dbname
  export POSTGRES_USER=dbuser
  export POSTGRES_PASSWORD=dbpass

Run with spark-submit including the Kafka and PostgreSQL JDBC jars:
  spark-submit \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1 \
    --jars /path/to/postgresql.jar \
    src/streaming/spark_upsert_matches.py

Note: adjust package versions to your Spark build.
"""

import os
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, expr, lit
from pyspark.sql.types import StructType, StructField, StringType, LongType, IntegerType, TimestampType, MapType

def main():
    spark = SparkSession.builder.appName("football-matches-upsert").getOrCreate()

    # Configs from environment
    kafka_bootstrap = os.environ.get('KAFKA_BOOTSTRAP')
    kafka_api_key = os.environ.get('KAFKA_API_KEY')
    kafka_api_secret = os.environ.get('KAFKA_API_SECRET')

    pg_url = os.environ.get('POSTGRES_URL')  # jdbc:postgresql://host:5432/db
    pg_user = os.environ.get('POSTGRES_USER')
    pg_password = os.environ.get('POSTGRES_PASSWORD')

    if not kafka_bootstrap:
        raise ValueError('KAFKA_BOOTSTRAP environment variable is required')

    # Define a minimal schema for the normalized JSON (match produced by NiFi Jolt)
    schema = StructType([
        StructField('match_id', LongType()),
        StructField('utcDate', StringType()),
        StructField('status', StringType()),
        StructField('matchday', IntegerType()),
        StructField('stage', StringType()),
        StructField('lastUpdated', StringType()),
        StructField('area', MapType(StringType(), StringType())),
        StructField('competition', MapType(StringType(), StringType())),
        StructField('season', MapType(StringType(), StringType())),
        StructField('home_team', MapType(StringType(), StringType())),
        StructField('away_team', MapType(StringType(), StringType())),
        StructField('winner', StringType()),
        StructField('duration', StringType()),
        StructField('ft_home_goals', IntegerType()),
        StructField('ft_away_goals', IntegerType()),
        StructField('ht_home_goals', IntegerType()),
        StructField('ht_away_goals', IntegerType()),
        StructField('raw', MapType(StringType(), StringType()))
    ])

    # Read from Kafka
    df = spark.readStream.format('kafka') \
        .option('kafka.bootstrap.servers', kafka_bootstrap) \
        .option('subscribe', 'football-matches') \
        .option('startingOffsets', 'latest') \
        .option('kafka.security.protocol', 'SASL_SSL') \
        .option('kafka.sasl.mechanism', 'PLAIN') \
        .option('kafka.sasl.jaas.config', f"org.apache.kafka.common.security.plain.PlainLoginModule required username=\"{kafka_api_key}\" password=\"{kafka_api_secret}\";") \
        .load()

    # value is the JSON payload as bytes
    json_df = df.selectExpr('CAST(value AS STRING) as value')

    parsed = json_df.select(from_json(col('value'), schema).alias('data')).select('data.*')

    # Prepare columns to write
    out = parsed.withColumnRenamed('match_id', 'match_id') \
                .withColumnRenamed('utcDate', 'utc_date') \
                .withColumnRenamed('lastUpdated', 'last_updated')

    # Function to upsert each microbatch
    def foreach_batch(batch_df, batch_id):
        if batch_df.rdd.isEmpty():
            return

        # write staging table
        staging_table = 'football_matches_staging'
        batch_df.write.format('jdbc').options(
            url=pg_url,
            driver='org.postgresql.Driver',
            dbtable=staging_table,
            user=pg_user,
            password=pg_password
        ).mode('append').save()

        # perform upsert from staging to target table using INSERT ... ON CONFLICT
        import psycopg2
        conn = psycopg2.connect(
            dbname=pg_url.split('/')[-1],
            user=pg_user,
            password=pg_password,
            host=pg_url.split('//')[-1].split(':')[0],
            port=pg_url.split(':')[-1].split('/')[0]
        )
        cur = conn.cursor()

        upsert_sql = '''
        INSERT INTO public.football_matches (match_id, utc_date, status, matchday, stage, last_updated, area, competition, season, home_team, away_team, winner, duration, ft_home_goals, ft_away_goals, ht_home_goals, ht_away_goals, raw, processing_ts)
        SELECT match_id, to_timestamp(utc_date, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AT TIME ZONE 'UTC', status, matchday, stage, to_timestamp(last_updated, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AT TIME ZONE 'UTC', area::jsonb, competition::jsonb, season::jsonb, home_team::jsonb, away_team::jsonb, winner, duration, ft_home_goals, ft_away_goals, ht_home_goals, ht_away_goals, raw::jsonb, now()
        FROM public.football_matches_staging
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
        '''

        cur.execute(upsert_sql)
        conn.commit()

        # Optionally truncate staging
        cur.execute(f'TRUNCATE TABLE {staging_table};')
        conn.commit()
        cur.close()
        conn.close()

    query = out.writeStream.foreachBatch(foreach_batch).trigger(processingTime='60 seconds').start()
    query.awaitTermination()


if __name__ == '__main__':
    main()
