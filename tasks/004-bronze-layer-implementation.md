# Task 004: Bronze Layer Implementation

## Objective
Implement Bronze layer data ingestion from both PostgreSQL (transactional data) and JSON files (IoT telemetry) into Delta Lake with raw data preservation.

## Scope

### 1. Bronze Layer Schema Design
- Define Delta Lake table schemas for all 5 transactional tables
- Define Delta Lake schema for IoT telemetry data
- Include metadata columns (ingestion_timestamp, source_file, etc.)
- Set up partitioning strategy (daily partitions by ingestion_date for transactional, reading_date for IoT)

### 2. Bronze SQL Ingestion (PySpark)
- Create PySpark script to read from PostgreSQL
- Extract all 5 tables (Orders, Shipments, Vehicles, Warehouses, Drivers)
- Write to Delta Lake Bronze layer with no transformations
- Preserve exact source data structure and content
- Add ingestion metadata (ingestion_timestamp, source_system)
- Implement incremental loading capability (based on watermark)

### 3. Bronze IoT Ingestion (PySpark)
- Create PySpark script to read JSON files from mounted directory
- Parse JSON schema (truck_id, timestamp, temperature, latitude, longitude)
- Handle multiple files in batch processing
- Write to Delta Lake Bronze layer with partitioning by reading_date
- Add file metadata (source_file_name, file_size, processing_timestamp)

### 4. File Processing Tracking
- Create processed_files_log Delta table
- Log all processed IoT files with metadata (filename, path, record count, checksum, status)
- Track processing timestamps and status
- Enable idempotency (prevent reprocessing of same file)

### 5. Error Handling and Logging
- Implement try-catch blocks for error handling
- Log exceptions to Spark logs with context
- Handle malformed JSON files gracefully
- Track failed file processing attempts
- Configure Spark logging at appropriate level (INFO)

### 6. Bronze Rejected Records Table
- Create bronze_rejected_records Delta table (Dead Letter Queue)
- Define schema for rejected records with metadata
- Implement rejection reason categorization
- Store raw payload for later analysis
- Add reprocessing status tracking

### 7. Delta Lake Configuration
- Enable auto-optimize on write
- Configure target file size (128MB for laptop)
- Set up partition columns
- Enable Delta Lake transaction logging

## Success Criteria
- All PostgreSQL tables successfully ingested to Bronze
- All IoT JSON files processed and loaded
- Delta Lake tables created with correct partitioning
- Processed files tracked in metadata table
- No data loss during ingestion
- Rejected records properly captured
- Idempotent processing (can re-run safely)
- Files deleted after successful processing

## Dependencies
- Task 003 completed (sample data available)
- Spark cluster running
- Delta Lake configured
- Source data accessible (PostgreSQL + JSON files)

## Deliverables
- bronze_ingest_sql.py PySpark script
- bronze_ingest_iot.py PySpark script
- Delta Lake table creation scripts
- Processed files tracking implementation
- Error handling and logging framework
- Documentation on Bronze layer design and usage
