# Technical Product Requirements Document (PRD)
## Smart Logistics Tracking - Lakehouse Architecture

**Project Name:** Smart Logistics Tracking Lakehouse  
**Version:** 1.0  
**Date:** 2026-02-06  
**Owner:** Data Architecture Team  
**Environment:** Local-First (Laptop Development)

---

## Executive Summary

This Technical PRD defines the complete architectural, design, and implementation specifications for the Smart Logistics Tracking Lakehouse. All decisions are optimized for **local laptop deployment** with realistic data patterns, production-ready SCD Type 2 implementation, robust error handling, and efficient resource utilization.

---

## Technical Requirements

| Requirement ID | Description | Technical Specification | Implementation Details |
|----------------|-------------|------------------------|------------------------|
| **TR-001** | Delta Lake Partitioning - Bronze Layer (Transactional) | Partition by `ingestion_date` (daily partitions) | Directory structure: `/bronze/transactional/table_name/ingestion_date=2026-02-06/`. Enables efficient time-based queries and data retention policies. New data lands in today's partition. |
| **TR-002** | Delta Lake Partitioning - Bronze Layer (IoT) | Partition by `reading_date` (extracted from timestamp, daily) | Directory structure: `/bronze/iot_telemetry/reading_date=2026-02-06/`. High-volume sensor data benefits from date-based partitioning for pruning. |
| **TR-003** | Delta Lake Partitioning - Silver Layer (Transactional) | Partition by `created_date` (shipment creation date, daily) | Directory structure: `/silver/shipments/created_date=2026-02-06/`. Business queries typically filter by creation date. Co-locate related shipments for better scan performance. |
| **TR-004** | Delta Lake Partitioning - Silver Layer (IoT) | Partition by `reading_date` (daily partitions) | Directory structure: `/silver/iot_telemetry/reading_date=2026-02-06/`. Maintains same partition strategy as Bronze for efficient incremental processing. |
| **TR-005** | Delta Lake Partitioning - Gold Layer | Partition by `shipment_date` (monthly partitions) | Directory structure: `/gold/shipment_analytics/year=2026/month=02/`. Aggregated data has lower volume, monthly partitions reduce metadata overhead while enabling efficient time-range queries. |
| **TR-006** | Z-ORDER Clustering - Silver Layer | Apply Z-ORDER on frequently queried columns | `OPTIMIZE shipments_silver ZORDER BY (shipment_id, truck_id, status);` Run weekly via maintenance job. Improves query performance by co-locating related data. |
| **TR-007** | Z-ORDER Clustering - Gold Layer | Apply Z-ORDER on join keys | `OPTIMIZE gold_shipment_analytics ZORDER BY (shipment_id, truck_id);` Optimizes analytical queries joining shipments with trucks. |
| **TR-008** | Delta Lake VACUUM Configuration | Retain 7 days of history for time travel | `VACUUM table_name RETAIN 168 HOURS;` Weekly cleanup job. Balances storage costs with ability to query historical versions and rollback if needed. |
| **TR-009** | Delta Lake Auto-Optimize | Enable auto-optimize on write | `spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")` Automatically compacts small files during write, maintaining optimal file sizes (~128MB target for laptop). |
| **TR-010** | SCD Type 2 - Primary Key Strategy | Use surrogate key for performance | `shipment_sk BIGINT PRIMARY KEY` (auto-incrementing). Natural key is `shipment_id VARCHAR(50)`. Surrogate keys enable faster joins and clearer version tracking. |
| **TR-011** | SCD Type 2 - Versioning Logic | Implement explicit version numbering | Add `version INT` column alongside effective dates. First record = version 1, increments with each change. Simplifies debugging and queries like "get version 3 of shipment X". |
| **TR-012** | SCD Type 2 - Temporal Columns | Use timestamp precision with microseconds | `effective_start_timestamp TIMESTAMP(6)`, `effective_end_timestamp TIMESTAMP(6)`. Handles same-day (even same-second) status changes. NULL for current records (SQL standard). |
| **TR-013** | SCD Type 2 - Current Record Flag | Use boolean flag for active records | `is_current BOOLEAN DEFAULT TRUE`. Single source of truth: only current records have `is_current = TRUE AND effective_end_timestamp IS NULL`. Enables fast queries: `WHERE is_current = TRUE`. |
| **TR-014** | SCD Type 2 - Change Detection Logic | Track changes only on status column | Monitor `status` column for changes. If status changes, close current record (set `is_current = FALSE`, `effective_end_timestamp = NOW()`), insert new record. Other column changes (e.g., address) do UPDATE in-place. |
| **TR-015** | SCD Type 2 - Merge Operation | Implement MERGE pattern for upserts | Use Delta Lake MERGE for atomic updates. Match on `shipment_id` WHERE `is_current = TRUE`. On status change: UPDATE old + INSERT new. On same status: UPDATE in-place. |
| **TR-016** | SCD Type 2 - Late Arriving Data | Reject out-of-order updates | If incoming timestamp < current `effective_start_timestamp`, log to rejected_records with reason="LATE_ARRIVAL". Manual review required. Prevents history corruption. |
| **TR-017** | SCD Type 2 - Simultaneous Changes | Use microsecond precision + sequence | If multiple changes occur in same second, use microsecond timestamp. If still collision, add `change_sequence INT` to order within same microsecond. Rare edge case handling. |
| **TR-018** | IoT File Processing - Deletion Strategy | Delete files after successful Bronze ingestion | After files loaded to Bronze and validation passed, delete from `/data/iot_raw/`. Reduce storage, prevent reprocessing. |
| **TR-019** | IoT File Historical Tracking | Create metadata table for processed files | Table: `processed_files_log(file_name, file_path, file_size_bytes, record_count, processing_timestamp, checksum_md5, status)`. Audit trail of all ingested files. |
| **TR-020** | IoT File Naming Convention | Standardized naming for easy parsing | Format: `iot_telemetry_YYYYMMDD_HHMMSS_<batch_id>.json`. Example: `iot_telemetry_20260206_143000_batch001.json`. Enables chronological processing and idempotency. |
| **TR-021** | IoT File Processing Order | Process files chronologically | Sort by filename (timestamp embedded), process oldest first. Ensures temporal consistency of data in lakehouse. |
| **TR-022** | Temperature Analytics - Metrics Calculation | Calculate ONLY average temperature | Gold layer: `avg_temperature = AVG(temperature)`. Keep it simple per requirement. Future enhancement: MIN/MAX/STDDEV can be added later. |
| **TR-023** | Temperature Analytics - Aggregation Window | Match sensor readings to shipment time window | Join condition: `sensor.timestamp BETWEEN assignment.start_time AND COALESCE(assignment.end_time, CURRENT_TIMESTAMP) AND sensor.truck_id = assignment.truck_id`. Only count readings during actual shipment transit. |
| **TR-024** | Temperature Alert Logic | Flag violations based on shipment type | Join with threshold reference table. Alert if `avg_temperature < min_threshold OR avg_temperature > max_threshold`. Store boolean: `temperature_alert TRUE/FALSE`. |
| **TR-025** | Temperature Alert Severity | Calculate deviation-based severity | None: within threshold. Minor: 0-2°C deviation. Major: 2-5°C deviation. Critical: >5°C deviation. Formula: `ABS(avg_temp - threshold_bound)`. |
| **TR-026** | Airflow Executor Selection | Use LocalExecutor for parallel task execution | LocalExecutor supports parallelism on single machine, better than SequentialExecutor for multi-stage DAG. Suitable for laptop with 4+ cores. Max 4 parallel tasks. |
| **TR-027** | Airflow DAG Structure | Single DAG with parallel Bronze ingestion | DAG: `smart_logistics_pipeline`. Tasks run in parallel where no dependencies exist. Bronze (SQL) and Bronze (IoT) run concurrently. Silver tasks wait for respective Bronze completion. |
| **TR-028** | Airflow Task Dependencies | Explicit dependency chain | `start >> [bronze_sql, bronze_iot]`, `bronze_sql >> silver_transactional`, `bronze_iot >> silver_iot`, `[silver_transactional, silver_iot] >> gold_aggregate >> data_quality_check >> end`. |
| **TR-029** | Airflow DAG Schedule | Manual trigger + hourly schedule | `schedule_interval='@hourly'` for production simulation. Can be triggered manually via UI for testing. Use `catchup=False` to prevent backfill on start. |
| **TR-030** | Airflow Retry Policy | 3 retries with exponential backoff | `retries=3`, `retry_delay=timedelta(minutes=2)`, `retry_exponential_backoff=True`, `max_retry_delay=timedelta(minutes=10)`. Handles transient failures (network, resource). |
| **TR-031** | Airflow Sensor for File Arrival | FileSensor to detect new IoT files | `FileSensor(task_id='wait_for_iot_files', filepath='/data/iot_raw/*.json', poke_interval=60, timeout=300)`. Only start Bronze IoT if files exist. |
| **TR-032** | Airflow Email Alerts | Configure failure notifications | `email_on_failure=True`, `email=['data-eng-team@smartlogistics.com']`. Requires SMTP configuration in docker-compose. |
| **TR-033** | Spark Cluster Architecture | Standalone cluster with 1 master + 1 worker | Master: orchestration only. Worker: 2 cores, 3GB RAM. Suitable for laptop with 8GB+ total RAM. Spark runs in Docker containers. |
| **TR-034** | Spark Resource Allocation - Driver | Driver memory and cores | `spark.driver.memory=1g`, `spark.driver.cores=1`. Driver coordinates tasks, doesn't need much memory for this workload. |
| **TR-035** | Spark Resource Allocation - Executor | Executor memory and cores | `spark.executor.memory=3g`, `spark.executor.cores=2`, `spark.executor.instances=1`. All processing happens in single executor on laptop. |
| **TR-036** | Spark Configuration - Parallelism | Configure parallelism for small cluster | `spark.default.parallelism=4`, `spark.sql.shuffle.partitions=4`. Match to available cores. Default 200 partitions is overkill for laptop. |
| **TR-037** | Spark Configuration - Delta Lake | Enable Delta Lake extensions | `spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension`, `spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog`. Required for Delta Lake operations. |
| **TR-038** | Spark Version Selection | Use Spark 3.5.0 with Delta Lake 3.0.0 | Compatible versions. Scala 2.12. Latest stable releases with good Delta Lake support. Image: `bitnami/spark:3.5.0`. |
| **TR-039** | Spark Logging Configuration | INFO level logging to console and file | `log4j.rootCategory=INFO`. Logs to `/opt/spark/logs/` with daily rotation. Retain 7 days. Balance verbosity with debuggability. |
| **TR-040** | Sample Data - Time Range | Generate 2 weeks of historical data | Data range: 2026-01-23 to 2026-02-06 (14 days). Shipments created across this period. Sensor readings span active shipment durations. |
| **TR-041** | Sample Data - Shipments Distribution | 100 shipments with realistic status distribution | Created: 5, Assigned: 8, In Transit: 15, Out for Delivery: 12, Delivered: 50, Cancelled: 5, Returned: 3, Failed Delivery: 2. Delivered is majority (realistic). |
| **TR-042** | Sample Data - Shipment Types | Distribution across 6 cargo types | Refrigerated: 30, Frozen: 15, Pharmaceutical: 10, Perishable: 20, Ambient: 20, Dry Goods: 5. Refrigerated is most common. |
| **TR-043** | Sample Data - Trucks | 50 trucks with Indian license plates | Format: `<State>-<District>-<Series>-<Number>`. Examples: `DL-01-AB-1234` (Delhi), `MH-02-CD-5678` (Mumbai), `KA-03-EF-9012` (Bangalore). Realistic registration patterns. |
| **TR-044** | Sample Data - Sensor Readings | 1000+ readings over 2 weeks | ~20 readings per active truck. Sample every 15-30 minutes during transit. Realistically sparse (trucks not always active). |
| **TR-045** | Sample Data - Temperature Patterns | Realistic temperature with variations | Refrigerated: Normal dist. mean=5°C, stddev=1.5°C. 10% of shipments have violations (temp >8°C or <2°C for periods). Frozen: mean=-20°C, stddev=2°C. Ambient: mean=20°C, stddev=3°C. |
| **TR-046** | Sample Data - GPS Routes | Realistic Indian city routes | Define 10 common routes: Delhi-Mumbai, Bangalore-Chennai, Kolkata-Hyderabad, etc. Generate waypoints along highways. Lat/Long progress realistically over time. |
| **TR-047** | Sample Data - Shipment Duration | Realistic transit times | Local (<300km): 4-8 hours. Regional (300-800km): 12-24 hours. Long-haul (>800km): 24-60 hours. Status changes at realistic intervals. |
| **TR-048** | Sample Data - Drivers and Warehouses | Supporting dimension data | 30 drivers with Indian names (Faker library). 20 warehouses in major cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad). Realistic phone numbers, addresses. |
| **TR-049** | Sample Data Generation - Idempotency | Deterministic generation with seed | `random.seed(42)`, `np.random.seed(42)`. Same seed = same data every run. Enables reproducible testing. |
| **TR-050** | Sample Data Generation - Foreign Keys | Maintain referential integrity | Orders.customer_id references Customers (generate 50 customers). Shipments.order_id references Orders. Shipments.origin_warehouse_id references Warehouses. No orphan records. |
| **TR-051** | Error Handling - Dead Letter Queue Pattern | Rejected records table in Bronze layer | Table: `bronze_rejected_records(record_id, source_table, source_file, rejection_reason, rejection_timestamp, raw_payload JSON, reprocessing_status)`. Stores all failed records with metadata. |
| **TR-052** | Error Handling - Rejection Reasons | Categorized rejection taxonomy | Reasons: `SCHEMA_VALIDATION_FAILED`, `NULL_CRITICAL_FIELD`, `INVALID_FOREIGN_KEY`, `DUPLICATE_DETECTED`, `LATE_ARRIVAL`, `MALFORMED_JSON`, `OUTLIER_DETECTED`, `BUSINESS_RULE_VIOLATION`. Enables analytics on failure patterns. |
| **TR-053** | Error Handling - Reprocessing Workflow | Manual review and reprocessing capability | Rejected records table has `reprocessing_status` (PENDING/REVIEWED/REPROCESSED/DISCARDED). Data engineer reviews weekly, fixes issues, updates status, reruns pipeline with corrected data. |
| **TR-054** | Error Handling - Exception Logging | Comprehensive error tracking | PySpark jobs log exceptions to `/opt/spark/logs/errors/`. Include: timestamp, DAG run ID, task ID, exception type, stack trace, affected record IDs. Airflow also logs task failures. |
| **TR-055** | Data Quality - Row Count Reconciliation | Validate counts between layers | After each layer: `source_count - rejected_count = target_count`. Log discrepancies. Alert if rejection rate >5%. Store metrics in `dq_metrics(layer, table, run_date, source_count, target_count, rejected_count, pass_fail)`. |
| **TR-056** | Data Quality - Null Value Checks | Enforce NOT NULL on critical fields | Bronze→Silver: Reject if NULL in `shipment_id`, `truck_id`, `timestamp`, `temperature`. Log to rejected_records. Silver layer has 0 nulls in critical fields. |
| **TR-057** | Data Quality - Duplicate Detection | Remove exact duplicates in Silver | Deduplicate on composite key: `(truck_id, timestamp)` for IoT, `(shipment_id, version)` for transactional. Keep first occurrence. Log duplicate count. |
| **TR-058** | Data Quality - Referential Integrity | Validate foreign keys during Silver load | Check: Shipments.order_id exists in Orders. Truck_assignments.truck_id exists in Vehicles. Reject orphan records. Ensures clean joins in Gold layer. |
| **TR-059** | Data Quality - Outlier Detection | Flag sensor anomalies | Temperature outliers: <-40°C or >60°C (sensor error). GPS outliers: impossible speed (>150 km/h). Flag as `is_outlier=TRUE` in Silver, exclude from Gold aggregations. Log to rejected_records. |
| **TR-060** | Data Quality - Business Rule Validation | Validate business logic | Rules: shipment_end_time >= shipment_start_time. Temperature thresholds exist for all shipment types. Truck assignments don't overlap for same truck. Reject violations. |

