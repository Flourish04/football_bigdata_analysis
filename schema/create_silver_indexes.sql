-- ============================================================================
-- POSTGRESQL INDEXES FOR SILVER LAYER
-- Purpose: Optimize query performance for common access patterns
-- ============================================================================

-- Drop existing indexes if rerunning
DROP INDEX IF EXISTS idx_silver_player_profiles_player_id CASCADE;
DROP INDEX IF EXISTS idx_silver_player_profiles_name CASCADE;
DROP INDEX IF EXISTS idx_silver_player_profiles_age CASCADE;
DROP INDEX IF EXISTS idx_silver_player_profiles_position CASCADE;
DROP INDEX IF EXISTS idx_silver_player_performances_player_id CASCADE;
DROP INDEX IF EXISTS idx_silver_player_performances_season CASCADE;
DROP INDEX IF EXISTS idx_silver_player_performances_competition CASCADE;
DROP INDEX IF EXISTS idx_silver_transfer_history_player_id CASCADE;
DROP INDEX IF EXISTS idx_silver_transfer_history_date CASCADE;
DROP INDEX IF EXISTS idx_silver_player_market_value_player_id CASCADE;
DROP INDEX IF EXISTS idx_silver_player_injuries_player_id CASCADE;
DROP INDEX IF EXISTS idx_silver_player_teammates_player_id CASCADE;

-- ============================================================================
-- PLAYER_PROFILES (92,671 rows) - Master Data
-- ============================================================================

CREATE INDEX idx_silver_player_profiles_player_id 
ON silver_layer.player_profiles(player_id);

CREATE INDEX idx_silver_player_profiles_name 
ON silver_layer.player_profiles(player_name);

CREATE INDEX idx_silver_player_profiles_age 
ON silver_layer.player_profiles(age DESC);

CREATE INDEX idx_silver_player_profiles_position 
ON silver_layer.player_profiles(position);

CREATE INDEX idx_silver_player_profiles_citizenship 
ON silver_layer.player_profiles(citizenship);

-- ============================================================================
-- PLAYER_PERFORMANCES (1,878,719 rows) - Largest fact table
-- ============================================================================

CREATE INDEX idx_silver_player_performances_player_id 
ON silver_layer.player_performances(player_id);

CREATE INDEX idx_silver_player_performances_season 
ON silver_layer.player_performances(season_name);

CREATE INDEX idx_silver_player_performances_competition 
ON silver_layer.player_performances(competition_name);

-- Composite index for common filter patterns
CREATE INDEX idx_silver_player_performances_player_season 
ON silver_layer.player_performances(player_id, season_name);

CREATE INDEX idx_silver_player_performances_goals 
ON silver_layer.player_performances(goals DESC) 
WHERE goals > 0;

-- ============================================================================
-- TRANSFER_HISTORY (1,101,440 rows)
-- ============================================================================

CREATE INDEX idx_silver_transfer_history_player_id 
ON silver_layer.transfer_history(player_id);

CREATE INDEX idx_silver_transfer_history_date 
ON silver_layer.transfer_history(transfer_date DESC);

CREATE INDEX idx_silver_transfer_history_from_club 
ON silver_layer.transfer_history(from_club_name);

CREATE INDEX idx_silver_transfer_history_to_club 
ON silver_layer.transfer_history(to_club_name);

-- Composite for date range queries
CREATE INDEX idx_silver_transfer_history_player_date 
ON silver_layer.transfer_history(player_id, transfer_date DESC);

-- ============================================================================
-- PLAYER_MARKET_VALUE (901,429 rows)
-- ============================================================================

CREATE INDEX idx_silver_player_market_value_player_id 
ON silver_layer.player_market_value(player_id);

CREATE INDEX idx_silver_player_market_value_date 
ON silver_layer.player_market_value(date DESC);

CREATE INDEX idx_silver_player_market_value_value 
ON silver_layer.player_market_value(market_value DESC) 
WHERE market_value IS NOT NULL;

-- Composite for time-series queries
CREATE INDEX idx_silver_player_market_value_player_date 
ON silver_layer.player_market_value(player_id, date DESC);

-- ============================================================================
-- PLAYER_INJURIES (143,195 rows)
-- ============================================================================

CREATE INDEX idx_silver_player_injuries_player_id 
ON silver_layer.player_injuries(player_id);

CREATE INDEX idx_silver_player_injuries_season 
ON silver_layer.player_injuries(season_name);

CREATE INDEX idx_silver_player_injuries_severity 
ON silver_layer.player_injuries(days_missed DESC) 
WHERE days_missed > 0;

CREATE INDEX idx_silver_player_injuries_date 
ON silver_layer.player_injuries(injury_date DESC);

-- ============================================================================
-- PLAYER_TEAMMATES_PLAYED_WITH (1,257,342 rows)
-- ============================================================================

CREATE INDEX idx_silver_player_teammates_player_id 
ON silver_layer.player_teammates_played_with(player_id);

CREATE INDEX idx_silver_player_teammates_teammate_id 
ON silver_layer.player_teammates_played_with(teammate_player_id);

-- Composite for bidirectional lookups
CREATE INDEX idx_silver_player_teammates_both 
ON silver_layer.player_teammates_played_with(player_id, teammate_player_id);

-- ============================================================================
-- PLAYER_NATIONAL_PERFORMANCES (92,701 rows)
-- ============================================================================

CREATE INDEX idx_silver_player_national_player_id 
ON silver_layer.player_national_performances(player_id);

CREATE INDEX idx_silver_player_national_competition 
ON silver_layer.player_national_performances(competition_name);

-- ============================================================================
-- TEAM DIMENSION TABLES (Small - indexes less critical but useful)
-- ============================================================================

CREATE INDEX idx_silver_team_details_team_id 
ON silver_layer.team_details(team_id);

CREATE INDEX idx_silver_team_details_name 
ON silver_layer.team_details(team_name);

CREATE INDEX idx_silver_team_competitions_team_id 
ON silver_layer.team_competitions_seasons(team_id);

CREATE INDEX idx_silver_team_competitions_season 
ON silver_layer.team_competitions_seasons(season_name);

CREATE INDEX idx_silver_team_children_parent_id 
ON silver_layer.team_children(parent_team_id);

CREATE INDEX idx_silver_team_children_child_id 
ON silver_layer.team_children(child_team_id);

-- ============================================================================
-- ANALYZE TABLES - Update statistics for query planner
-- ============================================================================

ANALYZE silver_layer.player_profiles;
ANALYZE silver_layer.player_performances;
ANALYZE silver_layer.player_market_value;
ANALYZE silver_layer.player_injuries;
ANALYZE silver_layer.player_national_performances;
ANALYZE silver_layer.player_teammates_played_with;
ANALYZE silver_layer.transfer_history;
ANALYZE silver_layer.team_details;
ANALYZE silver_layer.team_competitions_seasons;
ANALYZE silver_layer.team_children;

-- ============================================================================
-- VERIFICATION - Show all indexes
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes
WHERE schemaname = 'silver_layer'
ORDER BY tablename, indexname;

-- Show table sizes with indexes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE schemaname = 'silver_layer'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- ============================================================================
-- DONE - Indexes created successfully!
-- ============================================================================

\echo '✅ All indexes created successfully!'
\echo '📊 Total indexes: 35+'
\echo '🚀 Query performance optimized for:'
\echo '   - Player lookups by ID/name'
\echo '   - Season-based queries'
\echo '   - Transfer date ranges'
\echo '   - Market value trends'
\echo '   - Injury analysis'
\echo '   - Teammate relationships'
