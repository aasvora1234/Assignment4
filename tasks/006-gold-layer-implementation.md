# Task 006: Gold Layer Implementation

## Objective
Implement Gold layer analytics table that joins Shipments with IoT sensor data to calculate average temperatures and generate alerts based on thresholds.

## Scope

### 1. Gold Layer Schema Design
- Define schema for shipment_analytics aggregated table
- Include shipment details, truck information, and calculated metrics
- Add temperature analytics columns (avg_temperature)
- Add alert columns (temperature_alert boolean, alert_severity)
- Set up partitioning strategy (monthly by year/month)

### 2. Data Integration Logic
- Join current Shipments (is_current = TRUE) with truck_assignments
- Match IoT sensor readings to shipments using truck_id and time window
- Filter sensor readings within shipment start and end times
- Handle shipments with multiple truck assignments (reassignments)
- Exclude outlier sensor readings (is_outlier = TRUE)

### 3. Temperature Analytics Calculation
- Calculate average temperature (AVG) for each shipment
- Aggregate only sensor readings matching the shipment time window
- Handle shipments with no sensor data gracefully
- Round temperature values to 2 decimal places

### 4. Temperature Alert Detection
- Join with shipment type thresholds reference table
- Compare avg_temperature against min/max thresholds for shipment type
- Set temperature_alert flag (TRUE if violation, FALSE otherwise)
- Calculate alert severity based on deviation from threshold
  - None: within threshold
  - Minor: 0-2°C deviation
  - Major: 2-5°C deviation
  - Critical: >5°C deviation

### 5. Business Metrics Enrichment
- Include shipment metadata (shipment_id, order_id, status, type)
- Include truck and driver information
- Include warehouse origin and destination
- Add trip duration calculation
- Add sensor reading count per shipment
- Calculate delivery timeliness metrics

### 6. Gold Layer Optimization
- Implement Z-ORDER clustering on shipment_id and truck_id
- Configure monthly partitioning for efficient time-range queries
- Enable Delta Lake optimizations
- Optimize join strategies (broadcast small dimension tables)
- Implement incremental refresh logic

### 7. Data Quality Validation
- Validate all joins produce expected results
- Check for missing shipments in Gold layer
- Verify temperature calculations are accurate
- Validate alert detection logic
- Row count reconciliation against Silver Shipments

## Success Criteria
- Gold table successfully created with all shipments
- Average temperature calculated correctly
- Sensor readings properly matched to shipments by time window
- Alerts correctly flagged based on thresholds
- Alert severity accurately categorized
- No missing shipments due to join issues
- Monthly partitioning applied correctly
- Z-ORDER optimization completed
- Query performance meets requirements
- Business stakeholders can query for insights

## Dependencies
- Task 005 completed (Silver layer populated)
- Truck assignments table populated
- Temperature thresholds reference data available

## Deliverables
- gold_aggregate.py PySpark script
- Gold table schema definition
- Join logic implementation
- Alert detection logic
- Temperature calculation implementation
- Optimization configurations
- Sample analytical queries for validation
- Documentation on Gold layer design and business logic