---

## Architecture Decisions

### **1. Medallion Architecture Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │   PostgreSQL     │              │   IoT JSON Files │         │
│  │  (5 tables)      │              │   (sensor data)  │         │
│  └──────────────────┘              └──────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                      │                          │
                      ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BRONZE LAYER (Raw)                          │
│  Partition: ingestion_date=YYYY-MM-DD                           │
│  ┌────────────────────┐          ┌─────────────────────┐        │
│  │ Transactional      │          │ IoT Telemetry       │        │
│  │ (Orders, etc.)     │          │ (Temp, GPS)         │        │
│  └────────────────────┘          └─────────────────────┘        │
│  ┌────────────────────────────────────────────────────┐         │
│  │ Rejected Records (Dead Letter Queue)              │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                      │                          │
                      ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SILVER LAYER (Cleaned + SCD2)                  │
│  Partition: created_date / reading_date                         │
│  ┌────────────────────┐          ┌─────────────────────┐        │
│  │ Shipments (SCD2)   │          │ IoT Telemetry       │        │
│  │ Orders, Vehicles   │          │ (Cleaned sensors)   │        │
│  │ Warehouses, etc.   │          │                     │        │
│  └────────────────────┘          └─────────────────────┘        │
│  ┌────────────────────────────────────────────────────┐         │
│  │ Truck Assignments (Mapping Table)                 │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GOLD LAYER (Analytics)                        │
│  Partition: year=YYYY / month=MM                                │
│  ┌────────────────────────────────────────────────────┐         │
│  │ Shipment Analytics (Joined + Aggregated)          │         │
│  │ - Shipment details                                │         │
│  │ - Average temperature                             │         │
│  │ - Alert flags & severity                          │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### **2. SCD Type 2 Implementation**

