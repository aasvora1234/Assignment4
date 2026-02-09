# Task 007: Airflow DAG Orchestration

## Objective
Create a comprehensive Airflow DAG to orchestrate the entire Medallion pipeline with proper task dependencies, error handling, and monitoring.

## Scope

### 1. DAG Configuration
- Create smart_logistics_pipeline DAG
- Configure LocalExecutor for parallel task execution
- Set schedule to hourly (@hourly) with manual trigger capability
- Configure catchup=False to prevent backfill
- Set default_args (retries, retry_delay, email alerts)

### 2. Task Definitions
- Define start and end dummy tasks for clear visualization
- Define FileSensor task to wait for IoT files
- Define Bronze ingestion tasks (SQL and IoT)
- Define Silver transformation tasks (transactional and IoT)
- Define Gold aggregation task
- Define data quality validation task

### 3. Task Dependencies Setup
- Implement parallel Bronze ingestion (SQL and IoT run concurrently)
- Make Silver tasks depend on respective Bronze tasks
- Make Gold task depend on both Silver tasks completion
- Chain data quality check after Gold layer
- Create proper dependency graph with clear flow

### 4. Spark Job Integration
- Configure SparkSubmitOperator for each PySpark script
- Set Spark configuration parameters (master URL, resources)
- Pass required arguments to scripts (delta paths, dates, etc.)
- Configure JAR dependencies (Delta Lake)
- Set appropriate timeouts for long-running jobs

### 5. Error Handling and Retries
- Implement retry policy (3 retries with exponential backoff)
- Configure retry delays (2 min initial, 10 min max)
- Set up on_failure_callback for alerts
- Implement graceful failure handling
- Log detailed error information

### 6. Monitoring and Alerting
- Configure email alerts on task failure
- Set up task execution time monitoring
- Implement SLA monitoring
- Create custom metrics for DAG run tracking
- Log DAG run statistics

### 7. FileSensor Configuration
- Configure sensor to detect new IoT JSON files
- Set poke_interval (60 seconds)
- Set timeout (5 minutes)
- Define file path patterns to watch
- Handle sensor timeout gracefully

### 8. Airflow Connections and Variables
- Set up PostgreSQL connection in Airflow
- Configure Spark connection
- Define Airflow Variables for paths and configurations
- Externalize configuration for flexibility

## Success Criteria
- DAG visible in Airflow UI
- DAG validation passes (no syntax errors)
- All tasks properly defined and configured
- Task dependencies correctly implemented
- Manual trigger executes successfully
- Tasks run in correct order
- Parallel execution works for Bronze tasks
- Silver tasks wait for Bronze completion
- Gold task waits for both Silver tasks
- Retries work as expected on failures
- Email alerts trigger on failures
- DAG completes end-to-end successfully

## Dependencies
- Task 006 completed (all PySpark scripts ready)
- Airflow services running
- Spark cluster accessible
- PostgreSQL connection configured

## Deliverables
- smart_logistics_pipeline.py DAG file
- Airflow connections configuration
- Airflow variables setup
- Email alert configuration
- DAG documentation with task descriptions
- Monitoring and alerting setup
- Troubleshooting guide for common DAG issues
