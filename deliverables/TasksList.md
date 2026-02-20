# Tasks List
## Step-by-Step Build Checklist: Smart Logistics Data Lakehouse

---

## Phase 1: Project Setup & Infrastructure

- [x] **Task 001**: Define project requirements and architecture
  - Read assignment brief
  - Decide on Medallion Architecture (Bronze → Silver → Gold)
  - Choose technology stack: Python, Pandas, Airflow, Spark, Docker, PostgreSQL

- [x] **Task 002**: Set up Docker environment
  - Create `docker-compose.yml` with services: PostgreSQL, Spark Master, Spark Worker, Airflow Webserver, Airflow Scheduler, Airflow Init
  - Configure shared Docker volumes for data and scripts
  - Configure Docker networking so containers can communicate

- [x] **Task 003**: Configure environment variables
  - Create `.env` file with DB credentials, Airflow settings
  - Add `.env` to `.gitignore` to avoid leaking secrets
  - Set `AIRFLOW_UID` for file ownership on mounted volumes

---

## Phase 2: Database Setup

- [x] **Task 004**: Design PostgreSQL schema
  - Create `logistics` schema with 8 tables:
    - `customers`, `orders`, `shipments`
    - `drivers`, `vehicles`, `warehouses`
    - `shipment_types`, `truck_assignments`
  - Define foreign key relationships and indexes
  - Write `scripts/init_postgres.sql`

- [x] **Task 005**: Generate realistic sample data
  - Write `generate_sample_data.py` using Faker library
  - Generate: 50 customers, 150 orders, 100 shipments (6 status types)
  - Generate 7,000+ IoT sensor readings with intentional anomalies for testing
  - Seed IoT JSON files to `data/iot_raw/`
  - Load data into PostgreSQL via psycopg2

---

## Phase 3: Bronze Layer

- [x] **Task 006**: Build Bronze ingestion script
  - Write `bronze_simple.py`:
    - Connect to PostgreSQL via psycopg2
    - Read all 8 transactional tables with `pd.read_sql()`
    - Add metadata columns: `ingestion_timestamp`, `source_system`, `source_table`
    - Save each table as timestamped CSV to `/opt/data/delta-lake/bronze/{table}/`
  - Write separate IoT ingestion logic:
    - Read JSON files from `data/iot_raw/`
    - Flatten nested JSON structure
    - Save to `/opt/data/delta-lake/bronze/iot_sensor_readings/`
  - Verify: 8+ CSV files created in bronze layer

---

## Phase 4: Silver Layer

- [x] **Task 007**: Build SCD Type 2 for shipments
  - Read latest Bronze shipments CSV
  - Add 4 tracking columns: `surrogate_key`, `valid_from`, `valid_to`, `is_current`, `version`
  - Assign version numbers per `shipment_id` group
  - Mark only latest record as `is_current = True`
  - Save to `/opt/data/delta-lake/silver/shipments_scd2/`

- [x] **Task 008**: Build IoT outlier detection
  - Implement 3-method outlier detection:
    1. Range validation: temperature -30°C to +50°C
    2. Statistical: Z-score > 3.0 per truck
    3. Rapid change: temperature delta > 10°C
  - Add GPS coordinate validation
  - Compute `quality_score` (100=clean, 50=flagged) and `data_quality_flag`
  - Save clean + flagged data to `/opt/data/delta-lake/silver/iot_sensor_readings_clean/`

- [x] **Task 009**: Build Silver processing for reference tables
  - Deduplicate customers, orders, warehouses, drivers, vehicles
  - Add `silver_processed_at` timestamp
  - Save all to `/opt/data/delta-lake/silver/`
  - Verify: 16+ CSV files in silver layer

---

## Phase 5: Gold Layer

- [x] **Task 010**: Build Gold aggregations
  - Read latest Silver shipments SCD2 data
  - Group by `status`, count each category
  - Add `created_at` execution timestamp
  - Save to `/opt/data/delta-lake/gold/shipment_summary/`
  - Verify: summary shows 6 status groups (Delivered, In Transit, etc.)

---

## Phase 6: Airflow Orchestration

- [x] **Task 011**: Design Airflow DAG
  - Create `airflow/dags/medallion_airflow_pipeline.py`
  - Define 5-task DAG: `start → bronze_layer → silver_layer → gold_layer → complete`
  - Use `PythonOperator` for Bronze, Silver, Gold tasks
  - Use `EmptyOperator` for start/complete markers
  - Set: retries=1, retry_delay=2min, catchup=False