#### **Schema Design:**
```sql
CREATE TABLE silver.shipments (
    shipment_sk BIGINT PRIMARY KEY,           -- Surrogate key (auto-increment)
    shipment_id VARCHAR(50) NOT NULL,         -- Natural business key
    order_id VARCHAR(50) NOT NULL,
    origin_warehouse_id INT,
    dest_warehouse_id INT,
    shipment_type VARCHAR(50),
    status VARCHAR(50),                       -- Tracked field for SCD2
    assigned_driver_id INT,
    assigned_truck_id INT,
    shipment_start_time TIMESTAMP,
    shipment_end_time TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- SCD Type 2 columns
    version INT NOT NULL,                     -- Version number (1, 2, 3...)
    effective_start_timestamp TIMESTAMP(6),   -- Microsecond precision
    effective_end_timestamp TIMESTAMP(6),     -- NULL for current record
    is_current BOOLEAN DEFAULT TRUE,          -- TRUE only for latest version
    created_date DATE                         -- Partition key
);
```

#### **Merge Logic (PySpark):**
```python
# Simplified pseudo-code
deltaTable.alias("target").merge(
    updates.alias("source"),
    "target.shipment_id = source.shipment_id AND target.is_current = TRUE"
).whenMatchedUpdate(
    condition = "target.status != source.status",  # Status changed
    set = {
        "is_current": "FALSE",
        "effective_end_timestamp": "source.event_timestamp"
    }
).whenNotMatchedInsert(
    values = {
        "shipment_sk": "auto_increment",
        "version": "COALESCE(target.version, 0) + 1",
        "effective_start_timestamp": "source.event_timestamp",
        "effective_end_timestamp": "NULL",
        "is_current": "TRUE",
        ...
    }
).execute()
```

