# Business Product Requirements Document (PRD)
## Smart Logistics Tracking - Local-First Lakehouse

**Project Name:** Smart Logistics Tracking Lakehouse  
**Version:** 1.0  
**Date:** 2026-02-06  
**Owner:** Data Engineering Team

---

## Executive Summary

Design and implement an end-to-end, local-first Lakehouse architecture for Smart Logistics Tracking, a delivery company that needs to combine business transactional records with real-time IoT sensor data from delivery trucks to prevent goods spoilage during transit. The solution will use Medallion Architecture (Bronze, Silver, Gold layers) with Delta Lake, orchestrated via Apache Airflow, running locally via Docker Compose.

---

## Business Requirements

| Requirement ID | Description | User Story | Expected Behaviour/Outcome |
|----------------|-------------|------------|---------------------------|
| **BR-001** | PostgreSQL Source Database Setup | As a data engineer, I need a PostgreSQL database with 5 core transactional tables to store business operations data | PostgreSQL database container with tables: Shipments, Orders, Vehicles, Warehouses, Drivers. Sample data: 100 shipments, 50 trucks, 20 warehouses, 30 drivers, 150 orders |
| **BR-002** | IoT Sensor Data Ingestion | As a logistics manager, I need to capture temperature and location data from delivery trucks to monitor cargo conditions | JSON files containing sensor readings (Truck ID, Timestamp, Temperature, Latitude, Longitude) with 1000+ sample records stored in a monitored folder |
| **BR-003** | Shipment-to-Truck Mapping | As a dispatcher, I need to know which truck is assigned to which shipment during transit | A mapping table that links shipments to trucks with start and end timestamps for accurate trip tracking |
| **BR-004** | Temperature Threshold Management | As a compliance officer, I need different temperature thresholds for different types of goods (refrigerated, frozen, ambient) | Reference table storing shipment types with min/max temperature thresholds: Refrigerated (2-8°C), Frozen (≤-18°C), Ambient (15-25°C) |
| **BR-005** | Medallion Architecture - Bronze Layer | As a data engineer, I need to store raw data exactly as received without any transformations | Bronze layer Delta Lake tables for both transactional data and IoT sensor data with no schema enforcement or cleaning |
| **BR-006** | Medallion Architecture - Silver Layer (Transactional) | As a data analyst, I need clean, deduplicated transactional data with proper data types and quality checks | Silver layer Delta Lake tables with cleaned data: type conversions, duplicate removal, null handling, data validation |
| **BR-007** | SCD Type 2 Implementation for Shipments | As a logistics analyst, I need to track all historical status changes for shipments (Created → Assigned → In Transit → Out for Delivery → Delivered → Cancelled) | Shipments table in Silver layer with SCD Type 2: effective_start_date, effective_end_date, is_current flag. Each status change creates a new record with history preserved |
| **BR-008** | Medallion Architecture - Silver Layer (IoT) | As a quality manager, I need clean, validated sensor data with proper timestamps and data quality checks | Silver layer Delta Lake table for IoT telemetry with cleaned data, timezone standardization, outlier detection, and duplicate removal |
| **BR-009** | Gold Layer - Shipment Temperature Analytics | As a business analyst, I need to analyze average temperature conditions for each shipment to identify spoilage risks | Gold layer table joining Shipments with average temperature (AVG), matching by truck_id + shipment time range. Include shipment details, truck info, and calculated metrics |
| **BR-010** | Temperature Alert Detection | As a logistics manager, I need to identify shipments where temperature exceeded safe thresholds during transit | Gold layer includes alert flags: temperature_alert (boolean), temperature_violation_severity (None, Minor, Major, Critical) based on threshold breaches |
| **BR-011** | Docker Compose Infrastructure | As a DevOps engineer, I need a fully containerized local environment to run the entire lakehouse stack | docker-compose.yml with services: PostgreSQL, Apache Airflow (webserver, scheduler, worker), Apache Spark (master, worker), Delta Lake storage |
| **BR-012** | Airflow DAG Orchestration | As a data engineer, I need automated pipeline execution with proper task dependencies and error handling | Single Airflow DAG with tasks: Bronze ingestion (SQL + IoT) → Silver transformation (with dependencies) → Gold aggregation. Manual trigger for testing, hourly schedule for production |
| **BR-013** | Task Dependencies Management | As a workflow manager, I need to ensure Gold layer processing starts only after both transactional and IoT Silver layers complete | Airflow DAG with explicit task dependencies: bronze_sql → silver_transactional, bronze_iot → silver_iot, [silver_transactional + silver_iot] → gold_analytics |
| **BR-014** | Sample Data Generation | As a QA engineer, I need realistic sample data to test the pipeline end-to-end | Python scripts to generate: 100 shipments with realistic status transitions, 50 trucks, 1000 sensor readings with temperature variations, proper foreign key relationships |
| **BR-015** | Shipment Status Lifecycle | As a logistics coordinator, I need to track shipments through their entire lifecycle with realistic status transitions | Shipment statuses: Created, Assigned, In Transit, Out for Delivery, Delivered, Cancelled, Returned, Failed Delivery. Only current records marked as is_current=True |
| **BR-016** | PySpark Processing Scripts | As a data engineer, I need PySpark scripts for each layer transformation with proper error handling and logging | Separate PySpark scripts: bronze_ingest_sql.py, bronze_ingest_iot.py, silver_transform_transactional.py, silver_transform_iot.py, gold_aggregate.py |
| **BR-017** | Data Quality Validation | As a data steward, I need data quality checks between layers to ensure data integrity | Validation checks: row count reconciliation, null value checks for critical fields, duplicate detection, referential integrity validation |
| **BR-018** | Documentation and Setup Instructions | As a new developer, I need clear documentation to set up and run the lakehouse locally | README.md with: prerequisites, setup steps, how to run docker-compose, how to trigger Airflow DAG, how to query Delta Lake tables, troubleshooting guide |
| **BR-019** | Delta Lake Table Schema Design | As a data architect, I need well-defined schemas for all Bronze, Silver, and Gold tables | DDL definitions for all Delta Lake tables with proper data types, partitioning strategy (by date), and indexing considerations |
| **BR-020** | Temperature Analytics Calculations | As a data scientist, I need detailed temperature metrics for each shipment to analyze patterns | Gold table includes: avg_temperature, min_temperature, max_temperature, sensor_reading_count, trip_duration, temperature_variance |
| **BR-021** | Shipment Type Classification | As a warehouse manager, I need to categorize shipments by cargo type to apply correct handling procedures | Shipment types: Refrigerated, Frozen, Ambient, Perishable, Pharmaceutical, Dry Goods. Each type linked to temperature threshold requirements |
| **BR-022** | Time-based Sensor Matching | As a data analyst, I need to accurately match sensor readings to shipments based on truck assignment and time windows | Matching logic: sensor readings where timestamp BETWEEN shipment_start_time AND shipment_end_time AND truck_id matches assignment |
| **BR-023** | Alert Severity Classification | As a quality manager, I need to understand the severity of temperature violations | Alert severity levels: None (within threshold), Minor (1-2°C deviation), Major (2-5°C deviation), Critical (>5°C deviation or prolonged exposure) |
| **BR-024** | Incremental Data Loading | As a data engineer, I need to process only new/changed data to optimize performance | Implement incremental loading with watermarking: track last processed timestamp for IoT data, use CDC pattern for SQL source |
| **BR-025** | Local Storage Configuration | As an infrastructure engineer, I need persistent storage for Delta Lake tables accessible across container restarts | Docker volumes for Delta Lake storage, PostgreSQL data, Airflow metadata, ensuring data persists across container lifecycle |

