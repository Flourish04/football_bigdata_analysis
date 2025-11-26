-- ==============================================================================
-- PostgreSQL DDL Schema for Football Analytics Data Warehouse
-- ==============================================================================
-- Created: 2025-11-25
-- Purpose: Define schema for Gold Layer analytics tables
-- Usage: psql -U postgres -d football_analytics -f schema/analytics_schema.sql
-- ==============================================================================

-- Create analytics schema
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO analytics, public;

-- ==============================================================================
-- TABLE: player_form_metrics
-- Description: Aggregated player performance metrics across all seasons
-- Source: Gold Layer - player_performances aggregation
-- ==============================================================================

CREATE TABLE IF NOT EXISTS analytics.player_form_metrics (
    player_id BIGINT PRIMARY KEY,
    
    -- Season Statistics
    total_seasons INTEGER NOT NULL DEFAULT 0,
    total_appearances INTEGER NOT NULL DEFAULT 0,
    total_minutes_played INTEGER NOT NULL DEFAULT 0,
    
    -- Goal & Assist Metrics
    total_goals INTEGER NOT NULL DEFAULT 0,
    total_assists INTEGER NOT NULL DEFAULT 0,
    goal_contributions INTEGER NOT NULL DEFAULT 0,
    avg_goals_per_season DECIMAL(10,2) DEFAULT 0.00,
    avg_assists_per_season DECIMAL(10,2) DEFAULT 0.00,
    best_goals_season INTEGER DEFAULT 0,
    best_assists_season INTEGER DEFAULT 0,
    
    -- Per 90 Minutes Metrics
    goals_per_90min DECIMAL(10,4) DEFAULT 0.0000,
    assists_per_90min DECIMAL(10,4) DEFAULT 0.0000,
    
    -- Discipline
    total_yellow_cards INTEGER NOT NULL DEFAULT 0,
    total_red_cards INTEGER NOT NULL DEFAULT 0,
    
    -- Metadata
    gold_processed_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_total_seasons_positive CHECK (total_seasons >= 0),
    CONSTRAINT chk_total_appearances_positive CHECK (total_appearances >= 0),
    CONSTRAINT chk_total_goals_positive CHECK (total_goals >= 0),
    CONSTRAINT chk_goals_per_90min_positive CHECK (goals_per_90min >= 0)
);

-- Indexes
CREATE INDEX idx_form_total_goals ON analytics.player_form_metrics(total_goals DESC);
CREATE INDEX idx_form_total_assists ON analytics.player_form_metrics(total_assists DESC);
CREATE INDEX idx_form_goal_contributions ON analytics.player_form_metrics(goal_contributions DESC);
CREATE INDEX idx_form_goals_per_90 ON analytics.player_form_metrics(goals_per_90min DESC);
CREATE INDEX idx_form_assists_per_90 ON analytics.player_form_metrics(assists_per_90min DESC);

COMMENT ON TABLE analytics.player_form_metrics IS 'Aggregated player performance metrics across all seasons';
COMMENT ON COLUMN analytics.player_form_metrics.goals_per_90min IS 'Goals scored per 90 minutes played';
COMMENT ON COLUMN analytics.player_form_metrics.goal_contributions IS 'Total goals + assists';


-- ==============================================================================
-- TABLE: market_value_trends
-- Description: Player market value trends and volatility analysis
-- Source: Gold Layer - player_market_value aggregation
-- ==============================================================================

