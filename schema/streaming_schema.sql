-- ============================================================================
-- PostgreSQL Schema for Live Streaming Data
-- ============================================================================

-- Create streaming schema
CREATE SCHEMA IF NOT EXISTS streaming;

-- Set search path
SET search_path TO streaming, public;

-- ============================================================================
-- TABLE: live_events
-- Real-time match events from Kafka streaming
-- ============================================================================

DROP TABLE IF EXISTS streaming.live_events CASCADE;
CREATE TABLE streaming.live_events (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    status VARCHAR(20),
    minute INTEGER,
    
    -- Competition
    competition_name VARCHAR(255),
    competition_code VARCHAR(50),
    
    -- Teams
    home_team_name VARCHAR(255),
    away_team_name VARCHAR(255),
    
    -- Score
    home_score INTEGER,
    away_score INTEGER,
    total_goals INTEGER,
    match_result VARCHAR(20), -- HOME_WIN, AWAY_WIN, DRAW, LIVE
    
    -- Venue
    venue VARCHAR(255),
    
    -- Flags
    is_live BOOLEAN DEFAULT false,
    
    -- Metadata
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_event UNIQUE (match_id, event_timestamp)
);

-- Indexes
CREATE INDEX idx_live_events_match_id ON streaming.live_events(match_id);
CREATE INDEX idx_live_events_timestamp ON streaming.live_events(event_timestamp DESC);
CREATE INDEX idx_live_events_status ON streaming.live_events(status);
CREATE INDEX idx_live_events_is_live ON streaming.live_events(is_live) WHERE is_live = true;
CREATE INDEX idx_live_events_competition ON streaming.live_events(competition_code);

COMMENT ON TABLE streaming.live_events IS 'Real-time match events from Kafka stream';


-- Note: Detailed event breakdown (goals, cards, substitutions) can be added later
-- For now, streaming.live_events stores match-level updates
-- Future enhancement: Parse raw_data JSON to extract individual events


-- ============================================================================
-- VIEW: current_live_matches
-- Shows only currently LIVE matches with latest state
-- ============================================================================

DROP VIEW IF EXISTS streaming.vw_current_live_matches CASCADE;
CREATE VIEW streaming.vw_current_live_matches AS
WITH latest_events AS (
    SELECT DISTINCT ON (match_id)
        match_id,
        event_timestamp,
        competition_name,
        home_team_name,
        away_team_name,
        home_score,
        away_score,
        total_goals,
        status,
        minute,
        venue,
        processed_at
    FROM streaming.live_events
    WHERE is_live = true
    ORDER BY match_id, event_timestamp DESC
)
SELECT 
    match_id,
    competition_name,
    home_team_name,
    away_team_name,
    home_score,
    away_score,
    total_goals,
    home_team_name || ' ' || COALESCE(home_score::text, '0') || '-' || 
        COALESCE(away_score::text, '0') || ' ' || away_team_name AS match_summary,
    CASE 
        WHEN home_score > away_score THEN home_team_name
        WHEN away_score > home_score THEN away_team_name
        ELSE 'DRAW'
    END AS leading_team,
    status,
    minute,
    venue,
    event_timestamp AS last_updated
FROM latest_events
ORDER BY event_timestamp DESC;

COMMENT ON VIEW streaming.vw_current_live_matches IS 'Currently live (IN_PLAY) matches with latest scores';


-- ============================================================================
-- VIEW: match_score_progression
-- Show how scores change over time for each match
-- ============================================================================

DROP VIEW IF EXISTS streaming.vw_match_score_progression CASCADE;
CREATE VIEW streaming.vw_match_score_progression AS
SELECT 
    match_id,
    event_timestamp,
    minute,
    home_team_name,
    away_team_name,
    home_score,
    away_score,
    total_goals,
    match_result,
    competition_name
FROM streaming.live_events
ORDER BY match_id, event_timestamp;

COMMENT ON VIEW streaming.vw_match_score_progression IS 'Score progression timeline for each match';


-- ============================================================================
-- MATERIALIZED VIEW: competition_live_summary
-- Summary by competition
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS streaming.mvw_competition_summary CASCADE;
CREATE MATERIALIZED VIEW streaming.mvw_competition_summary AS
SELECT 
    competition_name,
    competition_code,
    COUNT(DISTINCT match_id) AS total_matches,
    SUM(total_goals) AS total_goals,
    ROUND(AVG(total_goals), 2) AS avg_goals_per_match,
    MAX(total_goals) AS max_goals_in_match,
    COUNT(*) FILTER (WHERE is_live = true) AS currently_live
FROM streaming.live_events
GROUP BY competition_name, competition_code
ORDER BY total_matches DESC;

CREATE INDEX idx_mvw_competition_summary_code ON streaming.mvw_competition_summary(competition_code);

COMMENT ON MATERIALIZED VIEW streaming.mvw_competition_summary IS 'Aggregated statistics by competition';


-- ============================================================================
-- FUNCTION: refresh_streaming_views
-- Refresh all materialized views in streaming schema
-- ============================================================================

CREATE OR REPLACE FUNCTION streaming.refresh_streaming_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY streaming.mvw_competition_summary;
    RAISE NOTICE 'Streaming materialized views refreshed';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION streaming.refresh_streaming_views() IS 'Refresh all streaming materialized views';


-- ============================================================================
-- RETENTION POLICY: Clean old data (keep last 7 days)
-- ============================================================================

CREATE OR REPLACE FUNCTION streaming.cleanup_old_data()
RETURNS void AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete events older than 7 days
    DELETE FROM streaming.live_events
    WHERE event_timestamp < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Deleted % old events (retention: 7 days)', deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION streaming.cleanup_old_data() IS 'Delete streaming data older than 7 days';


-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get current live matches
-- SELECT * FROM streaming.vw_current_live_matches;

-- Get score progression for a match
-- SELECT * FROM streaming.vw_match_score_progression WHERE match_id = '12345';

-- Get competition summary
-- SELECT * FROM streaming.mvw_competition_summary;

-- Refresh materialized views
-- SELECT streaming.refresh_streaming_views();

-- Clean old data
-- SELECT streaming.cleanup_old_data();

-- Get all events in last hour
-- SELECT * FROM streaming.live_events 
-- WHERE event_timestamp > NOW() - INTERVAL '1 hour'
-- ORDER BY event_timestamp DESC;


-- ============================================================================
-- GRANTS (adjust based on your user roles)
-- ============================================================================

-- GRANT USAGE ON SCHEMA streaming TO streaming_user;
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA streaming TO streaming_user;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA streaming TO streaming_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA streaming TO streaming_user;


-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Streaming Schema Created Successfully';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Schema: streaming';
    RAISE NOTICE 'Tables: 1 (live_events)';
    RAISE NOTICE 'Views: 2 (current_live_matches, match_score_progression)';
    RAISE NOTICE 'Materialized Views: 1 (competition_summary)';
    RAISE NOTICE 'Functions: 2 (refresh_streaming_views, cleanup_old_data)';
    RAISE NOTICE '========================================';
END $$;
