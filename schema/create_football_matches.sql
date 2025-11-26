-- DDL: Create table to store football matches (normalized)
-- Location: schema/create_football_matches.sql
-- Usage: psql -d yourdb -f create_football_matches.sql

CREATE TABLE IF NOT EXISTS public.football_matches (
    match_id BIGINT PRIMARY KEY,
    utc_date TIMESTAMPTZ,
    status TEXT,
    matchday INTEGER,
    stage TEXT,
    last_updated TIMESTAMPTZ,
    area JSONB,
    competition JSONB,
    season JSONB,
    home_team JSONB,
    away_team JSONB,
    winner TEXT,
    duration TEXT,
    ft_home_goals INTEGER,
    ft_away_goals INTEGER,
    ht_home_goals INTEGER,
    ht_away_goals INTEGER,
    raw JSONB, -- original normalized JSON payload (for debugging / future fields)
    processing_ts TIMESTAMPTZ DEFAULT now()
);

-- Index useful for time-range queries
CREATE INDEX IF NOT EXISTS idx_football_matches_utc_date ON public.football_matches (utc_date);

-- Example upsert (use in your ETL after staging table is populated)
-- This example assumes you wrote a staging table 'football_matches_staging' with same columns
-- and will collapse staging into the main table using INSERT ... ON CONFLICT.

-- INSERT INTO public.football_matches (...columns...)
-- SELECT ... FROM public.football_matches_staging
-- ON CONFLICT (match_id) DO UPDATE
-- SET
--   utc_date = EXCLUDED.utc_date,
--   status = EXCLUDED.status,
--   matchday = EXCLUDED.matchday,
--   stage = EXCLUDED.stage,
--   last_updated = EXCLUDED.last_updated,
--   area = EXCLUDED.area,
--   competition = EXCLUDED.competition,
--   season = EXCLUDED.season,
--   home_team = EXCLUDED.home_team,
--   away_team = EXCLUDED.away_team,
--   winner = EXCLUDED.winner,
--   duration = EXCLUDED.duration,
--   ft_home_goals = EXCLUDED.ft_home_goals,
--   ft_away_goals = EXCLUDED.ft_away_goals,
--   ht_home_goals = EXCLUDED.ht_home_goals,
--   ht_away_goals = EXCLUDED.ht_away_goals,
--   raw = EXCLUDED.raw,
--   processing_ts = now();