CREATE TABLE IF NOT EXISTS analytics.market_value_trends (
    player_id BIGINT PRIMARY KEY,
    
    -- Market Value Statistics
    peak_market_value BIGINT NOT NULL DEFAULT 0,
    lowest_market_value BIGINT NOT NULL DEFAULT 0,
    avg_market_value BIGINT DEFAULT 0,
    value_volatility BIGINT NOT NULL DEFAULT 0,
    
    -- Data Quality
    value_records_count INTEGER NOT NULL DEFAULT 0,
    latest_valuation_timestamp DATE,
    
    -- Metadata
    gold_processed_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_peak_value_positive CHECK (peak_market_value >= 0),
    CONSTRAINT chk_lowest_value_positive CHECK (lowest_market_value >= 0),
    CONSTRAINT chk_peak_gte_lowest CHECK (peak_market_value >= lowest_market_value),
    CONSTRAINT chk_value_records_positive CHECK (value_records_count >= 0)
);

-- Indexes
CREATE INDEX idx_market_peak_value ON analytics.market_value_trends(peak_market_value DESC);
CREATE INDEX idx_market_avg_value ON analytics.market_value_trends(avg_market_value DESC);
CREATE INDEX idx_market_volatility ON analytics.market_value_trends(value_volatility DESC);
CREATE INDEX idx_market_latest_valuation ON analytics.market_value_trends(latest_valuation_timestamp DESC);

COMMENT ON TABLE analytics.market_value_trends IS 'Player market value trends and volatility analysis';
COMMENT ON COLUMN analytics.market_value_trends.value_volatility IS 'Difference between peak and lowest market value';
COMMENT ON COLUMN analytics.market_value_trends.latest_valuation_timestamp IS 'Date of most recent market valuation';


-- ==============================================================================
-- TABLE: injury_risk_scores
-- Description: Player injury history and risk assessment
-- Source: Gold Layer - player_injuries aggregation
-- ==============================================================================

