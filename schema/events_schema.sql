-- ============================================================================
-- FOOTBALL EVENTS SCHEMA
-- Match-level events: goals, shots, cards, corners, substitutions
-- Integrated with existing player/team data
-- ============================================================================

-- ============================================================================
-- MATCH GENERAL INFO
-- ============================================================================

DROP TABLE IF EXISTS events.match_info CASCADE;
CREATE TABLE events.match_info (
    match_id VARCHAR(50) PRIMARY KEY,
    match_date DATE NOT NULL,
    year INTEGER,
    month INTEGER,
    country VARCHAR(100),
    league VARCHAR(100),
    season VARCHAR(20),
    home_team VARCHAR(200),
    away_team VARCHAR(200),
    home_goals INTEGER,
    away_goals INTEGER,
    total_goals INTEGER,
    match_result VARCHAR(20), -- HOME_WIN, AWAY_WIN, DRAW
    odd_h DECIMAL(10,2), -- home win odds
    odd_d DECIMAL(10,2), -- draw odds
    odd_a DECIMAL(10,2), -- away win odds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_info_date ON events.match_info(match_date);
CREATE INDEX idx_match_info_league ON events.match_info(league);
CREATE INDEX idx_match_info_season ON events.match_info(season);
CREATE INDEX idx_match_info_home_team ON events.match_info(home_team);
CREATE INDEX idx_match_info_away_team ON events.match_info(away_team);

COMMENT ON TABLE events.match_info IS 'General information about football matches';
COMMENT ON COLUMN events.match_info.match_result IS 'HOME_WIN, AWAY_WIN, or DRAW';

-- ============================================================================
-- MATCH STATISTICS (AGGREGATED FROM EVENTS)
-- ============================================================================

DROP TABLE IF EXISTS events.match_statistics CASCADE;
CREATE TABLE events.match_statistics (
    match_id VARCHAR(50) PRIMARY KEY REFERENCES events.match_info(match_id),
    total_goals INTEGER DEFAULT 0,
    total_shots INTEGER DEFAULT 0,
    shots_on_target INTEGER DEFAULT 0,
    shots_off_target INTEGER DEFAULT 0,
    shots_blocked INTEGER DEFAULT 0,
    shot_accuracy DECIMAL(5,2) DEFAULT 0.0, -- percentage
    total_corners INTEGER DEFAULT 0,
    free_kicks_won INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    fouls INTEGER DEFAULT 0,
    substitutions INTEGER DEFAULT 0,
    offsides INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_stats_goals ON events.match_statistics(total_goals DESC);
CREATE INDEX idx_match_stats_shots ON events.match_statistics(total_shots DESC);
CREATE INDEX idx_match_stats_accuracy ON events.match_statistics(shot_accuracy DESC);

COMMENT ON TABLE events.match_statistics IS 'Aggregated match statistics from events';

-- ============================================================================
-- PLAYER EVENT STATISTICS
-- Aggregated player performance from match events
-- ============================================================================

DROP TABLE IF EXISTS events.player_event_statistics CASCADE;
CREATE TABLE events.player_event_statistics (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES silver.player_profiles(player_id),
    player_name VARCHAR(255) NOT NULL,
    position VARCHAR(50),
    match_appearances INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    assists_provided INTEGER DEFAULT 0,
    total_shots INTEGER DEFAULT 0,
    shots_on_target INTEGER DEFAULT 0,
    shots_accuracy DECIMAL(5,2) DEFAULT 0.0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    fouls_committed INTEGER DEFAULT 0,
    offsides INTEGER DEFAULT 0,
    goals_per_match DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_player_event_stats_player_id ON events.player_event_statistics(player_id);
CREATE INDEX idx_player_event_stats_goals ON events.player_event_statistics(goals_scored DESC);
CREATE INDEX idx_player_event_stats_assists ON events.player_event_statistics(assists_provided DESC);
CREATE INDEX idx_player_event_stats_shots ON events.player_event_statistics(total_shots DESC);
CREATE INDEX idx_player_event_stats_appearances ON events.player_event_statistics(match_appearances DESC);

COMMENT ON TABLE events.player_event_statistics IS 'Player performance aggregated from match events';
COMMENT ON COLUMN events.player_event_statistics.player_id IS 'FK to silver.player_profiles (NULL if no match)';

-- ============================================================================
-- ANALYTICS VIEWS
-- ============================================================================

-- Top scorers from events
DROP VIEW IF EXISTS events.vw_top_scorers CASCADE;
CREATE VIEW events.vw_top_scorers AS
SELECT 
    player_name,
    position,
    goals_scored,
    assists_provided,
    match_appearances,
    goals_per_match,
    shots_accuracy,
    total_shots,
    shots_on_target
FROM events.player_event_statistics
WHERE goals_scored > 0
ORDER BY goals_scored DESC, assists_provided DESC
LIMIT 100;

COMMENT ON VIEW events.vw_top_scorers IS 'Top 100 goal scorers from match events';

-- Most disciplined/undisciplined players
DROP VIEW IF EXISTS events.vw_player_discipline CASCADE;
CREATE VIEW events.vw_player_discipline AS
SELECT 
    player_name,
    position,
    match_appearances,
    yellow_cards,
    red_cards,
    fouls_committed,
    ROUND(yellow_cards::DECIMAL / NULLIF(match_appearances, 0), 2) AS yellow_per_match,
    ROUND(red_cards::DECIMAL / NULLIF(match_appearances, 0), 3) AS red_per_match
FROM events.player_event_statistics
WHERE match_appearances >= 10
ORDER BY yellow_cards DESC, red_cards DESC;

COMMENT ON VIEW events.vw_player_discipline IS 'Player discipline statistics';

-- High-scoring matches
DROP VIEW IF EXISTS events.vw_high_scoring_matches CASCADE;
CREATE VIEW events.vw_high_scoring_matches AS
SELECT 
    mi.match_id,
    mi.match_date,
    mi.league,
    mi.home_team,
    mi.away_team,
    mi.home_goals,
    mi.away_goals,
    mi.total_goals,
    ms.total_shots,
    ms.shots_on_target,
    ms.shot_accuracy
FROM events.match_info mi
JOIN events.match_statistics ms ON mi.match_id = ms.match_id
WHERE mi.total_goals >= 5
ORDER BY mi.total_goals DESC, mi.match_date DESC;

COMMENT ON VIEW events.vw_high_scoring_matches IS 'Matches with 5+ goals';

-- ============================================================================
-- MATERIALIZED VIEW: League Performance
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS events.mvw_league_statistics CASCADE;
CREATE MATERIALIZED VIEW events.mvw_league_statistics AS
SELECT 
    mi.league,
    mi.country,
    COUNT(DISTINCT mi.match_id) AS total_matches,
    ROUND(AVG(mi.total_goals), 2) AS avg_goals_per_match,
    ROUND(AVG(ms.total_shots), 1) AS avg_shots_per_match,
    ROUND(AVG(ms.shot_accuracy), 1) AS avg_shot_accuracy,
    ROUND(AVG(ms.total_corners), 1) AS avg_corners_per_match,
    ROUND(AVG(ms.yellow_cards), 1) AS avg_yellow_cards,
    ROUND(AVG(ms.red_cards), 2) AS avg_red_cards
FROM events.match_info mi
JOIN events.match_statistics ms ON mi.match_id = ms.match_id
GROUP BY mi.league, mi.country
ORDER BY total_matches DESC;

CREATE INDEX idx_mvw_league_stats_league ON events.mvw_league_statistics(league);

COMMENT ON MATERIALIZED VIEW events.mvw_league_statistics IS 'Aggregated statistics by league';

-- ============================================================================
-- REFRESH FUNCTION FOR MATERIALIZED VIEWS
-- ============================================================================

CREATE OR REPLACE FUNCTION events.refresh_event_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY events.mvw_league_statistics;
    RAISE NOTICE 'Events materialized views refreshed';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION events.refresh_event_materialized_views() IS 'Refresh all events materialized views';

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT USAGE ON SCHEMA events TO postgres;
GRANT SELECT ON ALL TABLES IN SCHEMA events TO postgres;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA events TO postgres;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA events TO postgres;

-- ============================================================================
-- SUMMARY
-- ============================================================================

SELECT 'Events schema created successfully' AS status;
