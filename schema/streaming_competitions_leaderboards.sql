-- ============================================================================
-- PostgreSQL Schema Extension for Competitions & Leaderboards Streaming
-- ============================================================================
-- File: schema/streaming_competitions_leaderboards.sql
-- Purpose: Add competitions and leaderboards tables to streaming schema
-- Date: November 28, 2025
-- ============================================================================

-- Set search path
SET search_path TO streaming, public;

-- ============================================================================
-- TABLE: competitions
-- Competition/League information with current season details
-- Source: football-data.org API /competitions endpoint
-- ============================================================================

DROP TABLE IF EXISTS streaming.competitions CASCADE;
CREATE TABLE streaming.competitions (
    competition_id INTEGER PRIMARY KEY,
    competition_name VARCHAR(255) NOT NULL,
    competition_code VARCHAR(50) NOT NULL,
    competition_type VARCHAR(50), -- LEAGUE, CUP, PLAYOFFS
    emblem_url TEXT,
    plan VARCHAR(50), -- TIER_ONE, TIER_TWO, TIER_THREE, TIER_FOUR
    
    -- Area/Region information
    area_id INTEGER,
    area_name VARCHAR(255),
    area_code VARCHAR(10),
    area_flag_url TEXT,
    
    -- Current season details
    current_season_id INTEGER,
    season_start_date DATE,
    season_end_date DATE,
    current_matchday INTEGER,
    season_winner_id INTEGER,
    season_winner_name VARCHAR(255),
    
    -- Metadata
    number_of_available_seasons INTEGER,
    last_updated TIMESTAMP,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(50) DEFAULT 'football-data-api',
    
    CONSTRAINT unique_competition UNIQUE (competition_id)
);

-- Staging table for competitions (used by Spark Streaming)
DROP TABLE IF EXISTS streaming.competitions_staging;
CREATE TABLE streaming.competitions_staging (
    LIKE streaming.competitions INCLUDING ALL
);

-- Indexes for competitions
CREATE INDEX idx_competitions_code ON streaming.competitions(competition_code);
CREATE INDEX idx_competitions_name ON streaming.competitions(competition_name);
CREATE INDEX idx_competitions_type ON streaming.competitions(competition_type);
CREATE INDEX idx_competitions_area ON streaming.competitions(area_id);
CREATE INDEX idx_competitions_season ON streaming.competitions(current_season_id);
CREATE INDEX idx_competitions_matchday ON streaming.competitions(current_matchday);
CREATE INDEX idx_competitions_processed ON streaming.competitions(processed_at DESC);

-- Comments
COMMENT ON TABLE streaming.competitions IS 'Competition/League master data from football-data.org API';
COMMENT ON COLUMN streaming.competitions.competition_id IS 'Unique competition ID from API';
COMMENT ON COLUMN streaming.competitions.plan IS 'API plan tier: TIER_ONE, TIER_TWO, TIER_THREE, TIER_FOUR';
COMMENT ON COLUMN streaming.competitions.current_matchday IS 'Current matchday/gameweek number';

-- ============================================================================
-- TABLE: leaderboards
-- Competition standings/leaderboard/table data
-- Source: football-data.org API /competitions/{id}/standings endpoint
-- ============================================================================

DROP TABLE IF EXISTS streaming.leaderboards CASCADE;
CREATE TABLE streaming.leaderboards (
    id BIGSERIAL PRIMARY KEY,
    
    -- Competition reference
    competition_id INTEGER NOT NULL,
    competition_name VARCHAR(255),
    competition_code VARCHAR(50),
    competition_type VARCHAR(50),
    
    -- Season information
    season_id INTEGER NOT NULL,
    season_start_date DATE,
    season_end_date DATE,
    current_matchday INTEGER,
    
    -- Area/Region
    area_id INTEGER,
    area_name VARCHAR(255),
    area_code VARCHAR(10),
    
    -- Standing details
    stage VARCHAR(100), -- GROUP_STAGE, KNOCKOUT, REGULAR_SEASON, etc.
    standing_type VARCHAR(50), -- TOTAL, HOME, AWAY
    group_name VARCHAR(100), -- 'Group A', 'League phase', etc.
    
    -- Team position in table
    position INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    team_short_name VARCHAR(100),
    team_tla VARCHAR(10), -- Three Letter Abbreviation
    team_crest_url TEXT,
    
    -- Match statistics
    played_games INTEGER DEFAULT 0,
    won INTEGER DEFAULT 0,
    draw INTEGER DEFAULT 0,
    lost INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    
    -- Goal statistics
    goals_for INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    goal_difference INTEGER DEFAULT 0,
    
    -- Form (recent results)
    form VARCHAR(20), -- e.g., 'WWDLL' - last 5 matches
    
    -- Metadata
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(50) DEFAULT 'football-data-api',
    
    -- Unique constraint: one entry per team per competition/season/stage/type/group
    CONSTRAINT unique_leaderboard_entry UNIQUE (
        competition_id, 
        season_id, 
        stage, 
        standing_type, 
        team_id, 
        COALESCE(group_name, '')
    )
);