### **3. Airflow DAG Visualization**

```
start
  ├─> wait_for_iot_files (FileSensor)
  │
  ├─> bronze_ingest_sql ──────────────────────> silver_transactional
  │                                                      │
  └─> bronze_ingest_iot ──────────────────────> silver_iot
                                                         │
                                                         ├─> gold_aggregate
                                                         │         │
                                                         │         ▼
                                                         │   data_quality_check
                                                         │         │
                                                         └─────────> end
```

### **4. Docker Compose Services**

| Service | Image | Ports | Memory | CPU | Purpose |
|---------|-------|-------|--------|-----|---------|
| postgres | postgres:15 | 5432 | 512MB | 1 | Source transactional DB |
| spark-master | bitnami/spark:3.5.0 | 8080, 7077 | 1GB | 1 | Spark cluster master |
| spark-worker | bitnami/spark:3.5.0 | 8081 | 3GB | 2 | Spark processing worker |
| airflow-webserver | apache/airflow:2.8.0 | 8090 | 1GB | 1 | Airflow UI |
| airflow-scheduler | apache/airflow:2.8.0 | - | 1GB | 1 | DAG scheduler |
| airflow-init | apache/airflow:2.8.0 | - | 512MB | 1 | DB initialization |

**Total Resource Requirement:** ~7.5GB RAM, 7 CPUs  
**Minimum Laptop Spec:** 8GB RAM, 4-core CPU (with swap), 20GB disk

