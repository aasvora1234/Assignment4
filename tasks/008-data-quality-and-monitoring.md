# Task 008: Data Quality and Monitoring

## Objective
Implement comprehensive data quality checks, monitoring framework, and metadata tracking for the entire lakehouse pipeline.

## Scope

### 1. Data Quality Metrics Table
- Create dq_metrics Delta table to store quality check results
- Track metrics per layer, table, and DAG run
- Store source counts, target counts, rejected counts
- Calculate and store rejection rates
- Track pass/fail status for each check
- Add timestamp and DAG run ID for traceability

### 2. Row Count Reconciliation
- Implement count validation between layers
- Verify Bronze count = Source count
- Verify Silver count = Bronze count - Rejected count
- Verify Gold count matches expected aggregations
- Alert if discrepancies exceed threshold (1%)
- Log reconciliation results to dq_metrics

### 3. Data Quality Validation Framework
- Implement null value percentage checks
- Track duplicate detection and removal counts
- Validate referential integrity violations
- Monitor outlier detection rates
- Check business rule compliance rates
- Calculate overall data quality score per table

### 4. SCD Type 2 History Validation
- Verify no gaps in effective date ranges
- Check that only one record has is_current = TRUE per shipment_id
- Validate version numbering is sequential
- Detect overlapping time periods
- Ensure closed records have non-null end dates

### 5. Rejected Records Analysis
- Create summary views of rejected records by reason
- Track rejection trends over time
- Calculate rejection rate by source table
- Identify most common rejection reasons
- Generate alerts when rejection rate > 5%

### 6. Pipeline Performance Monitoring
- Track DAG execution time per run
- Monitor individual task durations
- Identify performance bottlenecks
- Log Spark job execution metrics
- Track storage growth over time

### 7. Delta Lake Health Checks
- Monitor small file problem (file count per partition)
- Track table size growth
- Verify VACUUM operations running correctly
- Check Z-ORDER optimization status
- Monitor transaction log size

### 8. Alerting and Notifications
- Configure alert thresholds for all metrics
- Implement email notifications for critical issues
- Create alert for rejection rate > 10%
- Alert on DAG execution time > 45 minutes
- Notify on data quality score drop

## Success Criteria
- Data quality metrics table populated after each run
- Row count reconciliation passes for all layers
- All data quality checks execute successfully
- SCD Type 2 validation confirms history integrity
- Rejected records properly tracked and categorized
- Performance metrics logged and accessible
- Alerts trigger correctly when thresholds exceeded
- Dashboard queries return meaningful insights
- Monitoring framework requires minimal manual intervention

## Dependencies
- Task 007 completed (DAG running successfully)
- All layers populated with data
- Rejected records table operational

## Deliverables
- data_quality_check.py PySpark script
- dq_metrics table schema and implementation
- Row count reconciliation logic
- Data quality validation checks
- SCD Type 2 history validation queries
- Rejected records analysis queries
- Performance monitoring dashboards (SQL queries)
- Alerting configuration and thresholds
- Documentation on monitoring and interpretation of metrics
