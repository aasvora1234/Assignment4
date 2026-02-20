# Smart Logistics Data Lakehouse Platform
## Assignment 4 - AI Native Data Engineering

---

## Overview

A production-ready **Data Lakehouse** for a logistics company that:
- Ingests transactional data (PostgreSQL) and IoT sensor data (JSON)
- Applies data quality scoring and SCD Type 2 historical tracking
- Generates business analytics (shipment summaries, violation alerts)
- Orchestrates the full pipeline via Apache Airflow

**Architecture**: Medallion Pattern → Bronze (Raw) → Silver (Cleaned) → Gold (Analytics)

---

## Prerequisites

- Docker Desktop (with WSL2 on Windows)
- Docker Compose v2
- At least 8GB RAM available for Docker
- Git

---

## Quick Start

### Step 1: Clone the Repository
```bash
git clone https://github.com/aasvora1234/Assignment4.git
cd Assignment4
```

### Step 2: Configure Environment
```bash
# Copy the env template (already included)
# Edit .env if you want custom credentials
```

### Step 3: Start All Services
```bash
docker-compose up -d
```

Wait ~60 seconds for all services to initialize.

### Step 4: Verify Services are Running
```bash
docker ps
```

Expected containers:
- `assignment4-postgres-1` (healthy)
- `assignment4-airflow-webserver-1` (up)
- `assignment4-airflow-scheduler-1` (up)
- `assignment4-spark-master-1` (up)
- `assignment4-spark-worker-1` (up)

### Step 5: Fix Permissions (first run only)
```bash
docker exec -u root assignment4-airflow-scheduler-1 chmod -R 777 /opt/data/delta-lake
```

### Step 6: Trigger the Pipeline

**Option A: Airflow UI**
1. Open http://localhost:8090
2. Login: `admin` / `admin`
3. Find `medallion_airflow_pipeline` DAG
4. Click the **Play ▶️** button → Trigger DAG

**Option B: PowerShell Script**
```powershell
.\run-pipeline.ps1
```

**Option C: Command Line**
```bash
docker exec assignment4-airflow-scheduler-1 airflow dags trigger medallion_airflow_pipeline
```

### Step 7: Monitor Execution
- **Airflow UI**: http://localhost:8090 — Watch tasks turn green
- **Spark UI**: http://localhost:8080 — Monitor Spark jobs

### Step 8: View Results

**Gold Layer Analytics:**
```bash
docker exec assignment4-airflow-scheduler-1 python3 -c "
import pandas as pd
from pathlib import Path
files = list(Path('/opt/data/delta-lake/gold/shipment_summary').glob('*.csv'))
df = pd.read_csv(max(files, key=lambda x: x.stat().st_mtime))
print(df.to_string(index=False))
"
```

**PostgreSQL Database:**
```bash
docker exec -it assignment4-postgres-1 psql -U admin -d postgres
# Then: SELECT status, COUNT(*) FROM logistics.shipments GROUP BY status;
```

---

## Project Structure

```
Assignment 4/
├── deliverables/               ← Submission files
│   ├── PRD.md                  ← Product Requirements Document
│   ├── Design.md               ← Architecture + Mermaid diagrams
│   ├── TechDetails.md          ← SCD Type 2 & Spark optimization details
│   ├── TasksList.md            ← Step-by-step build checklist (24 tasks)
│   ├── CHAT_HISTORY.md         ← AI assistant conversation history
│   ├── README.md               ← This file
│   ├── docker-compose.yml      ← Docker services configuration
│   └── code/
│       ├── spark/
│       │   ├── bronze_ingestion.py    ← Raw data ingestion
│       │   ├── silver_processing.py   ← Cleaning, SCD2, outliers
│       │   └── gold_aggregations.py   ← Business analytics
│       └── airflow_dag.py             ← Airflow orchestration DAG
├── airflow/
│   ├── dags/                   ← Airflow DAG files
│   └── Dockerfile              ← Custom Airflow image
├── spark/scripts/              ← All Spark/Python scripts
├── scripts/init_postgres.sql   ← Database schema
├── data/iot_raw/               ← IoT sensor JSON files
└── docker-compose.yml          ← Root Docker configuration
```

---

## Architecture

```
PostgreSQL DB     IoT JSON Files
     │                  │
     └──────┬───────────┘
            ▼
      Bronze Layer (Raw CSV)
            │
            ▼
      Silver Layer (Cleaned)
      • SCD Type 2 (Shipments)
      • Outlier Detection (IoT)
      • Quality Scoring
            │
            ▼
      Gold Layer (Analytics)
      • Shipment Summary
      • Status Breakdown
            │
            ▼
      Business Insights
```

All orchestrated by **Apache Airflow** DAG:
`start → bronze_layer → silver_layer → gold_layer → complete`

---

## Key Design Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Processing | Pandas (not PySpark) | Simpler for MVP; easily migrated |
| Storage | CSV | Easy inspection; sufficient for scale |
| DAG Code | Inline Python | Self-contained, no path dependencies |
| Outlier Detection | 3-method approach | More robust than single method |
| History Tracking | SCD Type 2 | Full audit trail for compliance |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | Apache Airflow 2.8.0 |
| Processing | Python 3.8, Pandas, NumPy |
| Database | PostgreSQL 15 |
| Compute | Apache Spark 3.5.0 |
| Containerization | Docker Compose |
| Language | Python |

---

## Stopping the Services

```bash
docker-compose down
```

To also remove data volumes:
```bash
docker-compose down -v
```

---

## Author

**GitHub**: https://github.com/aasvora1234/Assignment4