-- Staging table for leaderboards (used by Spark Streaming)
DROP TABLE IF EXISTS streaming.leaderboards_staging;
CREATE TABLE streaming.leaderboards_staging (
    LIKE streaming.leaderboards INCLUDING ALL
);

-- Indexes for leaderboards
CREATE INDEX idx_leaderboards_competition ON streaming.leaderboards(competition_id);
CREATE INDEX idx_leaderboards_season ON streaming.leaderboards(season_id);
CREATE INDEX idx_leaderboards_team ON streaming.leaderboards(team_id);
CREATE INDEX idx_leaderboards_position ON streaming.leaderboards(position);
CREATE INDEX idx_leaderboards_points ON streaming.leaderboards(points DESC);
CREATE INDEX idx_leaderboards_goal_diff ON streaming.leaderboards(goal_difference DESC);
CREATE INDEX idx_leaderboards_stage ON streaming.leaderboards(stage);
CREATE INDEX idx_leaderboards_type ON streaming.leaderboards(standing_type);
CREATE INDEX idx_leaderboards_group ON streaming.leaderboards(group_name);
CREATE INDEX idx_leaderboards_processed ON streaming.leaderboards(processed_at DESC);

-- Composite indexes for common queries
CREATE INDEX idx_leaderboards_comp_season ON streaming.leaderboards(competition_id, season_id);
CREATE INDEX idx_leaderboards_comp_stage ON streaming.leaderboards(competition_id, stage);
CREATE INDEX idx_leaderboards_team_season ON streaming.leaderboards(team_id, season_id);

-- Comments
COMMENT ON TABLE streaming.leaderboards IS 'Competition standings/tables from football-data.org API';
COMMENT ON COLUMN streaming.leaderboards.stage IS 'Competition stage: GROUP_STAGE, KNOCKOUT, REGULAR_SEASON, etc.';
COMMENT ON COLUMN streaming.leaderboards.standing_type IS 'Table type: TOTAL (all matches), HOME (home only), AWAY (away only)';
COMMENT ON COLUMN streaming.leaderboards.form IS 'Recent form string: W=Win, D=Draw, L=Loss (e.g., WWDLL)';
COMMENT ON COLUMN streaming.leaderboards.team_tla IS 'Three-letter team abbreviation (e.g., ARS, PSG, FCB)';

-- Foreign key constraint (optional - enable if referential integrity needed)
-- ALTER TABLE streaming.leaderboards 
-- ADD CONSTRAINT fk_leaderboards_competition 
-- FOREIGN KEY (competition_id) REFERENCES streaming.competitions(competition_id) ON DELETE CASCADE;

-- ============================================================================
-- VIEWS: Useful queries for dashboards
-- ============================================================================

-- View: Current season standings for all competitions
DROP VIEW IF EXISTS streaming.vw_current_standings CASCADE;
CREATE VIEW streaming.vw_current_standings AS
SELECT 
    l.competition_name,
    l.competition_code,
    l.stage,
    l.group_name,
    l.position,
    l.team_name,
    l.team_tla,
    l.played_games,
    l.won,
    l.draw,
    l.lost,
    l.points,
    l.goals_for,
    l.goals_against,
    l.goal_difference,
    l.form,
    c.current_matchday,
    c.season_end_date
FROM streaming.leaderboards l
JOIN streaming.competitions c ON l.competition_id = c.competition_id
WHERE l.season_id = c.current_season_id
  AND l.standing_type = 'TOTAL'
