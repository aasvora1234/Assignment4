# Task 005: Silver Layer Implementation

## Objective
Implement Silver layer with data cleaning, validation, SCD Type 2 for Shipments, and comprehensive data quality checks.

## Scope

### 1. Silver Layer Schema Design
- Define cleaned schemas for all transactional tables
- Design SCD Type 2 schema for Shipments table with temporal columns
- Define cleaned schema for IoT telemetry
- Set up partitioning strategy (daily by created_date for transactional, reading_date for IoT)
- Add data quality flag columns (is_outlier, data_quality_score, etc.)

### 2. Data Cleaning and Transformation (Transactional)
- Implement data type conversions and standardization
- Remove exact duplicates
- Handle null values based on business rules
- Standardize formats (dates, phone numbers, addresses)
- Apply business rule validations
- Flag outliers and anomalies

### 3. SCD Type 2 Implementation for Shipments
- Implement surrogate key generation (shipment_sk)
- Add temporal columns (effective_start_timestamp, effective_end_timestamp, is_current)
- Add version column for tracking changes
- Implement MERGE logic for handling updates
- Track changes only on status column
- Close old records and insert new on status change
- Update in-place for non-tracked column changes
- Handle late-arriving data with rejection logic

### 4. Data Cleaning and Transformation (IoT)
- Clean sensor data with validation rules
- Standardize timestamp formats to UTC with microsecond precision
- Validate temperature ranges (reject < -40°C or > 60°C as sensor errors)
- Validate GPS coordinates (latitude, longitude ranges)
- Detect impossible location jumps
- Remove duplicate sensor readings
- Flag outliers for exclusion from Gold layer

### 5. Data Quality Validations
- Implement null value checks on critical fields
- Validate referential integrity (foreign keys)
- Check duplicate detection and removal
- Apply business rule validations
- Row count reconciliation with Bronze layer
- Calculate rejection rate and alert if > 5%

### 6. Rejected Records Processing
- Route validation failures to bronze_rejected_records table
- Categorize rejection reasons (SCHEMA_VALIDATION_FAILED, NULL_CRITICAL_FIELD, etc.)
- Store raw payload and metadata for rejected records
- Track rejection statistics by reason
- Enable reprocessing workflow

### 7. Silver Layer Optimization
- Implement Z-ORDER clustering on frequently queried columns
- Configure Delta Lake optimizations
- Set up incremental processing logic
- Implement efficient merge patterns for SCD Type 2

## Success Criteria
- All Bronze data successfully cleaned and loaded to Silver
- SCD Type 2 correctly implemented for Shipments with history preservation
- Zero nulls in critical fields in Silver layer
- Exact duplicates removed
- Referential integrity maintained
- Outliers properly flagged
- Rejection rate < 5%
- Row count reconciliation passes
- Z-ORDER applied successfully
- Query performance meets expectations

## Dependencies
- Task 004 completed (Bronze layer populated)
- Understanding of SCD Type 2 patterns
- Business rules documented

## Deliverables
- silver_transform_transactional.py PySpark script
- silver_transform_iot.py PySpark script
- SCD Type 2 MERGE logic implementation
- Data quality validation framework
- Data cleaning and transformation logic
- Rejected records routing implementation
- Documentation on Silver layer design, SCD Type 2 logic, and data quality rules
