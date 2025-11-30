# 📊 Database Schema Diagrams

## Table of Contents
- [Silver Layer Schema](#silver-layer-schema)
- [Gold Layer Analytics Schema](#gold-layer-analytics-schema)
- [Streaming Schema](#streaming-schema)
- [Complete System Overview](#complete-system-overview)

---

## Silver Layer Schema

### Player-Related Tables

```mermaid
erDiagram
    PLAYER_PROFILES {
        varchar player_id PK
        varchar player_slug
        varchar player_name
        varchar player_image_url
        varchar date_of_birth_url
        date date_of_birth
        varchar place_of_birth_country
        varchar place_of_birth
        varchar height
        varchar citizenship_country
        varchar citizenship
        varchar position
        varchar foot
        varchar player_agent_url
        varchar player_agent
        varchar current_club_id FK
        varchar current_club_url
        date joined
        date contract_expires
        varchar social_media_url
        varchar social_media
        varchar player_main_position
        varchar player_sub_position
    }

    PLAYER_MARKET_VALUES {
        varchar player_id FK
        bigint date_unix PK
        int value
        date value_date
    }

    PLAYER_LATEST_MARKET_VALUES {
        varchar player_id PK
        int latest_market_value
        date value_date
    }

    PLAYER_TRANSFER_HISTORIES {
        varchar transfer_id PK
        varchar player_id FK
        varchar season
        date date
        varchar date_unformatted
        varchar from_team_id FK
        varchar from_team_url
        varchar from_team_name
        varchar to_team_id FK
        varchar to_team_url
        varchar to_team_name
        int value_at_transfer
        varchar transfer_fee
    }

    PLAYER_PERFORMANCES {
        varchar player_id FK
        varchar season
        varchar competition_id FK
        varchar competition_url
        varchar competition_name
        varchar team_id FK
        varchar team_url
        varchar team_name
        int nb_in_group
        int nb_on_pitch
        int goals
        int own_goals
        int assists
        int subed_in
        int subed_out
        int yellow_cards
        int second_yellow_cards
        int direct_red_cards
        int penalty_goals
        int minutes_played
        int goals_conceded
        int clean_sheets
    }

    PLAYER_TEAMMATES_PLAYED_WITH {
        varchar player_id FK
        varchar teammate_id FK
        varchar player_with_url
        varchar player_with_name
        float ppg_played_with
        int joint_goal_participation
        int minutes_played_with
    }

    PLAYER_INJURY_HISTORIES {
        varchar player_id FK
        varchar season
        varchar injury_reason
        date from_date PK
        date end_date
        int days_missed
        int games_missed
    }

    PLAYER_NATIONAL_TEAM_PERFORMANCES {
        varchar player_id FK
        varchar team_id FK
        varchar team_url
        varchar team_name
        date first_game_date PK
        int matches
        int goals
    }

    %% Player Relationships
    PLAYER_PROFILES ||--o{ PLAYER_MARKET_VALUES : "has historical values"
    PLAYER_PROFILES ||--|| PLAYER_LATEST_MARKET_VALUES : "has current value"
    PLAYER_PROFILES ||--o{ PLAYER_TRANSFER_HISTORIES : "has transfers"
    PLAYER_PROFILES ||--o{ PLAYER_PERFORMANCES : "has performances"
    PLAYER_PROFILES ||--o{ PLAYER_TEAMMATES_PLAYED_WITH : "played with teammates"
    PLAYER_PROFILES ||--o{ PLAYER_INJURY_HISTORIES : "has injuries"
    PLAYER_PROFILES ||--o{ PLAYER_NATIONAL_TEAM_PERFORMANCES : "national team caps"
```

### Team and Competition Tables

```mermaid
erDiagram
    TEAMS_DETAILS {
        varchar club_id PK
        varchar club_slug
        varchar club_name
        varchar logo_url
        varchar country_name
        varchar season_id
        varchar competition_id FK
        varchar competition_slug
        varchar competition_name
        varchar club_division
        varchar source_url
    }

    TEAMS_CHILDREN {
        varchar parent_team_id FK
        varchar parent_team_name
        varchar child_team_id FK
        varchar child_team_name
    }

    TEAMS_COMPETITIONS_SEASONS {
        varchar club_division
        varchar club_id FK
        varchar competition_id FK
        varchar competition_name
        int season_draws
        int season_goal_difference
        int season_goals_against
        int season_goals_for
        varchar season_id
        boolean season_is_two_point_system
        varchar season_league_competition_id
        varchar season_league_league_name
        varchar season_league_league_slug
        varchar season_league_level_level_name
        int season_league_level_level_number
        varchar season_league_season_id
        int season_losses
        varchar season_manager
        varchar season_manager_manager_id
        varchar season_manager_manager_name
        varchar season_manager_manager_slug
        int season_points
        int season_points_against
        int season_points_for
        int season_rank
        varchar season_season
        int season_total_matches
        int season_wins
        varchar team_name
    }

    COMPETITIONS {
        varchar competition_id PK
        varchar competition_slug
        varchar competition_name
    }

    %% Team Relationships
    TEAMS_DETAILS ||--o{ TEAMS_CHILDREN : "has youth teams"
    TEAMS_DETAILS ||--o{ TEAMS_COMPETITIONS_SEASONS : "participates in seasons"
    COMPETITIONS ||--o{ TEAMS_DETAILS : "includes teams"
    COMPETITIONS ||--o{ TEAMS_COMPETITIONS_SEASONS : "season records"
```

### Integrated Silver Layer Schema

```mermaid
erDiagram
    PLAYER_PROFILES {
        varchar player_id PK
        varchar player_name
        varchar position
        varchar current_club_id FK
        date date_of_birth
        varchar citizenship
    }

    PLAYER_PERFORMANCES {
        varchar player_id FK
        varchar competition_id FK
        varchar team_id FK
        int goals
        int assists
        int minutes_played
    }

    PLAYER_TRANSFER_HISTORIES {
        varchar transfer_id PK
        varchar player_id FK
        varchar from_team_id FK
        varchar to_team_id FK
        int value_at_transfer
    }

    TEAMS_DETAILS {
        varchar club_id PK
        varchar club_name
        varchar competition_id FK
        varchar country_name
    }

    COMPETITIONS {
        varchar competition_id PK
        varchar competition_name
    }

    PLAYER_INJURY_HISTORIES {
        varchar player_id FK
        date from_date PK
        int days_missed
        int games_missed
    }

    PLAYER_MARKET_VALUES {
        varchar player_id FK
        bigint date_unix PK
        int value
    }

    %% Cross-entity Relationships
    PLAYER_PROFILES ||--o{ PLAYER_PERFORMANCES : "performs in"
    PLAYER_PROFILES ||--o{ PLAYER_TRANSFER_HISTORIES : "transferred"
    PLAYER_PROFILES ||--o{ PLAYER_INJURY_HISTORIES : "injured"
    PLAYER_PROFILES ||--o{ PLAYER_MARKET_VALUES : "valued at"
    
    TEAMS_DETAILS ||--o{ PLAYER_PROFILES : "current club"
    TEAMS_DETAILS ||--o{ PLAYER_PERFORMANCES : "team performance"
    TEAMS_DETAILS ||--o{ PLAYER_TRANSFER_HISTORIES : "from/to team"
    
    COMPETITIONS ||--o{ TEAMS_DETAILS : "competes in"
    COMPETITIONS ||--o{ PLAYER_PERFORMANCES : "competition stats"
```

---

## Gold Layer Analytics Schema

### Analytics 360° Tables

```mermaid
erDiagram
    PLAYER_ANALYTICS_360 {
        varchar player_id PK
        varchar player_name
        varchar position
        varchar current_team
        float overall_player_score
        int peak_market_value
        int current_market_value
        int total_career_goals
        int total_career_assists
        int total_career_minutes
        int total_seasons_played
        int total_clubs_played_for
        float career_goals_per_90
        float career_assists_per_90
        int total_injuries
        int total_days_injured
        float avg_days_per_injury
        int total_transfers
        int total_transfer_value
        varchar age_group
        varchar value_category
        varchar scouting_recommendation
    }

    PLAYER_FORM_METRICS {
        varchar player_id PK
        varchar player_name
        varchar position
        varchar current_team
        int last_season_goals
        int last_season_assists
        int last_season_minutes
        float last_season_goals_per_90
        float last_season_assists_per_90
        float last_season_goal_participation
        int last_3_seasons_goals
        int last_3_seasons_assists
        int last_3_seasons_minutes
        float performance_consistency_score
        varchar form_status
        int yellow_cards
        int red_cards
        float disciplinary_score
    }

    MARKET_VALUE_TRENDS {
        varchar player_id PK
        varchar player_name
        varchar position
        int current_market_value
        int peak_market_value
        date peak_value_date
        int value_change_1y
        int value_change_3y
        float value_growth_rate_1y
        float value_growth_rate_3y
        int value_volatility_score
        varchar market_trend
        varchar investment_recommendation
    }

    INJURY_RISK_SCORES {
        varchar player_id PK
        varchar player_name
        varchar position
        int total_injuries
        int total_days_injured
        float avg_days_per_injury
        int injuries_last_3y
        int days_injured_last_3y
        date last_injury_date
        varchar last_injury_reason
        float injury_frequency_score
        float injury_severity_score
        float overall_injury_risk_score
        varchar risk_category
        float availability_percentage
    }

    TRANSFER_INTELLIGENCE {
        varchar transfer_id PK
        varchar player_id FK
        varchar player_name
        varchar from_team
        varchar to_team
        date transfer_date
        int transfer_fee
        int value_at_transfer
        int market_value_before
        int market_value_after
        float transfer_value_ratio
        varchar transfer_type
        varchar deal_quality
        int age_at_transfer
        varchar career_stage
    }

    %% Analytics Relationships
    PLAYER_ANALYTICS_360 ||--|| PLAYER_FORM_METRICS : "same player"
    PLAYER_ANALYTICS_360 ||--|| MARKET_VALUE_TRENDS : "same player"
    PLAYER_ANALYTICS_360 ||--|| INJURY_RISK_SCORES : "same player"
    PLAYER_ANALYTICS_360 ||--o{ TRANSFER_INTELLIGENCE : "player transfers"
```

### Analytics Views

```mermaid
erDiagram
    VW_TOP_PLAYERS {
        varchar player_id PK
        varchar player_name
        float overall_player_score
        int current_market_value
        varchar position
        varchar current_team
        int total_career_goals
        int total_career_assists
        varchar scouting_recommendation
    }

    VW_HIGH_VALUE_LOW_RISK_PLAYERS {
        varchar player_id PK
        varchar player_name
        int current_market_value
        float overall_player_score
        float injury_risk_score
        int total_injuries
        varchar position
        varchar risk_category
        varchar investment_recommendation
    }

    VW_TRANSFER_OPPORTUNITIES {
        varchar player_id PK
        varchar player_name
        int current_market_value
        float value_growth_rate_1y
        float overall_player_score
        int last_season_goals
        int last_season_assists
        varchar position
        varchar market_trend
        varchar deal_quality_potential
    }

    MVW_POSITION_STATISTICS {
        varchar position PK
        int total_players
        float avg_overall_score
        int avg_market_value
        float avg_goals_per_90
        float avg_assists_per_90
        float avg_injury_risk
        int total_transfers
        bigint total_transfer_value
    }

    MVW_AGE_GROUP_ANALYSIS {
        varchar age_group PK
        int total_players
        float avg_overall_score
        int avg_market_value
        float avg_goals_per_90
        int total_injuries
        float avg_injury_risk
        varchar most_common_position
    }

    MVW_LEAGUE_STATISTICS {
        varchar competition_name PK
        int total_teams
        int total_players
        int total_goals
        int total_assists
        float avg_goals_per_match
        float avg_market_value_per_player
        int total_transfers
        bigint total_transfer_spending
    }

    %% View Relationships (logical)
    VW_TOP_PLAYERS ||--o| PLAYER_ANALYTICS_360 : "derives from"
    VW_HIGH_VALUE_LOW_RISK_PLAYERS ||--o| PLAYER_ANALYTICS_360 : "derives from"
    VW_HIGH_VALUE_LOW_RISK_PLAYERS ||--o| INJURY_RISK_SCORES : "derives from"
    VW_TRANSFER_OPPORTUNITIES ||--o| MARKET_VALUE_TRENDS : "derives from"
```

---

## Streaming Schema

### Real-Time Streaming Tables

```mermaid
erDiagram
    FOOTBALL_MATCHES {
        int match_id PK
        int competition_id FK
        varchar competition_name
        varchar competition_code
        varchar competition_type
        varchar competition_emblem
        int season_id
        int current_matchday
        varchar home_team_id FK
        varchar home_team_name
        varchar home_team_short_name
        varchar home_team_tla
        varchar home_team_crest
        varchar away_team_id FK
        varchar away_team_name
        varchar away_team_short_name
        varchar away_team_tla
        varchar away_team_crest
        timestamp utc_date
        varchar status
        int matchday
        varchar stage
        varchar group_name
        timestamp last_updated
        varchar venue
        int minute
        varchar injuryTime
        int ht_home_goals
        int ht_away_goals
        int ft_home_goals
        int ft_away_goals
        int et_home_goals
        int et_away_goals
        int pen_home_goals
        int pen_away_goals
        varchar winner
        varchar duration
        jsonb match_data
        timestamp created_at
        timestamp updated_at
    }

    COMPETITIONS_STREAMING {
        int competition_id PK
        varchar code
        varchar name
        varchar type
        varchar emblem
        jsonb competition_data
        timestamp created_at
        timestamp updated_at
    }

    LEADERBOARDS_STREAMING {
        int competition_id FK
        int season_id
        int stage_id
        varchar stage_type
        varchar stage_start_date
        varchar stage_end_date
        jsonb standings_data
        timestamp created_at
        timestamp updated_at
    }

    MATCHES_STAGING {
        int match_id PK
        varchar status
        jsonb match_data
        timestamp processing_timestamp
    }

    COMPETITIONS_STAGING {
        int competition_id PK
        jsonb competition_data
        timestamp processing_timestamp
    }

    LEADERBOARDS_STAGING {
        int competition_id PK
        int season_id
        jsonb standings_data
        timestamp processing_timestamp
    }

    %% Streaming Relationships
    COMPETITIONS_STREAMING ||--o{ FOOTBALL_MATCHES : "competition has matches"
    COMPETITIONS_STREAMING ||--o{ LEADERBOARDS_STREAMING : "competition has standings"
    MATCHES_STAGING ||--|| FOOTBALL_MATCHES : "staged then loaded"
    COMPETITIONS_STAGING ||--|| COMPETITIONS_STREAMING : "staged then loaded"
    LEADERBOARDS_STAGING ||--|| LEADERBOARDS_STREAMING : "staged then loaded"
```

### Streaming Views

```mermaid
erDiagram
    VW_CURRENT_LIVE_MATCHES {
        int match_id PK
        varchar competition_name
        varchar home_team_name
        varchar away_team_name
        int ft_home_goals
        int ft_away_goals
        varchar status
        int minute
        timestamp utc_date
        varchar venue
    }

    VW_MATCH_SCORE_PROGRESSION {
        int match_id PK
        varchar home_team_name
        varchar away_team_name
        int ht_home_goals
        int ht_away_goals
        int ft_home_goals
        int ft_away_goals
        int et_home_goals
        int et_away_goals
        varchar status
        varchar winner
    }

    VW_COMPETITION_LIVE_STANDINGS {
        int competition_id FK
        varchar competition_name
        int season_id
        varchar team_name
        int position
        int played_games
        int won
        int draw
        int lost
        int points
        int goals_for
        int goals_against
        int goal_difference
    }

    %% Streaming View Relationships
    VW_CURRENT_LIVE_MATCHES ||--o| FOOTBALL_MATCHES : "filters live status"
    VW_MATCH_SCORE_PROGRESSION ||--o| FOOTBALL_MATCHES : "shows score timeline"
    VW_COMPETITION_LIVE_STANDINGS ||--o| LEADERBOARDS_STREAMING : "parses standings JSON"
    VW_COMPETITION_LIVE_STANDINGS }o--|| COMPETITIONS_STREAMING : "joins competition info"
```

---

## Complete System Overview

### Data Flow Architecture

```mermaid
erDiagram
    %% Source Layer
    CSV_FILES {
        varchar source_file
        int record_count
        varchar format
    }

    %% Bronze Layer
    BRONZE_PARQUET {
        varchar table_name
        int record_count
        timestamp ingestion_time
        varchar file_path
    }

    %% Silver Layer
    SILVER_PARQUET {
        varchar table_name
        int record_count
        timestamp cleaning_time
        float data_quality_score
    }

    SILVER_POSTGRES {
        varchar schema_name
        varchar table_name
        int record_count
        int index_count
    }

    %% Gold Layer
    GOLD_PARQUET {
        varchar table_name
        int record_count
        timestamp aggregation_time
    }

    GOLD_POSTGRES {
        varchar schema_name
        varchar table_name
        int record_count
        varchar view_type
    }

    %% Streaming Layer
    KAFKA_TOPICS {
        varchar topic_name PK
        int partition_count
        varchar retention_policy
    }

    STREAMING_POSTGRES {
        varchar schema_name
        varchar table_name
        varchar trigger_interval
        jsonb metadata
    }

    %% Data Flow
    CSV_FILES ||--|| BRONZE_PARQUET : "ingested to"
    BRONZE_PARQUET ||--|| SILVER_PARQUET : "cleaned to"
    SILVER_PARQUET ||--|| SILVER_POSTGRES : "loaded to"
    SILVER_POSTGRES ||--|| GOLD_PARQUET : "aggregated to"
    GOLD_PARQUET ||--|| GOLD_POSTGRES : "loaded to"
    
    KAFKA_TOPICS ||--|| STREAMING_POSTGRES : "streamed to"
    SILVER_POSTGRES ||--o{ GOLD_POSTGRES : "joined with"
    STREAMING_POSTGRES ||--o{ GOLD_POSTGRES : "integrated with"
```

### Schema Organization

```mermaid
erDiagram
    SCHEMA_SILVER {
        varchar schema_name "silver"
        int total_tables "10"
        int total_records "5535614"
        varchar storage_type "Parquet + PostgreSQL"
    }

    SCHEMA_GOLD {
        varchar schema_name "analytics"
        int total_tables "5"
        int total_records "402992"
        varchar storage_type "Parquet + PostgreSQL"
    }

    SCHEMA_STREAMING {
        varchar schema_name "streaming"
        int total_tables "6"
        int total_records "342"
        varchar storage_type "PostgreSQL JSONB"
    }

    SCHEMA_VIEWS {
        varchar schema_name "analytics"
        int total_views "5"
        int total_materialized_views "3"
        varchar refresh_strategy "On-demand"
    }

    %% Schema Relationships
    SCHEMA_SILVER ||--|| SCHEMA_GOLD : "feeds analytics"
    SCHEMA_STREAMING ||--o{ SCHEMA_VIEWS : "provides real-time data"
    SCHEMA_GOLD ||--|| SCHEMA_VIEWS : "provides aggregated data"
```

---

## Index and Constraint Overview

### Performance Optimization

```mermaid
erDiagram
    INDEXES_SILVER {
        varchar table_name
        varchar index_name PK
        varchar index_type
        varchar columns
        boolean is_unique
    }

    INDEXES_GOLD {
        varchar table_name
        varchar index_name PK
        varchar index_type
        varchar columns
        boolean is_unique
    }

    INDEXES_STREAMING {
        varchar table_name
        varchar index_name PK
        varchar index_type
        varchar columns
        boolean is_unique
    }

    CONSTRAINTS {
        varchar table_name
        varchar constraint_name PK
        varchar constraint_type
        varchar columns
        varchar referenced_table
    }

    %% Performance Features
    INDEXES_SILVER ||--o{ CONSTRAINTS : "enforces with"
    INDEXES_GOLD ||--o{ CONSTRAINTS : "enforces with"
    INDEXES_STREAMING ||--o{ CONSTRAINTS : "enforces with"
```

---

## Summary Statistics

| Layer | Schema | Tables | Records | Indexes | Views | Storage |
|-------|--------|--------|---------|---------|-------|---------|
| **Bronze** | - | 11 | 5,605,055 | 0 | 0 | 320 MB Parquet |
| **Silver** | `silver` | 10 | 5,535,614 | 38 | 0 | 280 MB Parquet + 615 MB PG |
| **Gold** | `analytics` | 5 | 402,992 | 15 | 5 regular + 3 MV | 180 MB Parquet + 320 MB PG |
| **Streaming** | `streaming` | 6 | 342 | 9 | 3 | 12 MB PG JSONB |
| **Total** | - | **32** | **11,544,003** | **62** | **11** | **1.7 GB** |

---

## Database Connection Information

```yaml
# PostgreSQL Configuration
Host: localhost
Port: 5432
Database: football_analytics
Schemas:
  - silver        # Cleaned data (10 tables, 5.5M records)
  - analytics     # Analytics (5 tables, 403K records, 8 views)
  - streaming     # Real-time (6 tables, 342 records)

# Parquet Data Lake
Location: artifacts/
Layers:
  - bronze/       # Raw data (11 files, 5.6M records)
  - silver/       # Cleaned (10 files, 5.5M records)
  - gold/         # Analytics (5 files, 403K records)
```

---

*Generated: November 30, 2025*  
*Project: Football Big Data Analytics Platform*  
*Repository: github.com/Flourish04/football_bigdata_analysis*