---

## Data Sources

### Source 1: Transactional Data (PostgreSQL)
- **Tables:** Shipments, Orders, Vehicles, Warehouses, Drivers
- **Format:** Relational database (PostgreSQL)
- **Volume:** ~100 shipments, 50 vehicles, 30 drivers, 20 warehouses, 150 orders
- **Update Frequency:** Real-time (simulated as batch for POC)

### Source 2: IoT Telemetry Data
- **Format:** JSON files
- **Schema:** `{truck_id, timestamp, temperature, latitude, longitude}`
- **Volume:** 1000+ sensor readings
- **Frequency:** Continuous (simulated as file drops)

---

## Technical Architecture

### Medallion Layers
1. **Bronze Layer:** Raw data ingestion (no transformations)
2. **Silver Layer:** Cleaned, validated data with SCD Type 2 for Shipments
3. **Gold Layer:** Business-ready analytics with joined shipment + temperature data

### Technology Stack
- **Storage Format:** Delta Lake
- **Processing Engine:** Apache Spark (PySpark)
- **Orchestration:** Apache Airflow
- **Source Database:** PostgreSQL
- **Containerization:** Docker Compose

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Data Accuracy | 100% of records from source appear in Bronze layer |
| Data Quality | Zero duplicates in Silver layer, all critical fields non-null |
| SCD Type 2 Accuracy | All shipment status changes tracked with correct effective dates |
| Temperature Analytics | Gold layer accurately calculates average temperature per shipment |
| Alert Detection | 100% of threshold violations flagged correctly |
| Pipeline Reliability | DAG runs successfully end-to-end without failures |
| Local Deployment | All services start successfully via docker-compose |

---

## Out of Scope (Future Enhancements)
- Real-time streaming with Kafka
- Cloud deployment (AWS/Azure/GCP)
- ML-based predictive spoilage models
- Customer-facing tracking portal
- Mobile app integration
- Multi-region replication

---

## Appendix: Shipment Status Definitions

| Status | Description | Typical Duration |
|--------|-------------|------------------|
| Created | Order placed, shipment record created | Instant |
| Assigned | Driver and truck assigned to shipment | 1-2 hours |
| In Transit | Truck departed from warehouse | Hours to days |
| Out for Delivery | Truck reached destination city, final mile delivery | 2-4 hours |
| Delivered | Successfully delivered to customer | Terminal state |
| Cancelled | Shipment cancelled before delivery | Terminal state |
| Returned | Delivery failed, returned to warehouse | Terminal state |
| Failed Delivery | Delivery attempt failed, awaiting retry | 1-2 days |

---

## Appendix: Temperature Thresholds by Shipment Type

| Shipment Type | Min Temp (°C) | Max Temp (°C) | Alert Condition |
|---------------|---------------|---------------|-----------------|
| Refrigerated | 2 | 8 | Temperature < 2°C OR > 8°C |
| Frozen | -25 | -18 | Temperature > -18°C |
| Pharmaceutical | 2 | 8 | Temperature < 2°C OR > 8°C (Critical) |
| Perishable | 0 | 4 | Temperature > 4°C |
| Ambient | 15 | 25 | Temperature < 15°C OR > 25°C |
| Dry Goods | -10 | 35 | Temperature > 35°C (heat damage) |

---

**Document Status:** Draft  
**Review Required:** Yes  
**Approver:** Business Stakeholders + Technical Lead
