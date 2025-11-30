-- ==============================================================================
-- Create Views and Materialized Views Only
-- ==============================================================================
-- Purpose: Create views and materialized views for existing analytics tables
-- Usage: psql -U postgres -d football_analytics -f schema/create_views_only.sql
-- ==============================================================================

-- Set search path
SET search_path TO analytics, public;

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
    latest_market_value,
    latest_valuation_timestamp,
    total_goals,
    total_assists,
    injury_risk_level
FROM analytics.player_analytics_360
WHERE overall_player_score > 0
ORDER BY overall_player_score DESC
LIMIT 100;

COMMENT ON VIEW analytics.vw_top_players IS 'Top 100 players ranked by overall player score. Market values in EUR (raw values, e.g., 100000000 = €100M)';


-- High-value players with low injury risk
CREATE OR REPLACE VIEW analytics.vw_high_value_low_risk_players AS
SELECT 
    player_id,
    player_name,
    age,
    player_main_position,
    peak_market_value,
    latest_market_value,
    latest_valuation_timestamp,
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

COMMENT ON VIEW analytics.vw_high_value_low_risk_players IS 'High-value players (>10M EUR) with low injury risk, aged 20-30. Market values in EUR (raw values, e.g., 100000000 = €100M)';


-- Transfer market opportunities
CREATE OR REPLACE VIEW analytics.vw_transfer_opportunities AS
SELECT 
    pa.player_id,
    pa.player_name,
    pa.age,
    pa.player_main_position,
    pa.peak_market_value,  -- EUR (raw value, no division)
    pa.latest_market_value,  -- EUR (raw value, no division)
    pa.latest_valuation_timestamp,
    pa.avg_market_value,  -- EUR (raw value, no division)
    (pa.latest_market_value - pa.avg_market_value) as value_growth,  -- EUR (raw value)
    pa.total_goals,
    pa.goals_per_90min,
    ti.total_transfers,
    ti.avg_transfer_fee,
    ti.transfer_value_trend,
    pa.injury_risk_level,
    pa.overall_player_score,
    -- Calculate opportunity score (0-100)
    CASE 
        WHEN pa.latest_market_value > 0 THEN
            LEAST(100, GREATEST(0,
                (pa.overall_player_score * 0.4) +
                (CASE WHEN ti.transfer_value_trend = 'PROFIT' THEN 20 ELSE 0 END) +
                (CASE WHEN pa.injury_risk_level = 'LOW' THEN 20 
                      WHEN pa.injury_risk_level = 'MEDIUM' THEN 10 
                      ELSE 0 END) +
                (CASE WHEN pa.age BETWEEN 22 AND 26 THEN 20 
                      WHEN pa.age BETWEEN 20 AND 28 THEN 15 
                      ELSE 5 END)
            ))
        ELSE 0
    END as opportunity_score
FROM analytics.player_analytics_360 pa
JOIN analytics.transfer_intelligence ti ON pa.player_id = ti.player_id
WHERE 
    pa.age BETWEEN 20 AND 28
    AND pa.injury_risk_level IN ('LOW', 'MEDIUM')
    AND ti.transfer_value_trend = 'PROFIT'
    AND pa.overall_player_score > 50
    AND pa.latest_market_value > 0
ORDER BY opportunity_score DESC, pa.overall_player_score DESC;

COMMENT ON VIEW analytics.vw_transfer_opportunities IS 'Players with strong performance, positive transfer trends, and manageable injury risk. Includes opportunity_score (0-100) based on performance, age, risk, and transfer trend. Market values in EUR (raw values, e.g., 100000000 = €100M)';


-- ==============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ==============================================================================

-- Position-based statistics
DROP MATERIALIZED VIEW IF EXISTS analytics.mvw_position_statistics CASCADE;
CREATE MATERIALIZED VIEW analytics.mvw_position_statistics AS
SELECT 
    player_main_position,
    COUNT(*) as total_players,
    AVG(overall_player_score) as avg_overall_score,
    AVG(peak_market_value) as avg_peak_market_value,
    AVG(latest_market_value) as avg_latest_market_value,
    AVG(avg_market_value) as avg_market_value,
    AVG(total_goals) as avg_goals,
    AVG(total_assists) as avg_assists,
    AVG(goals_per_90min) as avg_goals_per_90min,
    AVG(assists_per_90min) as avg_assists_per_90min,
    AVG(age) as avg_age,
    SUM(CASE WHEN injury_risk_level = 'HIGH' THEN 1 ELSE 0 END) as high_risk_count,
    SUM(CASE WHEN injury_risk_level = 'MEDIUM' THEN 1 ELSE 0 END) as medium_risk_count,
    SUM(CASE WHEN injury_risk_level = 'LOW' THEN 1 ELSE 0 END) as low_risk_count
FROM analytics.player_analytics_360
WHERE player_main_position IS NOT NULL
GROUP BY player_main_position;

CREATE UNIQUE INDEX idx_mvw_position ON analytics.mvw_position_statistics(player_main_position);

COMMENT ON MATERIALIZED VIEW analytics.mvw_position_statistics IS 'Aggregated statistics by player position - refresh periodically. Market values in EUR (raw values, e.g., 100000000 = €100M)';


-- Age group analysis
DROP MATERIALIZED VIEW IF EXISTS analytics.mvw_age_group_analysis CASCADE;
CREATE MATERIALIZED VIEW analytics.mvw_age_group_analysis AS
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
    AVG(peak_market_value) as avg_peak_market_value,
    AVG(latest_market_value) as avg_latest_market_value,
    AVG(avg_market_value) as avg_market_value,
    AVG(total_goals) as avg_goals,
    AVG(total_assists) as avg_assists,
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
-- Print completion message
-- ==============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Views and Materialized Views Created Successfully';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Regular Views: 3';
    RAISE NOTICE 'Materialized Views: 2';
    RAISE NOTICE 'Refresh Function: 1';
    RAISE NOTICE '========================================';
END $$;
