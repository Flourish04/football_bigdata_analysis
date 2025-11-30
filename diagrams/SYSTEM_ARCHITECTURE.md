# 🏗️ System Architecture Diagrams

## Table of Contents
- [Lambda Architecture Overview](#lambda-architecture-overview)
- [Medallion Architecture Flow](#medallion-architecture-flow)
- [ETL Pipeline Flow](#etl-pipeline-flow)
- [Streaming Architecture](#streaming-architecture)
- [Component Integration](#component-integration)

---

## Lambda Architecture Overview

### High-Level System Architecture

```mermaid
graph TB
    subgraph "DATA SOURCES"
        A1[CSV Files<br/>11 files, 5.6M records]
        A2[Football-Data.org API<br/>Live Match Data]
    end

    subgraph "BATCH LAYER"
        B1[Bronze Layer<br/>Raw Ingestion]
        B2[Silver Layer<br/>Data Cleaning]
        B3[Gold Layer<br/>Analytics Aggregation]
    end

    subgraph "SPEED LAYER"
        C1[Apache NiFi<br/>Data Producer]
        C2[Confluent Kafka<br/>Message Queue]
        C3[Spark Streaming<br/>Consumer]
    end

    subgraph "SERVING LAYER"
        D1[PostgreSQL<br/>Data Warehouse]
        D2[Parquet<br/>Data Lake]
        D3[Views & MVs<br/>Query Layer]
    end

    subgraph "PRESENTATION LAYER"
        E1[Apache Superset<br/>Dashboards]
        E2[SQL Queries<br/>Ad-hoc Analysis]
    end

    A1 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> D1
    B1 --> D2
    B2 --> D2
    B3 --> D2

    A2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1

    D1 --> D3
    D2 --> D3
    D3 --> E1
    D3 --> E2

    style B1 fill:#cd7f32
    style B2 fill:#c0c0c0
    style B3 fill:#ffd700
    style C2 fill:#ff6b6b
    style D1 fill:#4ecdc4
    style E1 fill:#95e1d3
```

---

## Medallion Architecture Flow

### Bronze → Silver → Gold Layers

```mermaid
graph LR
    subgraph "BRONZE LAYER"
        A1[CSV Ingestion]
        A2[Schema Inference]
        A3[Add Metadata]
        A4[Parquet Write<br/>Snappy Compression]
    end

    subgraph "SILVER LAYER"
        B1[Read Bronze Parquet]
        B2[Data Type Conversion]
        B3[Null Handling]
        B4[Deduplication]
        B5[Standardization]
        B6[Validation]
        B7[Write Silver Parquet]
        B8[Load to PostgreSQL]
    end

    subgraph "GOLD LAYER"
        C1[Read Silver Data]
        C2[Player Analytics 360]
        C3[Form Metrics]
        C4[Market Trends]
        C5[Injury Risk Scores]
        C6[Transfer Intelligence]
        C7[Write Gold Parquet]
        C8[Load to PostgreSQL]
    end

    A1 --> A2 --> A3 --> A4
    A4 --> B1
    B1 --> B2 --> B3 --> B4 --> B5 --> B6
    B6 --> B7
    B6 --> B8
    B7 --> C1
    B8 --> C1
    C1 --> C2
    C1 --> C3
    C1 --> C4
    C1 --> C5
    C1 --> C6
    C2 --> C7
    C3 --> C7
    C4 --> C7
    C5 --> C7
    C6 --> C7
    C2 --> C8
    C3 --> C8
    C4 --> C8
    C5 --> C8
    C6 --> C8

    style A4 fill:#cd7f32
    style B7 fill:#c0c0c0
    style B8 fill:#c0c0c0
    style C7 fill:#ffd700
    style C8 fill:#ffd700
```

---

## ETL Pipeline Flow

### Step-by-Step Execution

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator as run_pipeline.py
    participant Bronze as bronze_layer.py
    participant Silver as silver_layer.py
    participant Gold as gold_layer.py
    participant Loader as PostgreSQL Loaders
    participant Views as View Creator
    participant Validator as Data Quality Check

    User->>Orchestrator: python run_pipeline.py
    
    Note over Orchestrator: Step 1/7: Bronze Layer
    Orchestrator->>Bronze: Execute Bronze Ingestion
    Bronze->>Bronze: Read 11 CSV files
    Bronze->>Bronze: Infer schemas
    Bronze->>Bronze: Add ingestion metadata
    Bronze->>Bronze: Write to Parquet (Snappy)
    Bronze-->>Orchestrator: ✅ 5,605,055 records (52s)

    Note over Orchestrator: Step 2/7: Silver Layer
    Orchestrator->>Silver: Execute Silver Cleaning
    Silver->>Silver: Read Bronze Parquet
    Silver->>Silver: Clean 10 tables
    Silver->>Silver: Standardize formats
    Silver->>Silver: Handle nulls & duplicates
    Silver->>Silver: Write to Parquet
    Silver-->>Orchestrator: ✅ 5,535,614 records (25s)

    Note over Orchestrator: Step 3/7: Gold Layer
    Orchestrator->>Gold: Execute Gold Aggregation
    Gold->>Gold: Read Silver data
    Gold->>Gold: Calculate 5 analytics tables
    Gold->>Gold: Player 360, Form, Market, Injury, Transfer
    Gold->>Gold: Write to Parquet
    Gold-->>Orchestrator: ✅ 402,992 records (11s)

    Note over Orchestrator: Step 4/7: Load Silver to PostgreSQL
    Orchestrator->>Loader: Load Silver Tables
    Loader->>Loader: Read Silver Parquet
    Loader->>Loader: Create tables with indexes
    Loader->>Loader: Bulk insert data
    Loader-->>Orchestrator: ✅ 5,535,614 records (13s)

    Note over Orchestrator: Step 5/7: Load Gold to PostgreSQL
    Orchestrator->>Loader: Load Gold Tables
    Loader->>Loader: Read Gold Parquet
    Loader->>Loader: Create analytics schema
    Loader->>Loader: Create tables & indexes
    Loader->>Loader: Bulk insert data
    Loader-->>Orchestrator: ✅ 402,992 records (33s)

    Note over Orchestrator: Step 6/7: Create Views
    Orchestrator->>Views: Create SQL Views
    Views->>Views: 5 Regular Views
    Views->>Views: 3 Materialized Views
    Views-->>Orchestrator: ✅ 8 views (0.2s)

    Note over Orchestrator: Step 7/7: Data Quality Validation
    Orchestrator->>Validator: Run Quality Checks
    Validator->>Validator: 8 validation rules
    Validator->>Validator: Check completeness
    Validator->>Validator: Check consistency
    Validator->>Validator: Check accuracy
    Validator-->>Orchestrator: ✅ All checks passed (10s)

    Orchestrator-->>User: ✅ Pipeline Complete (148.7s)
```

---

## Streaming Architecture

### Real-Time Data Pipeline

```mermaid
graph TB
    subgraph "DATA SOURCE"
        A[Football-Data.org API<br/>REST API with Auth Token]
    end

    subgraph "APACHE NIFI PRODUCERS"
        B1[InvokeHTTP<br/>Fetch Matches<br/>Every 10s]
        B2[InvokeHTTP<br/>Fetch Competitions<br/>Every 60s]
        B3[InvokeHTTP<br/>Fetch Leaderboards<br/>Every 60s]
        B4[RouteOnAttribute<br/>Filter by Status]
        B5[EvaluateJsonPath<br/>Extract Competition IDs]
    end

    subgraph "CONFLUENT KAFKA TOPICS"
        C1[live-match-events<br/>Partition: 3<br/>Retention: 7 days]
        C2[football-competitions<br/>Partition: 1<br/>Retention: 30 days]
        C3[football-leaderboards<br/>Partition: 1<br/>Retention: 30 days]
    end

    subgraph "SPARK STREAMING CONSUMERS"
        D1[Match Events Consumer<br/>Trigger: 15s<br/>Checkpoint: Global]
        D2[Competitions Consumer<br/>Trigger: 60s<br/>Checkpoint: Global]
    end

    subgraph "STAGING TABLES"
        E1[matches_staging<br/>Temporary Buffer]
        E2[competitions_staging<br/>Temporary Buffer]
        E3[leaderboards_staging<br/>Temporary Buffer]
    end

    subgraph "POSTGRESQL TABLES"
        F1[streaming.football_matches<br/>JSONB + Structured]
        F2[streaming.competitions<br/>JSONB Metadata]
        F3[streaming.leaderboards<br/>JSONB Standings]
    end

    subgraph "VIEWS"
        G1[vw_current_live_matches]
        G2[vw_match_score_progression]
        G3[vw_competition_live_standings]
    end

    A --> B1
    A --> B2
    A --> B3
    B1 --> B4
    B4 --> C1
    B2 --> B5
    B5 --> C2
    B3 --> C3

    C1 --> D1
    C2 --> D2
    C3 --> D2

    D1 --> E1
    D2 --> E2
    D2 --> E3

    E1 --> F1
    E2 --> F2
    E3 --> F3

    F1 --> G1
    F1 --> G2
    F2 --> G3
    F3 --> G3

    style C1 fill:#ff6b6b
    style C2 fill:#ff6b6b
    style C3 fill:#ff6b6b
    style F1 fill:#4ecdc4
    style G1 fill:#95e1d3
```

### Streaming Data Flow Detail

```mermaid
sequenceDiagram
    participant API as Football-Data.org API
    participant NiFi as Apache NiFi
    participant Kafka as Confluent Kafka
    participant Spark as Spark Streaming
    participant Staging as Staging Tables
    participant DB as PostgreSQL
    participant View as SQL Views

    Note over API,NiFi: Every 10 seconds (Matches)
    API->>NiFi: HTTP GET /matches
    NiFi->>NiFi: Parse JSON response
    NiFi->>NiFi: Filter IN_PLAY status
    NiFi->>Kafka: Publish to live-match-events

    Note over Kafka,Spark: Every 15 seconds (Trigger)
    Kafka->>Spark: Consume batch
    Spark->>Spark: Parse JSON schema
    Spark->>Spark: Extract structured fields
    Spark->>Spark: Keep full JSON in match_data
    Spark->>Staging: Write to matches_staging

    Note over Staging,DB: Transactional UPSERT
    Staging->>DB: MERGE INTO football_matches
    DB->>DB: ON CONFLICT (match_id) DO UPDATE
    DB->>DB: Update changed fields only
    DB->>DB: Commit transaction
    
    Note over DB,View: Real-time Query
    DB->>View: Refresh vw_current_live_matches
    View-->>View: SELECT * WHERE status='IN_PLAY'

    Note over API,NiFi: Every 60 seconds (Competitions)
    API->>NiFi: HTTP GET /competitions
    NiFi->>NiFi: Parse competitions JSON
    NiFi->>NiFi: Extract competition IDs
    NiFi->>Kafka: Publish to football-competitions
    
    loop For each competition
        NiFi->>API: HTTP GET /competition/{id}/standings
        API->>NiFi: Return leaderboard JSON
        NiFi->>Kafka: Publish to football-leaderboards
    end

    Note over Kafka,Spark: Every 60 seconds (Trigger)
    Kafka->>Spark: Consume competitions batch
    Spark->>Staging: Write to competitions_staging
    Staging->>DB: UPSERT to streaming.competitions
    
    Kafka->>Spark: Consume leaderboards batch
    Spark->>Staging: Write to leaderboards_staging
    Staging->>DB: UPSERT to streaming.leaderboards
    
    DB->>View: Join competitions + leaderboards
    View-->>View: vw_competition_live_standings
```

---

## Component Integration

### Technology Stack Integration

```mermaid
graph TB
    subgraph "PROCESSING LAYER"
        A1[Apache Spark 4.0<br/>Distributed Processing]
        A2[PySpark<br/>Python API]
    end

    subgraph "STORAGE LAYER"
        B1[PostgreSQL 14+<br/>Relational Database<br/>935 MB]
        B2[Parquet Files<br/>Columnar Storage<br/>800 MB]
    end

    subgraph "STREAMING LAYER"
        C1[Apache NiFi 1.25<br/>Visual ETL]
        C2[Confluent Kafka<br/>Message Broker<br/>SASL/SSL Auth]
        C3[Spark Structured Streaming<br/>Micro-batch Processing]
    end

    subgraph "VISUALIZATION LAYER"
        D1[Apache Superset 3.0<br/>BI Dashboards]
        D2[SQL Client<br/>pgAdmin/DBeaver]
    end

    subgraph "ORCHESTRATION"
        E1[run_pipeline.py<br/>Python Script]
        E2[.env Configuration<br/>Environment Variables]
    end

    subgraph "DATA QUALITY"
        F1[validate_data.py<br/>8 Quality Checks]
        F2[Logging System<br/>Comprehensive Logs]
    end

    A1 --> A2
    A2 --> B1
    A2 --> B2

    C1 --> C2
    C2 --> C3
    C3 --> B1

    B1 --> D1
    B1 --> D2
    B2 --> A2

    E1 --> A2
    E1 --> C3
    E2 --> E1

    F1 --> B1
    F1 --> B2
    F2 --> E1

    style A1 fill:#e8833a
    style B1 fill:#336791
    style C2 fill:#231f20
    style D1 fill:#20a7c9
```

### Data Flow Volume Metrics

```mermaid
graph LR
    A[CSV Files<br/>5,605,066 records<br/>850 MB]
    B[Bronze Parquet<br/>5,605,055 records<br/>320 MB<br/>-0.002% loss]
    C[Silver Parquet<br/>5,535,614 records<br/>280 MB<br/>-1.2% loss]
    D[Gold Parquet<br/>402,992 records<br/>180 MB<br/>Analytics]
    E[PostgreSQL<br/>5,938,606 records<br/>935 MB<br/>Silver + Gold]
    F[Streaming<br/>342 records<br/>12 MB<br/>Real-time]

    A -->|52s| B
    B -->|25s| C
    C -->|11s| D
    C -->|13s| E
    D -->|33s| E
    F -->|15-60s| E

    style B fill:#cd7f32
    style C fill:#c0c0c0
    style D fill:#ffd700
    style E fill:#4ecdc4
    style F fill:#ff6b6b
```

---

## Performance Metrics Dashboard

### Pipeline Execution Metrics

```mermaid
gantt
    title ETL Pipeline Execution Timeline (148.7s Total)
    dateFormat ss
    axisFormat %S

    section Bronze Layer
    CSV Ingestion (52s)           :active, bronze, 00, 52s

    section Silver Layer
    Data Cleaning (25s)           :active, silver, 52, 25s

    section Gold Layer
    Analytics Aggregation (11s)   :active, gold, 77, 11s

    section PostgreSQL Load
    Load Silver Tables (13s)      :active, load1, 88, 13s
    Load Gold Tables (33s)        :active, load2, 101, 33s

    section Finalization
    Create Views (0.2s)           :active, views, 134, 1s
    Data Quality Check (10s)      :active, validate, 135, 10s
```

### Storage Distribution

```mermaid
pie title Storage Distribution (1.7 GB Total)
    "Bronze Parquet" : 320
    "Silver Parquet" : 280
    "Gold Parquet" : 180
    "PostgreSQL Silver" : 615
    "PostgreSQL Gold" : 320
    "PostgreSQL Streaming" : 12
```

### Record Distribution by Layer

```mermaid
pie title Record Distribution (11.5M Total)
    "Silver Layer" : 5535614
    "Bronze Layer" : 5605055
    "Gold Analytics" : 402992
    "Streaming" : 342
```

---

## Deployment Architecture

### Local Development Setup

```mermaid
graph TB
    subgraph "LOCALHOST MACHINE"
        subgraph "PYTHON ENVIRONMENT"
            A1[Python 3.11+<br/>Virtual Environment]
            A2[Dependencies<br/>requirements.txt]
        end

        subgraph "DATABASES"
            B1[PostgreSQL 14+<br/>Port: 5432<br/>DB: football_analytics]
        end

        subgraph "DATA STORAGE"
            C1[Project Directory<br/>football_project/]
            C2[Parquet Files<br/>artifacts/bronze/silver/gold/]
            C3[CSV Source Data<br/>football-datasets/datalake/]
        end

        subgraph "SPARK RUNTIME"
            D1[Spark Driver<br/>Local Mode]
            D2[Spark Executors<br/>Local Threads]
        end

        subgraph "EXTERNAL SERVICES"
            E1[Confluent Cloud<br/>Kafka Cluster<br/>pkc-xxx.aws]
            E2[Football-Data.org<br/>REST API]
        end

        subgraph "VISUALIZATION"
            F1[Apache Superset<br/>Port: 8088<br/>localhost]
        end
    end

    A1 --> A2
    A2 --> D1
    D1 --> D2
    D2 --> C2
    D2 --> B1
    C3 --> D1
    E1 --> D1
    E2 --> E1
    B1 --> F1

    style E1 fill:#ff6b6b
    style E2 fill:#4ecdc4
    style B1 fill:#336791
    style F1 fill:#20a7c9
```

---

## Summary Statistics

### System Metrics Overview

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Records Processed** | 11,544,003 | Across all layers |
| **Pipeline Runtime** | 148.7 seconds | Full ETL execution |
| **Storage Footprint** | 1.7 GB | Parquet + PostgreSQL |
| **Data Quality Score** | 98.8% | After cleaning |
| **Throughput** | 39,333 rec/s | Average processing rate |
| **Streaming Latency** | 15-60 seconds | Microbatch interval |
| **Tables Created** | 32 | Across 3 schemas |
| **Indexes Created** | 62 | Performance optimization |
| **Views Created** | 11 | 8 regular + 3 materialized |

### Layer-by-Layer Breakdown

| Layer | Duration | Records | Throughput | Storage | Data Loss |
|-------|----------|---------|------------|---------|-----------|
| Bronze | 52s | 5,605,055 | 107,789/s | 320 MB | 0.002% |
| Silver | 25s | 5,535,614 | 221,424/s | 280 MB | 1.2% |
| Gold | 11s | 402,992 | 36,635/s | 180 MB | N/A |
| Load Silver | 13s | 5,535,614 | 425,816/s | 615 MB | 0% |
| Load Gold | 33s | 402,992 | 12,212/s | 320 MB | 0% |
| Streaming | Real-time | 342 | N/A | 12 MB | 0% |

---

*Generated: November 30, 2025*  
*Project: Football Big Data Analytics Platform*  
*Repository: github.com/Flourish04/football_bigdata_analysis*