CREATE TABLE IF NOT EXISTS analytics.injury_risk_scores (
    player_id BIGINT PRIMARY KEY,
    
    -- Injury Statistics
    total_injuries INTEGER NOT NULL DEFAULT 0,
    total_days_missed INTEGER NOT NULL DEFAULT 0,
    total_games_missed INTEGER NOT NULL DEFAULT 0,
    
    -- Average Metrics
    avg_days_per_injury DECIMAL(10,2) DEFAULT 0.00,
    avg_games_per_injury DECIMAL(10,2) DEFAULT 0.00,
    
    -- Severity Indicators
    longest_injury_days INTEGER DEFAULT 0,
    longest_injury_games INTEGER DEFAULT 0,
    
    -- Risk Assessment
    injury_severity_score DECIMAL(10,2) DEFAULT 0.00,
    injury_risk_level VARCHAR(20) DEFAULT 'LOW',
    
    -- Metadata
    gold_processed_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_total_injuries_positive CHECK (total_injuries >= 0),
    CONSTRAINT chk_total_days_missed_positive CHECK (total_days_missed >= 0),
    CONSTRAINT chk_injury_risk_level CHECK (injury_risk_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

-- Indexes
CREATE INDEX idx_injury_total_injuries ON analytics.injury_risk_scores(total_injuries DESC);
CREATE INDEX idx_injury_severity_score ON analytics.injury_risk_scores(injury_severity_score DESC);
CREATE INDEX idx_injury_risk_level ON analytics.injury_risk_scores(injury_risk_level);
CREATE INDEX idx_injury_days_missed ON analytics.injury_risk_scores(total_days_missed DESC);

COMMENT ON TABLE analytics.injury_risk_scores IS 'Player injury history and risk assessment';
COMMENT ON COLUMN analytics.injury_risk_scores.injury_severity_score IS 'Calculated risk score: (total_injuries * 5 + total_days_missed / 10) / 100';
COMMENT ON COLUMN analytics.injury_risk_scores.injury_risk_level IS 'Risk level: HIGH (>5), MEDIUM (>2), LOW (<=2)';


-- ==============================================================================
-- TABLE: transfer_intelligence
-- Description: Player transfer history and market intelligence
-- Source: Gold Layer - transfer_history aggregation
-- ==============================================================================

CREATE TABLE IF NOT EXISTS analytics.transfer_intelligence (
    player_id BIGINT PRIMARY KEY,
    
    -- Transfer Statistics
    total_transfers INTEGER NOT NULL DEFAULT 0,
    total_transfer_fees BIGINT DEFAULT 0,
    avg_transfer_fee BIGINT DEFAULT 0,
    highest_transfer_fee BIGINT DEFAULT 0,
    
    -- Market Value Comparison
    avg_value_at_transfer BIGINT DEFAULT 0,
    
    -- Transfer Patterns
    transfer_frequency DECIMAL(10,2) DEFAULT 0.00,
    transfer_value_trend VARCHAR(20) DEFAULT 'STABLE',
    last_transfer_date DATE,
    
    -- Metadata
    gold_processed_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_total_transfers_positive CHECK (total_transfers >= 0),
    CONSTRAINT chk_total_transfer_fees_positive CHECK (total_transfer_fees >= 0),
    CONSTRAINT chk_transfer_value_trend CHECK (transfer_value_trend IN ('PROFIT', 'LOSS', 'STABLE'))
);

-- Indexes
CREATE INDEX idx_transfer_total_fees ON analytics.transfer_intelligence(total_transfer_fees DESC);
CREATE INDEX idx_transfer_highest_fee ON analytics.transfer_intelligence(highest_transfer_fee DESC);
CREATE INDEX idx_transfer_frequency ON analytics.transfer_intelligence(transfer_frequency DESC);
CREATE INDEX idx_transfer_last_date ON analytics.transfer_intelligence(last_transfer_date DESC);
CREATE INDEX idx_transfer_value_trend ON analytics.transfer_intelligence(transfer_value_trend);

COMMENT ON TABLE analytics.transfer_intelligence IS 'Player transfer history and market intelligence';
COMMENT ON COLUMN analytics.transfer_intelligence.transfer_frequency IS 'Total transfers divided by 10 (normalized frequency)';
COMMENT ON COLUMN analytics.transfer_intelligence.transfer_value_trend IS 'PROFIT if total_transfer_fees > avg_value_at_transfer, else LOSS';


-- ==============================================================================
-- TABLE: player_analytics_360
-- Description: Comprehensive 360-degree player analytics combining all metrics
-- Source: Gold Layer - join of profiles + all analytics tables
-- ==============================================================================

CREATE TABLE IF NOT EXISTS analytics.player_analytics_360 (
    player_id BIGINT PRIMARY KEY,
    
    -- Player Profile
    player_name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    age INTEGER,
    player_main_position VARCHAR(50),
    citizenship VARCHAR(100),
    current_club_id BIGINT,
    height INTEGER,
    foot VARCHAR(20),
    
    -- Performance Metrics (from form_metrics)
    total_appearances INTEGER DEFAULT 0,
    total_goals INTEGER DEFAULT 0,
    total_assists INTEGER DEFAULT 0,
    goals_per_90min DECIMAL(10,4) DEFAULT 0.0000,
    assists_per_90min DECIMAL(10,4) DEFAULT 0.0000,
    goal_contributions INTEGER DEFAULT 0,
    avg_goals_per_season DECIMAL(10,2) DEFAULT 0.00,
    avg_assists_per_season DECIMAL(10,2) DEFAULT 0.00,
    
    -- Market Value Metrics (from market_trends)
    peak_market_value BIGINT DEFAULT 0,
    avg_market_value BIGINT DEFAULT 0,
    value_volatility BIGINT DEFAULT 0,
    latest_valuation_timestamp DATE,
    
    -- Injury Risk Metrics (from injury_risks)
    total_injuries INTEGER DEFAULT 0,
    total_days_missed INTEGER DEFAULT 0,
    injury_severity_score DECIMAL(10,2) DEFAULT 0.00,
    injury_risk_level VARCHAR(20) DEFAULT 'LOW',
    
    -- Transfer Metrics (from transfer_intel)
    total_transfers INTEGER DEFAULT 0,
    total_transfer_fees BIGINT DEFAULT 0,
    avg_transfer_fee BIGINT DEFAULT 0,
    last_transfer_date DATE,
    
    -- Composite Scores (0-100 scale)
    performance_score DECIMAL(10,2) DEFAULT 0.00,
    market_score DECIMAL(10,2) DEFAULT 0.00,
    health_score DECIMAL(10,2) DEFAULT 0.00,
    overall_player_score DECIMAL(10,2) DEFAULT 0.00,
    
    -- Rankings
    player_rank INTEGER,
    player_rank_percentile DECIMAL(5,2),
    
    -- Metadata
    gold_processed_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_age_reasonable CHECK (age IS NULL OR (age >= 14 AND age <= 80)),
    CONSTRAINT chk_height_reasonable CHECK (height IS NULL OR (height >= 150 AND height <= 220)),
    CONSTRAINT chk_performance_score_range CHECK (performance_score >= 0 AND performance_score <= 100),
    CONSTRAINT chk_market_score_range CHECK (market_score >= 0 AND market_score <= 100),
    CONSTRAINT chk_health_score_range CHECK (health_score >= 0 AND health_score <= 100),
    CONSTRAINT chk_overall_score_range CHECK (overall_player_score >= 0 AND overall_player_score <= 100),
    CONSTRAINT chk_percentile_range CHECK (player_rank_percentile IS NULL OR (player_rank_percentile >= 0 AND player_rank_percentile <= 100)),
    CONSTRAINT chk_injury_risk_level_360 CHECK (injury_risk_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

-- Indexes for player_analytics_360
CREATE INDEX idx_360_player_name ON analytics.player_analytics_360(player_name);
CREATE INDEX idx_360_position ON analytics.player_analytics_360(player_main_position);
CREATE INDEX idx_360_age ON analytics.player_analytics_360(age);
CREATE INDEX idx_360_current_club ON analytics.player_analytics_360(current_club_id);
CREATE INDEX idx_360_overall_score ON analytics.player_analytics_360(overall_player_score DESC);
CREATE INDEX idx_360_performance_score ON analytics.player_analytics_360(performance_score DESC);
CREATE INDEX idx_360_market_score ON analytics.player_analytics_360(market_score DESC);
CREATE INDEX idx_360_health_score ON analytics.player_analytics_360(health_score DESC);
CREATE INDEX idx_360_player_rank ON analytics.player_analytics_360(player_rank);
CREATE INDEX idx_360_peak_value ON analytics.player_analytics_360(peak_market_value DESC);
CREATE INDEX idx_360_total_goals ON analytics.player_analytics_360(total_goals DESC);
CREATE INDEX idx_360_injury_risk ON analytics.player_analytics_360(injury_risk_level);

COMMENT ON TABLE analytics.player_analytics_360 IS 'Comprehensive 360-degree player analytics combining all metrics from profiles, performance, market value, injury risk, and transfer intelligence';
COMMENT ON COLUMN analytics.player_analytics_360.overall_player_score IS 'Composite score combining performance, market value, and health metrics (0-100 scale)';
COMMENT ON COLUMN analytics.player_analytics_360.player_rank IS 'Global ranking based on overall_player_score';
COMMENT ON COLUMN analytics.player_analytics_360.player_rank_percentile IS 'Percentile ranking (0-100)';


-- ==============================================================================
-- FOREIGN KEY CONSTRAINTS
-- ==============================================================================

-- Note: Foreign keys reference player_analytics_360 as the master dimension table
-- Uncomment these if you want enforced referential integrity:

-- ALTER TABLE analytics.player_form_metrics
--     ADD CONSTRAINT fk_form_player 
--     FOREIGN KEY (player_id) 
--     REFERENCES analytics.player_analytics_360(player_id) 
--     ON DELETE CASCADE;

-- ALTER TABLE analytics.market_value_trends
--     ADD CONSTRAINT fk_market_player 
--     FOREIGN KEY (player_id) 
--     REFERENCES analytics.player_analytics_360(player_id) 
--     ON DELETE CASCADE;

-- ALTER TABLE analytics.injury_risk_scores
--     ADD CONSTRAINT fk_injury_player 
--     FOREIGN KEY (player_id) 
--     REFERENCES analytics.player_analytics_360(player_id) 
--     ON DELETE CASCADE;

-- ALTER TABLE analytics.transfer_intelligence
--     ADD CONSTRAINT fk_transfer_player 
--     FOREIGN KEY (player_id) 
--     REFERENCES analytics.player_analytics_360(player_id) 
--     ON DELETE CASCADE;


-- ==============================================================================
-- VIEWS FOR COMMON QUERIES
-- ==============================================================================

-- Top performing players by overall score
CREATE OR REPLACE VIEW analytics.vw_top_players AS
SELECT 
    player_id,
    player_name,
    age,
    player_main_position,
    overall_player_score,
    performance_score,
    market_score,
    health_score,
    player_rank,
    peak_market_value,
    total_goals,
    total_assists,
    injury_risk_level
FROM analytics.player_analytics_360
WHERE overall_player_score > 0
ORDER BY overall_player_score DESC
LIMIT 100;

COMMENT ON VIEW analytics.vw_top_players IS 'Top 100 players ranked by overall player score';


-- High-value players with low injury risk
CREATE OR REPLACE VIEW analytics.vw_high_value_low_risk_players AS
SELECT 
    player_id,
    player_name,
    age,
    player_main_position,
    peak_market_value,
    avg_market_value,
    injury_risk_level,
    total_injuries,
    total_goals,
    total_assists,
    overall_player_score
FROM analytics.player_analytics_360
WHERE 
    peak_market_value > 10000000  -- > 10M EUR
    AND injury_risk_level = 'LOW'
    AND age BETWEEN 20 AND 30
ORDER BY peak_market_value DESC;

COMMENT ON VIEW analytics.vw_high_value_low_risk_players IS 'High-value players (>10M EUR) with low injury risk, aged 20-30';


-- Transfer market opportunities
CREATE OR REPLACE VIEW analytics.vw_transfer_opportunities AS
SELECT 
    pa.player_id,
    pa.player_name,
    pa.age,
    pa.player_main_position,
    pa.peak_market_value,
    pa.total_goals,
    pa.goals_per_90min,
    ti.total_transfers,
    ti.avg_transfer_fee,
    ti.transfer_value_trend,
    pa.injury_risk_level,
    pa.overall_player_score
FROM analytics.player_analytics_360 pa
JOIN analytics.transfer_intelligence ti ON pa.player_id = ti.player_id
WHERE 
    pa.age BETWEEN 20 AND 28
    AND pa.injury_risk_level IN ('LOW', 'MEDIUM')
    AND ti.transfer_value_trend = 'PROFIT'
    AND pa.overall_player_score > 50
ORDER BY pa.overall_player_score DESC;

COMMENT ON VIEW analytics.vw_transfer_opportunities IS 'Players with strong performance, positive transfer trends, and manageable injury risk';


-- ==============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ==============================================================================

-- Position-based statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mvw_position_statistics AS
SELECT 
    player_main_position,
    COUNT(*) as total_players,
    AVG(overall_player_score) as avg_overall_score,
    AVG(peak_market_value) as avg_peak_value,
    AVG(total_goals) as avg_goals,
    AVG(total_assists) as avg_assists,
    AVG(goals_per_90min) as avg_goals_per_90,
    AVG(age) as avg_age,
    SUM(CASE WHEN injury_risk_level = 'HIGH' THEN 1 ELSE 0 END) as high_risk_count,
    SUM(CASE WHEN injury_risk_level = 'MEDIUM' THEN 1 ELSE 0 END) as medium_risk_count,
    SUM(CASE WHEN injury_risk_level = 'LOW' THEN 1 ELSE 0 END) as low_risk_count
FROM analytics.player_analytics_360
WHERE player_main_position IS NOT NULL
GROUP BY player_main_position;

CREATE UNIQUE INDEX idx_mvw_position ON analytics.mvw_position_statistics(player_main_position);

COMMENT ON MATERIALIZED VIEW analytics.mvw_position_statistics IS 'Aggregated statistics by player position - refresh periodically';


-- Age group analysis
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mvw_age_group_analysis AS
SELECT 
    CASE 
        WHEN age < 21 THEN 'U21'
        WHEN age BETWEEN 21 AND 25 THEN '21-25'
        WHEN age BETWEEN 26 AND 30 THEN '26-30'
        WHEN age BETWEEN 31 AND 35 THEN '31-35'
        WHEN age > 35 THEN '35+'
        ELSE 'Unknown'
    END as age_group,
    COUNT(*) as total_players,
    AVG(overall_player_score) as avg_overall_score,
    AVG(peak_market_value) as avg_peak_value,
    AVG(total_goals) as avg_goals,
    AVG(injury_severity_score) as avg_injury_score,
    AVG(total_transfers) as avg_transfers
FROM analytics.player_analytics_360
WHERE age IS NOT NULL
GROUP BY 
    CASE 
        WHEN age < 21 THEN 'U21'
        WHEN age BETWEEN 21 AND 25 THEN '21-25'
        WHEN age BETWEEN 26 AND 30 THEN '26-30'
        WHEN age BETWEEN 31 AND 35 THEN '31-35'
        WHEN age > 35 THEN '35+'
        ELSE 'Unknown'
    END;

CREATE UNIQUE INDEX idx_mvw_age_group ON analytics.mvw_age_group_analysis(age_group);

COMMENT ON MATERIALIZED VIEW analytics.mvw_age_group_analysis IS 'Player statistics grouped by age ranges';


-- ==============================================================================
-- REFRESH FUNCTIONS FOR MATERIALIZED VIEWS
-- ==============================================================================

CREATE OR REPLACE FUNCTION analytics.refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mvw_position_statistics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mvw_age_group_analysis;
    RAISE NOTICE 'All materialized views refreshed successfully';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_all_materialized_views() IS 'Refresh all materialized views in analytics schema';


-- ==============================================================================
-- GRANTS (adjust based on your user roles)
-- ==============================================================================

-- Grant usage on schema
-- GRANT USAGE ON SCHEMA analytics TO analytics_user;

-- Grant select on all tables
-- GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO analytics_user;

-- Grant select on all views
-- GRANT SELECT ON ALL VIEWS IN SCHEMA analytics TO analytics_user;

-- Grant execute on functions
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA analytics TO analytics_user;


-- ==============================================================================
-- MAINTENANCE QUERIES
-- ==============================================================================

-- Show table sizes
/*
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'analytics'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
*/

-- Show row counts
/*
SELECT 
    'player_form_metrics' as table_name, COUNT(*) as row_count FROM analytics.player_form_metrics
UNION ALL
SELECT 'market_value_trends', COUNT(*) FROM analytics.market_value_trends
UNION ALL
SELECT 'injury_risk_scores', COUNT(*) FROM analytics.injury_risk_scores
UNION ALL
SELECT 'transfer_intelligence', COUNT(*) FROM analytics.transfer_intelligence
UNION ALL
SELECT 'player_analytics_360', COUNT(*) FROM analytics.player_analytics_360;
*/


-- ==============================================================================
-- END OF SCHEMA DEFINITION
-- ==============================================================================

-- Print completion message
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Football Analytics Schema Created Successfully';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Schema: analytics';
    RAISE NOTICE 'Tables: 5';
    RAISE NOTICE 'Views: 3';
    RAISE NOTICE 'Materialized Views: 2';
    RAISE NOTICE '========================================';
END $$;