ORDER BY l.competition_id, l.stage, l.group_name, l.position;

COMMENT ON VIEW streaming.vw_current_standings IS 'Current season standings for all competitions (TOTAL table type only)';

-- View: Top teams across all competitions
DROP VIEW IF EXISTS streaming.vw_top_teams CASCADE;
CREATE VIEW streaming.vw_top_teams AS
SELECT 
    l.team_name,
    l.team_tla,
    l.competition_name,
    l.position,
    l.points,
    l.played_games,
    l.goal_difference,
    l.goals_for,
    ROUND(l.points::NUMERIC / NULLIF(l.played_games, 0), 2) AS points_per_game,
    ROUND(l.goals_for::NUMERIC / NULLIF(l.played_games, 0), 2) AS goals_per_game,
    l.form
FROM streaming.leaderboards l
JOIN streaming.competitions c ON l.competition_id = c.competition_id
WHERE l.season_id = c.current_season_id
  AND l.standing_type = 'TOTAL'
  AND l.position <= 5
ORDER BY l.points DESC, l.goal_difference DESC, l.goals_for DESC
LIMIT 100;

COMMENT ON VIEW streaming.vw_top_teams IS 'Top 5 teams from each competition based on current standings';

-- View: Competition summary statistics
DROP VIEW IF EXISTS streaming.vw_competition_summary CASCADE;
CREATE VIEW streaming.vw_competition_summary AS
SELECT 
    c.competition_id,
    c.competition_name,
    c.competition_code,
    c.competition_type,
    c.area_name,
    c.current_matchday,
    c.season_start_date,
    c.season_end_date,
    COUNT(DISTINCT l.team_id) AS total_teams,
    SUM(l.goals_for) AS total_goals,
    ROUND(AVG(l.goals_for + l.goals_against)::NUMERIC / NULLIF(AVG(l.played_games), 0), 2) AS avg_goals_per_game,
    MAX(l.points) AS max_points,
    MIN(l.points) AS min_points
FROM streaming.competitions c
LEFT JOIN streaming.leaderboards l ON c.competition_id = l.competition_id 
    AND c.current_season_id = l.season_id
    AND l.standing_type = 'TOTAL'
GROUP BY 
    c.competition_id,
    c.competition_name,
    c.competition_code,
    c.competition_type,
    c.area_name,
    c.current_matchday,
    c.season_start_date,
    c.season_end_date
ORDER BY c.competition_name;

COMMENT ON VIEW streaming.vw_competition_summary IS 'Summary statistics for all competitions';

-- View: Team performance comparison (home vs away)
DROP VIEW IF EXISTS streaming.vw_team_home_away_comparison CASCADE;
CREATE VIEW streaming.vw_team_home_away_comparison AS
WITH home_stats AS (
    SELECT 
        competition_id,
        season_id,
        team_id,
        team_name,
        points AS home_points,
        goals_for AS home_goals_for,
        goals_against AS home_goals_against
    FROM streaming.leaderboards
    WHERE standing_type = 'HOME'
),
away_stats AS (
    SELECT 
        competition_id,
        season_id,
        team_id,
        team_name,
        points AS away_points,
        goals_for AS away_goals_for,
        goals_against AS away_goals_against
    FROM streaming.leaderboards
    WHERE standing_type = 'AWAY'
)
SELECT 
    h.team_name,
    c.competition_name,
    h.home_points,
    a.away_points,
    (h.home_points + a.away_points) AS total_points,
    h.home_goals_for,
    a.away_goals_for,
    h.home_goals_against,
    a.away_goals_against,
    (h.home_points - a.away_points) AS home_advantage,
    CASE 
        WHEN h.home_points > a.away_points THEN 'Stronger at home'
        WHEN h.home_points < a.away_points THEN 'Stronger away'
        ELSE 'Balanced'
    END AS performance_type
FROM home_stats h
JOIN away_stats a ON h.competition_id = a.competition_id 
    AND h.season_id = a.season_id 
    AND h.team_id = a.team_id
JOIN streaming.competitions c ON h.competition_id = c.competition_id
    AND h.season_id = c.current_season_id
ORDER BY (h.home_points + a.away_points) DESC;

COMMENT ON VIEW streaming.vw_team_home_away_comparison IS 'Compare team performance at home vs away';