### **5. Directory Structure**

```
smart-logistics-lakehouse/
├── docker-compose.yml
├── .env
├── README.md
│
├── airflow/
│   ├── dags/
│   │   └── smart_logistics_pipeline.py
│   ├── logs/
│   └── plugins/
│
├── spark/
│   ├── scripts/
│   │   ├── bronze_ingest_sql.py
│   │   ├── bronze_ingest_iot.py
│   │   ├── silver_transform_transactional.py
│   │   ├── silver_transform_iot.py
│   │   └── gold_aggregate.py
│   ├── jars/
│   │   └── delta-core_2.12-3.0.0.jar
│   └── logs/
│
├── data/
│   ├── delta-lake/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   ├── iot_raw/          # IoT JSON files land here
│   └── postgres/         # PostgreSQL data volume
│
├── scripts/
│   ├── generate_sample_data.py
│   ├── init_postgres.sql
│   └── create_delta_tables.py
│
└── docs/
    ├── architecture.md
    └── setup_guide.md
```

### **6. Error Handling Flow**

```
Record arrives
    │
    ▼
┌─────────────────────┐
│ Schema Validation   │
└─────────────────────┘
    │
    ├─ PASS ──> Continue to next check
    │
    └─ FAIL ──> rejected_records (reason: SCHEMA_VALIDATION_FAILED)
                STOP
    │
    ▼
┌─────────────────────┐
│ Null Value Check    │
└─────────────────────┘
    │
    ├─ PASS ──> Continue
    │
    └─ FAIL ──> rejected_records (reason: NULL_CRITICAL_FIELD)
    │
    ▼
┌─────────────────────┐
│ Duplicate Check     │
└─────────────────────┘
    │
    ├─ UNIQUE ──> Continue
    │
    └─ DUPLICATE ──> rejected_records (reason: DUPLICATE_DETECTED)
    │
    ▼
┌─────────────────────┐
│ Business Rules      │
└─────────────────────┘
    │
    ├─ PASS ──> Load to Silver Layer ✓
    │
    └─ FAIL ──> rejected_records (reason: BUSINESS_RULE_VIOLATION)
```

