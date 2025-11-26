-- =====================================================================
-- Football Matches Table - HYBRID DESIGN (Flat + JSONB)
-- =====================================================================
-- Use Case: Analytics-first design with flexible metadata storage
-- 
-- Design Philosophy:
-- - Frequently queried fields → FLAT columns (fast queries, indexes)
-- - Metadata/rarely queried → JSONB (flexibility, less columns)
-- - Keep raw JSON for audit trail
-- =====================================================================

-- Drop existing tables if needed
DROP TABLE IF EXISTS public.football_matches_staging;
DROP TABLE IF EXISTS public.football_matches;

-- Main table
CREATE TABLE public.football_matches (
    -- Primary identifiers
    match_id BIGINT PRIMARY KEY,
    utc_date TIMESTAMPTZ NOT NULL,
    last_updated TIMESTAMPTZ,
    
    -- Match status and stage
    status TEXT NOT NULL,
    matchday INTEGER DEFAULT 0,
    stage TEXT DEFAULT 'UNKNOWN',
    
    -- Area (FLAT - for filtering)
    area_id INTEGER,
    area_name TEXT,
    area_code TEXT,
    
    -- Competition (FLAT - frequently queried)
    competition_id INTEGER,
    competition_name TEXT,
    competition_code TEXT,
    
    -- Season (FLAT - for time-based queries)
    season_id INTEGER,
    season_start_date DATE,
    season_end_date DATE,
    
    -- Home Team (FLAT - core entity for queries)
    home_team_id INTEGER,
    home_team_name TEXT,
    home_team_short_name TEXT,
    home_team_tla TEXT,
    
    -- Away Team (FLAT - core entity for queries)
    away_team_id INTEGER,
    away_team_name TEXT,
    away_team_short_name TEXT,
    away_team_tla TEXT,
    
    -- Match Result (FLAT - for statistics)
    winner TEXT,  -- HOME_TEAM, AWAY_TEAM, DRAW
    duration TEXT DEFAULT 'REGULAR',
    ft_home_goals INTEGER DEFAULT 0,
    ft_away_goals INTEGER DEFAULT 0,
    ht_home_goals INTEGER DEFAULT 0,
    ht_away_goals INTEGER DEFAULT 0,
    
    -- JSONB for metadata (rarely queried, flexible)
    area_details JSONB,        -- {"flag": "https://...", ...}
    competition_details JSONB, -- {"type": "CUP", "emblem": "https://...", ...}
    season_details JSONB,      -- {"currentMatchday": 5, "winner": null, ...}
    home_team_details JSONB,   -- {"crest": "https://...", ...}
    away_team_details JSONB,   -- {"crest": "https://...", ...}
    score_details JSONB,       -- {"regularTime": {...}, "extraTime": {...}, "penalties": {...}}
    referees JSONB,            -- [{"id": 123, "name": "...", "type": "REFEREE", ...}]
    
    -- Audit trail
    raw JSONB,  -- Original JSON from API (for debugging/future fields)
    processing_ts TIMESTAMPTZ DEFAULT now(),
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED', 'FINISHED', 'POSTPONED', 'SUSPENDED', 'CANCELLED'))
);

-- Staging table (same structure for bulk inserts)
CREATE TABLE public.football_matches_staging (
    match_id BIGINT,
    utc_date TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    status TEXT,
    matchday INTEGER,
    stage TEXT,
    area_id INTEGER,
    area_name TEXT,
    area_code TEXT,
    competition_id INTEGER,
    competition_name TEXT,
    competition_code TEXT,
    season_id INTEGER,
    season_start_date DATE,
    season_end_date DATE,
    home_team_id INTEGER,
    home_team_name TEXT,
    home_team_short_name TEXT,
    home_team_tla TEXT,
    away_team_id INTEGER,
    away_team_name TEXT,
    away_team_short_name TEXT,
    away_team_tla TEXT,
    winner TEXT,
    duration TEXT,
    ft_home_goals INTEGER,
    ft_away_goals INTEGER,
    ht_home_goals INTEGER,
    ht_away_goals INTEGER,
    area_details JSONB,
    competition_details JSONB,
    season_details JSONB,
    home_team_details JSONB,
    away_team_details JSONB,
    score_details JSONB,
    referees JSONB,
    raw JSONB,
    processing_ts TIMESTAMPTZ
);

-- =====================================================================
-- INDEXES for Performance
-- =====================================================================

-- Time-based queries (most common)
CREATE INDEX idx_matches_date ON public.football_matches(utc_date DESC);
CREATE INDEX idx_matches_date_status ON public.football_matches(utc_date DESC, status);

-- Competition queries
CREATE INDEX idx_matches_competition ON public.football_matches(competition_id);
CREATE INDEX idx_matches_competition_name ON public.football_matches(competition_name);

-- Team queries (very common)
CREATE INDEX idx_matches_home_team ON public.football_matches(home_team_id);
CREATE INDEX idx_matches_away_team ON public.football_matches(away_team_id);
CREATE INDEX idx_matches_teams ON public.football_matches(home_team_id, away_team_id);

-- Status queries
CREATE INDEX idx_matches_status ON public.football_matches(status);

-- Season queries
CREATE INDEX idx_matches_season ON public.football_matches(season_id);

-- Area/Country queries
CREATE INDEX idx_matches_area ON public.football_matches(area_id);

-- GIN indexes for JSONB (for occasional deep queries)
CREATE INDEX idx_matches_referees ON public.football_matches USING GIN (referees);

-- =====================================================================
-- EXAMPLE QUERIES
-- =====================================================================

-- Example 1: Find all Arsenal home matches
-- SELECT * FROM football_matches 
-- WHERE home_team_name = 'Arsenal FC' 
-- AND status = 'FINISHED'
-- ORDER BY utc_date DESC;

-- Example 2: Champions League standings
-- SELECT 
--     home_team_name,
--     COUNT(*) as matches,
--     SUM(CASE WHEN winner = 'HOME_TEAM' THEN 1 ELSE 0 END) as wins
-- FROM football_matches
-- WHERE competition_name = 'UEFA Champions League'
-- GROUP BY home_team_name;

-- Example 3: Get team logo (from JSONB)
-- SELECT 
--     home_team_name,
--     home_team_details->>'crest' as logo_url
-- FROM football_matches
-- LIMIT 10;

-- Example 4: Upsert from staging
-- INSERT INTO public.football_matches (...)
-- SELECT * FROM public.football_matches_staging
-- ON CONFLICT (match_id) DO UPDATE SET
--     status = EXCLUDED.status,
--     ft_home_goals = EXCLUDED.ft_home_goals,
--     ...;

COMMENT ON TABLE public.football_matches IS 'Hybrid design: Flat columns for queries, JSONB for metadata';
COMMENT ON COLUMN public.football_matches.match_id IS 'Unique match identifier from API';
COMMENT ON COLUMN public.football_matches.raw IS 'Original JSON payload for audit trail';
