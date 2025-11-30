# 📊 Diagrams & Visualizations

This directory contains comprehensive database schema diagrams and system architecture visualizations for the Football Big Data Analytics Platform.

---

## 📑 Available Diagrams

### 1. [Database Schema Diagrams](DATABASE_SCHEMA.md)

Complete Entity-Relationship Diagrams (ERD) using Mermaid syntax covering all database schemas:

**Contents:**
- ✅ **Silver Layer Schema** - Player profiles, performances, transfers, injuries, market values
- ✅ **Gold Layer Analytics Schema** - Player 360°, form metrics, market trends, injury risk, transfer intelligence
- ✅ **Streaming Schema** - Real-time match events, competitions, leaderboards
- ✅ **Complete System Overview** - Data flow architecture, schema organization
- ✅ **Index & Constraint Overview** - Performance optimization details

**Diagrams Include:**
- 🔷 Player-Related Tables (7 tables with relationships)
- 🔷 Team and Competition Tables (4 tables with relationships)
- 🔷 Integrated Silver Layer Schema (cross-entity relationships)
- 🔷 Analytics 360° Tables (5 gold tables)
- 🔷 Analytics Views (3 regular + 3 materialized views)
- 🔷 Real-Time Streaming Tables (6 tables)
- 🔷 Streaming Views (3 views)
- 🔷 Data Flow Architecture (Bronze → Silver → Gold)
- 🔷 Schema Organization (3 schemas overview)

**Summary Statistics:**
```
├── 32 Tables Total
├── 11,544,003 Records Total
├── 62 Indexes
├── 11 Views (8 regular + 3 materialized)
└── 1.7 GB Total Storage
```

---

### 2. [System Architecture Diagrams](SYSTEM_ARCHITECTURE.md)

Complete system architecture visualizations showing data flow, components, and integration:

**Contents:**
- ✅ **Lambda Architecture Overview** - Batch + Speed + Serving layers
- ✅ **Medallion Architecture Flow** - Bronze → Silver → Gold transformations
- ✅ **ETL Pipeline Flow** - Step-by-step execution sequence
- ✅ **Streaming Architecture** - Real-time data pipeline
- ✅ **Component Integration** - Technology stack integration

**Diagrams Include:**
- 🔶 High-Level System Architecture (5 layers)
- 🔶 Bronze → Silver → Gold Layers (detailed flow)
- 🔶 ETL Pipeline Sequence Diagram (7 steps with timing)
- 🔶 Real-Time Data Pipeline (NiFi → Kafka → Spark → PostgreSQL)
- 🔶 Streaming Data Flow Detail (sequence diagram)
- 🔶 Technology Stack Integration (all components)
- 🔶 Data Flow Volume Metrics (with data loss percentages)
- 🔶 Pipeline Execution Timeline (Gantt chart)
- 🔶 Storage Distribution (pie chart)
- 🔶 Record Distribution (pie chart)
- 🔶 Deployment Architecture (local development setup)

**Performance Metrics:**
```
├── Pipeline Runtime: 148.7 seconds
├── Throughput: 39,333 records/second
├── Data Quality: 98.8%
├── Streaming Latency: 15-60 seconds
└── Storage: 1.7 GB (Parquet + PostgreSQL)
```

---

## 🎨 Diagram Types

### Mermaid Diagrams

All diagrams are created using **Mermaid.js** syntax, which renders beautifully on GitHub and can be embedded in Markdown files.

**Supported Diagram Types:**
- **Entity-Relationship Diagrams (ERD)** - Database schemas with relationships
- **Flow Charts** - Data flow and process flows
- **Sequence Diagrams** - Interaction between components
- **Gantt Charts** - Timeline visualization
- **Pie Charts** - Distribution visualization
- **Graph Diagrams** - System architecture

### How to View

1. **On GitHub**: Open the `.md` files directly on GitHub - Mermaid renders automatically
2. **In VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **Export to Image**: Use Mermaid Live Editor (https://mermaid.live/) to export to PNG/SVG

---

## 📂 Diagram Organization

```
diagrams/
├── README.md                    # This file - Diagram index
├── DATABASE_SCHEMA.md           # Complete database ERD diagrams
└── SYSTEM_ARCHITECTURE.md       # System architecture diagrams
```

---

## 🔍 Quick Reference

### Database Schemas

| Schema | Tables | Records | Purpose |
|--------|--------|---------|---------|
| **silver** | 10 | 5,535,614 | Cleaned data layer |
| **analytics** | 5 + 8 views | 402,992 | Gold analytics layer |
| **streaming** | 6 | 342 | Real-time data |

### Key Relationships

```
PLAYER_PROFILES (92,671)
├── has historical values → PLAYER_MARKET_VALUES (248,175)
├── has current value → PLAYER_LATEST_MARKET_VALUES (92,671)
├── has transfers → PLAYER_TRANSFER_HISTORIES (117,944)
├── has performances → PLAYER_PERFORMANCES (4,965,850)
├── played with teammates → PLAYER_TEAMMATES_PLAYED_WITH (227,050)
├── has injuries → PLAYER_INJURY_HISTORIES (34,561)
└── national team caps → PLAYER_NATIONAL_TEAM_PERFORMANCES (1,347)

TEAMS_DETAILS (862)
├── has youth teams → TEAMS_CHILDREN (11)
├── participates in seasons → TEAMS_COMPETITIONS_SEASONS (11,542)
└── competes in → COMPETITIONS (59)
```

### Data Flow Summary

```
CSV Files (5.6M records)
    ↓ (52s)
Bronze Parquet (5.6M records) -0.002% loss
    ↓ (25s)
Silver Parquet (5.5M records) -1.2% loss
    ↓ (11s)
Gold Parquet (403K records) Analytics
    ↓ (46s)
PostgreSQL (5.9M records) Silver + Gold
    ↓ (Real-time)
Streaming (342 records) Live data
```

---

## 📊 Dashboard Visualizations

The project also includes **5 Apache Superset dashboards** with visual analytics:

1. **Player Scouting** - Top performers by position and metrics
2. **Performance Analytics** - Form metrics and statistical trends
3. **Transfer Market Intelligence** - Market value trends and opportunities
4. **Injury Risk Management** - Health scores and injury analysis
5. **Football Leaderboards** - Competition standings and rankings

Screenshots available in `/dashboards/` directory.

---

## 🔗 Related Documentation

- [Main README](../README.md) - Project overview and quick start
- [PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) - Complete system documentation
- [STREAMING_ARCHITECTURE.md](../STREAMING_ARCHITECTURE.md) - Streaming pipeline details
- [BAO_CAO_TONG_QUAN.md](../BAO_CAO_TONG_QUAN.md) - Vietnamese project report

---

## 🛠️ Tools Used

- **Mermaid.js** - Diagram as code (https://mermaid.js.org/)
- **GitHub Markdown** - Native rendering support
- **VS Code** - Markdown preview with Mermaid extension

---

## 📝 Notes

- All diagrams are automatically rendered on GitHub
- Diagrams are version-controlled and can be updated easily
- No external image files needed - all diagrams are code-based
- Easy to maintain and update as the system evolves

---

*Last Updated: November 30, 2025*  
*Project: Football Big Data Analytics Platform*  
*Repository: github.com/Flourish04/football_bigdata_analysis*