**Weekly Review Process:**
1. Data Engineer queries `rejected_records` WHERE `reprocessing_status = 'PENDING'`
2. Analyze rejection patterns (e.g., common schema issues)
3. Fix source data or update validation rules
4. Mark as `REPROCESSED` or `DISCARDED`
5. Rerun pipeline for reprocessed records

### **7. Performance Optimizations**

| Optimization | Layer | Configuration | Impact |
|--------------|-------|---------------|--------|
| Auto-Optimize | All | `optimizeWrite.enabled=true` | Prevents small files |
| Z-ORDER | Silver/Gold | Weekly maintenance job | 30-50% faster queries |
| Partition Pruning | All | Date-based partitions | 80-95% less data scanned |
| Broadcast Joins | Gold | `broadcast(dim_table)` | Avoid shuffles for small tables |
| File Compaction | All | Target 128MB files | Optimal read performance |
| Cache SCD Lookups | Silver | `.cache()` on current records | Faster SCD merges |

---

## Data Quality Framework

| Check Type | Layer | Frequency | Threshold | Action on Failure |
|------------|-------|-----------|-----------|-------------------|
| Row Count Reconciliation | All | Every run | 100% ± rejected | Alert + log |
| Null Value Check | Silver | Every run | 0% nulls in critical fields | Reject record |
| Duplicate Detection | Silver | Every run | < 1% duplicates | Deduplicate |
| Referential Integrity | Silver | Every run | 100% valid FKs | Reject orphans |
| Outlier Detection | Silver | Every run | < 2% outliers | Flag, exclude from Gold |
| Business Rule Validation | Silver | Every run | 100% compliance | Reject violations |
| SCD2 History Integrity | Silver | Daily | No gaps in effective dates | Alert + manual review |