- [x] **Task 012**: Build custom Airflow image
  - Create `airflow/Dockerfile` extending `apache/airflow:2.8.0`
  - Install: `pandas`, `psycopg2-binary`, `numpy`, `faker`
  - Create `airflow/requirements.txt`
  - Update `docker-compose.yml` to build from custom image

- [x] **Task 013**: Test and debug Airflow pipeline
  - Fix: `ModuleNotFoundError: pandas` → added to custom Dockerfile
  - Fix: Typo `sh ipments_file` → corrected variable name
  - Fix: SyntaxError in f-string with backslash → refactored string
  - Fix: `PermissionError` on gold directory → `chmod 777 /opt/data/delta-lake/gold`
  - Verify: All 5 tasks show green (SUCCESS) in Airflow UI

---

## Phase 7: Testing & Validation

- [x] **Task 014**: Manual pipeline test
  - Run `run-pipeline.ps1` to execute all 3 layers manually
  - Verify Bronze: 18+ files created
  - Verify Silver: 16+ files created
  - Verify Gold: 2+ summary files created
  - Verify Gold output: 6 status groups, 100 total shipments

- [x] **Task 015**: Airflow DAG end-to-end test
  - Trigger DAG via Airflow UI (http://localhost:8090)
  - Confirm all tasks: `start`, `bronze_layer`, `silver_layer`, `gold_layer`, `complete` = SUCCESS
  - Check Gold output matches manually-run results

- [x] **Task 016**: Database validation
  - Connect to PostgreSQL: `docker exec -it ... psql -U admin`
  - Verify all 8 tables populated
  - Run status breakdown query: confirm 52 Delivered, 19 In Transit, etc.

---

## Phase 8: Documentation

- [x] **Task 017**: Write PRD.md
  - Business problem statement
  - Solution overview with capabilities
  - Functional and non-functional requirements
  - Success metrics and future roadmap

- [x] **Task 018**: Write Design.md
  - System architecture overview
  - Mermaid.js data flow diagram (Source → Bronze → Silver → Gold)
  - Docker container architecture diagram
  - Airflow DAG structure diagram
  - ER diagram for database schema

- [x] **Task 019**: Write TechDetails.md
  - SCD Type 2 full implementation with code examples
  - IoT outlier detection (all 3 methods with code)
  - Spark/Pandas optimization strategies
  - Production PySpark roadmap

- [x] **Task 020**: Write README.md
  - Prerequisites and setup instructions
  - How to start the pipeline
  - How to access Airflow UI
  - How to view results

- [x] **Task 021**: Organize deliverables
  - Create `deliverables/` folder
  - Copy all required submission files with correct names
  - Verify folder structure matches assignment requirements

---

## Phase 9: Submission

- [x] **Task 022**: Initialize Git repository
  - `git init` in project folder
  - Create `.gitignore` (exclude `.env`, `data/`, `__pycache__`)
  - `git add .` → `git commit -m "Initial commit"`

- [x] **Task 023**: Push to GitHub
  - `git remote add origin https://github.com/aasvora1234/Assignment4.git`
  - `git branch -M main`
  - `git push -u origin main`
  - Verify files visible on GitHub

- [x] **Task 024**: Share repository
  - Add collaborator: `dmistryTal` via GitHub Settings → Collaborators
  - Send invitation

---

## Summary Statistics

| Phase | Tasks | Status |
|-------|-------|--------|
| Setup & Infrastructure | 3 tasks | ✅ Complete |
| Database Setup | 2 tasks | ✅ Complete |
| Bronze Layer | 1 task | ✅ Complete |
| Silver Layer | 3 tasks | ✅ Complete |
| Gold Layer | 1 task | ✅ Complete |
| Airflow Orchestration | 3 tasks | ✅ Complete |
| Testing & Validation | 3 tasks | ✅ Complete |
| Documentation | 5 tasks | ✅ Complete |
| Submission | 3 tasks | ✅ Complete |
| **TOTAL** | **24 tasks** | **✅ All Done** |

---

## Key Decisions Made During Build

| Decision | Choice | Reason |
|----------|--------|--------|
| Processing Engine | Pandas (not PySpark) | Simpler, faster to debug for MVP scale |
| Storage Format | CSV (not Delta Lake) | Easier inspection, sufficient for assignment |
| DAG Code Style | Inline Python in DAG | Self-contained, no external script dependencies |
| Outlier Detection | 3-method combined | More robust than any single method alone |
| SCD Type 2 Scope | Shipments only | Most critical business entity for history |
| Docker Volumes | Bind mounts | DAG hot-reload without container rebuild |

---

**Document Version**: 1.0
**Last Updated**: February 20, 2026