-- ============================================================================
-- MATERIALIZED VIEW: Competition rankings (for fast dashboard queries)
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS streaming.mv_competition_rankings CASCADE;
CREATE MATERIALIZED VIEW streaming.mv_competition_rankings AS
SELECT 
    l.competition_id,
    l.competition_name,
    l.competition_code,
    l.season_id,
    l.stage,
    l.group_name,
    l.position,
    l.team_id,
    l.team_name,
    l.team_tla,
    l.team_crest_url,
    l.played_games,
    l.won,
    l.draw,
    l.lost,
    l.points,
    l.goals_for,
    l.goals_against,
    l.goal_difference,
    l.form,
    c.current_matchday,
    c.area_name,
    -- Performance metrics
    ROUND(l.points::NUMERIC / NULLIF(l.played_games, 0), 2) AS points_per_game,
    ROUND(l.goals_for::NUMERIC / NULLIF(l.played_games, 0), 2) AS goals_scored_per_game,
    ROUND(l.goals_against::NUMERIC / NULLIF(l.played_games, 0), 2) AS goals_conceded_per_game,
    ROUND((l.won::NUMERIC / NULLIF(l.played_games, 0)) * 100, 1) AS win_percentage,
    -- Rankings
    RANK() OVER (PARTITION BY l.competition_id, l.season_id, l.stage ORDER BY l.points DESC, l.goal_difference DESC, l.goals_for DESC) AS overall_rank,
    -- Metadata
    CURRENT_TIMESTAMP AS refreshed_at
FROM streaming.leaderboards l
JOIN streaming.competitions c ON l.competition_id = c.competition_id
WHERE l.season_id = c.current_season_id
  AND l.standing_type = 'TOTAL';

-- Indexes on materialized view
CREATE UNIQUE INDEX idx_mv_comp_rankings_unique ON streaming.mv_competition_rankings(
    competition_id, season_id, stage, team_id, COALESCE(group_name, '')
);
CREATE INDEX idx_mv_comp_rankings_comp ON streaming.mv_competition_rankings(competition_id);
CREATE INDEX idx_mv_comp_rankings_team ON streaming.mv_competition_rankings(team_id);
CREATE INDEX idx_mv_comp_rankings_position ON streaming.mv_competition_rankings(position);
CREATE INDEX idx_mv_comp_rankings_points ON streaming.mv_competition_rankings(points DESC);

COMMENT ON MATERIALIZED VIEW streaming.mv_competition_rankings IS 'Pre-calculated competition rankings with performance metrics';

-- ============================================================================
-- REFRESH FUNCTION for Materialized View
-- ============================================================================

CREATE OR REPLACE FUNCTION streaming.refresh_competition_rankings()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY streaming.mv_competition_rankings;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION streaming.refresh_competition_rankings() IS 'Refresh competition rankings materialized view';

-- ============================================================================
-- GRANT PERMISSIONS (adjust as needed)
-- ============================================================================

-- Grant read access to analytics role (if exists)
-- GRANT SELECT ON ALL TABLES IN SCHEMA streaming TO analytics_role;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA streaming TO analytics_role;

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

/*
-- Get all competitions
SELECT * FROM streaming.competitions ORDER BY competition_name;

-- Get current standings for a specific competition (e.g., Premier League)
SELECT * FROM streaming.leaderboards
WHERE competition_code = 'PL'
  AND standing_type = 'TOTAL'
ORDER BY position;

-- Get top 10 teams by points across all competitions
SELECT 
    team_name, 
    competition_name, 
    position, 
    points, 
    goal_difference
FROM streaming.leaderboards
WHERE standing_type = 'TOTAL'
ORDER BY points DESC, goal_difference DESC
LIMIT 10;

-- Get Champions League group standings
SELECT 
    group_name,
    position,
    team_name,
    played_games,
    points,
    goal_difference
FROM streaming.leaderboards
WHERE competition_code = 'CL'
  AND stage = 'GROUP_STAGE'
  AND standing_type = 'TOTAL'
ORDER BY group_name, position;

-- Refresh materialized view
SELECT streaming.refresh_competition_rankings();

-- Query materialized view
SELECT * FROM streaming.mv_competition_rankings
WHERE competition_code = 'PL'
ORDER BY position
LIMIT 20;
*/

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

COMMIT;