---

## Sample Data Specifications

### **Realistic Data Generation Parameters**

| Entity | Count | Distribution | Characteristics |
|--------|-------|--------------|-----------------|
| **Customers** | 50 | Indian names via Faker | Phone: +91-XXXXXXXXXX, cities across India |
| **Orders** | 150 | 1-3 orders per customer | Order amount: ₹5,000 - ₹50,000 (normal dist.) |
| **Shipments** | 100 | 1-2 shipments per order | Types: 30% Refrigerated, 20% Frozen, 30% Ambient, 20% other |
| **Vehicles** | 50 | Indian license plates | DL/MH/KA/TN prefixes, 30 with refrigeration units |
| **Drivers** | 30 | Indian names | License valid, phone numbers |
| **Warehouses** | 20 | Major cities | Mumbai (4), Delhi (3), Bangalore (3), Chennai (2), others (8) |
| **Truck Assignments** | 120 | 1.2x shipments (some reassignments) | 10% of shipments have mid-route truck changes |
| **IoT Readings** | 1200 | ~12 readings per shipment | Every 15-30 min during transit, realistic gaps |

### **Temperature Data Patterns**

| Shipment Type | Target Range | Mean | Std Dev | Violation Rate | Pattern |
|---------------|--------------|------|---------|----------------|---------|
| Refrigerated | 2-8°C | 5°C | 1.5°C | 10% (>8°C) | Gradual increase in summer heat |
| Frozen | ≤-18°C | -20°C | 2°C | 8% (>-18°C) | Spikes during loading/unloading |
| Pharmaceutical | 2-8°C | 5°C | 0.8°C | 5% (critical alerts) | Tight control, few violations |
| Perishable | 0-4°C | 2°C | 1°C | 12% (>4°C) | Morning deliveries cooler |
| Ambient | 15-25°C | 20°C | 3°C | 5% (>25°C) | Follows outdoor temperature |
| Dry Goods | -10-35°C | 25°C | 5°C | 3% (>35°C) | Wide tolerance, rare violations |

### **Shipment Status Transitions**

```
Created (Day 0, 00:00)
   ↓ (2-6 hours)
Assigned (Day 0, 04:00)
   ↓ (1-3 hours)
In Transit (Day 0, 06:00)
   ↓ (4-60 hours depending on distance)
Out for Delivery (Day 0-2, variable)
   ↓ (2-4 hours)
Delivered (Day 0-3, variable)

Alternate paths:
Created → Cancelled (before assignment)
In Transit → Failed Delivery → Returned
Out for Delivery → Failed Delivery → (retry) → Delivered
```

### **Realistic Routes (GPS Waypoints)**

| Route | Distance | Duration | Waypoints | Temperature Challenge |
|-------|----------|----------|-----------|----------------------|
| Delhi → Mumbai | 1,400 km | 24-30 hrs | 12 waypoints via NH48 | Hot days in Rajasthan |
| Bangalore → Chennai | 350 km | 6-8 hrs | 5 waypoints via NH44 | Consistent temps |
| Kolkata → Hyderabad | 1,500 km | 28-36 hrs | 14 waypoints via NH16 | Humid coastal regions |
| Mumbai → Pune | 150 km | 3-4 hrs | 3 waypoints via Expressway | Short haul, easy |
| Delhi → Jaipur | 280 km | 5-6 hrs | 4 waypoints via NH48 | Desert heat |

Each route has lat/long coordinates at major milestones, with intermediate points interpolated linearly with time.

---

## Technology Stack Versions

| Component | Version | Justification |
|-----------|---------|---------------|
| Apache Spark | 3.5.0 | Latest stable, best Delta Lake support |
| Delta Lake | 3.0.0 | Compatible with Spark 3.5, production-ready |
| Scala | 2.12 | Required for Spark 3.5 |
| Apache Airflow | 2.8.0 | Latest stable, LocalExecutor support |
| PostgreSQL | 15 | Modern, performant, JSON support |
| Python | 3.10 | Airflow 2.8 compatible |
| PySpark | 3.5.0 | Matches Spark version |
| Docker | 24.x | Latest stable |
| Docker Compose | 2.x | V2 syntax |

---

## Security & Compliance

| Requirement | Implementation |
|-------------|----------------|
| Database Credentials | Store in `.env`, do not commit to Git |
| Airflow Connections | Use Airflow Secrets Backend |
| Data Encryption at Rest | Enable filesystem encryption on host machine |
| Data Lineage | Track via `processed_files_log` and Delta Lake transaction log |
| GDPR/Data Retention | VACUUM retains 7 days, then purge. Configurable. |
| Audit Trail | All SCD2 changes logged with timestamp, all file processing logged |

---

## Deployment Instructions

### **Prerequisites**
- Windows 10/11 with WSL2 enabled
- Docker Desktop with 8GB RAM allocated
- At least 20GB free disk space
- Internet connection for pulling images

### **Setup Steps**
1. Clone repository
2. Copy `.env.example` to `.env`, configure credentials
3. Run `docker-compose up -d`
4. Wait for all services to start (~5 minutes)
5. Access Airflow UI: `http://localhost:8090` (user: admin, pwd: admin)
6. Run sample data generation: `docker exec spark-master python /scripts/generate_sample_data.py`
7. Trigger DAG manually: Airflow UI → DAGs → `smart_logistics_pipeline` → Play button
8. Monitor progress in Airflow UI and Spark UI (`http://localhost:8080`)

### **Validation**
- Check Bronze tables: `SELECT COUNT(*) FROM delta.`/data/delta-lake/bronze/shipments``
- Check Silver SCD2: `SELECT shipment_id, version, status, is_current FROM delta.`/data/delta-lake/silver/shipments``
- Check Gold analytics: `SELECT * FROM delta.`/data/delta-lake/gold/shipment_analytics` WHERE temperature_alert = TRUE`

---

## Monitoring & Observability

| Metric | Tool | Threshold | Alert |
|--------|------|-----------|-------|
| DAG Success Rate | Airflow UI | > 95% | Email on failure |
| Task Duration | Airflow Gantt Chart | < 30 min per run | Log warning if >45 min |
| Rejection Rate | DQ Metrics Table | < 5% | Email if >10% |
| Storage Growth | Docker volume size | < 10GB total | Alert at 15GB |
| Spark Job Failures | Spark UI | 0 failures | Log all exceptions |
| File Processing Lag | Processed Files Log | < 1 hour | Alert if >2 hours |

---

## Testing Strategy

### **Unit Tests**
- PySpark transformations: Test with sample DataFrames
- SCD2 merge logic: Test all scenarios (insert/update/no-change)
- Temperature calculations: Validate AVG aggregation
- Tools: `pytest`, `chispa` (Spark DataFrame testing)

### **Integration Tests**
- End-to-end DAG run with synthetic data
- Verify Bronze → Silver → Gold flow
- Validate SCD2 history preservation
- Check rejected_records handling

### **Data Quality Tests**
- Row count reconciliation: Source = Bronze = Silver (minus rejected)
- No nulls in critical columns
- All foreign keys valid
- Temperature alerts correctly flagged

---

## Future Enhancements (Out of Scope)

| Enhancement | Complexity | Value |
|-------------|------------|-------|
| Real-time streaming with Kafka | High | High - live alerts |
| ML-based spoilage prediction | Medium | High - proactive prevention |
| Cloud deployment (AWS/Azure) | Medium | Medium - scalability |
| Customer tracking portal | Medium | Medium - transparency |
| Advanced analytics (time series) | Low | Medium - trend analysis |
| Multi-tenancy support | High | Low - not needed for single company |

---

**Document Status:** Final  
**Review Status:** Approved for Implementation  
**Next Steps:** Proceed with implementation plan creation
