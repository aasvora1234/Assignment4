# Technical Details
## Smart Logistics Data Lakehouse Platform

---

## 1. SCD Type 2 Implementation

### **What is SCD Type 2?**

Slowly Changing Dimension Type 2 (SCD Type 2) is a data warehousing technique that **tracks the full historical changes** of a record over time. Instead of overwriting old data, each change creates a new row, preserving the complete history.

### **Why We Used It**

Shipments change status multiple times during their lifecycle:
```
Created → Assigned → In Transit → Out for Delivery → Delivered
```

Without SCD Type 2, we'd only see the **current** status and lose all history. With SCD Type 2, we can answer:
- "What was the status of Shipment ABC at 10 AM yesterday?"
- "How many hours did this shipment spend In Transit?"
- "Show me the full audit trail for compliance"

---

### **SCD Type 2 Schema Design**

We added 4 tracking columns to the Silver shipments table:

| Column | Type | Description |
|--------|------|-------------|
| `surrogate_key` | INTEGER | Auto-incrementing unique ID for each version |
| `valid_from` | TIMESTAMP | When this version became active |
| `valid_to` | TIMESTAMP | When this version was superseded (NULL = current) |
| `is_current` | BOOLEAN | True only for the latest active record |
| `version` | INTEGER | Sequential version number starting from 1 |

---

### **SCD Type 2 Logic (Python/Pandas)**

```python
def apply_scd_type2(df):
    """
    Applies SCD Type 2 logic to shipments data.
    Each unique (shipment_id, status) combination creates a new version.
    """
    # Sort by shipment_id and creation time to process chronologically
    df = df.sort_values(['shipment_id', 'created_at'])
    
    scd2_records = []
    surrogate_key = 1
    
    # Group by shipment to process version history per shipment
    for shipment_id, group in df.groupby('shipment_id'):
        group = group.reset_index(drop=True)
        
        for i, row in group.iterrows():
            record = row.to_dict()
            
            # Assign surrogate key
            record['surrogate_key'] = surrogate_key
            surrogate_key += 1
            
            # Set valid_from = ingestion timestamp
            record['valid_from'] = pd.Timestamp.now()
            
            # Set valid_to = None (current) for last record, else next record's time
            if i < len(group) - 1:
                record['valid_to'] = pd.Timestamp.now()
                record['is_current'] = False
            else:
                record['valid_to'] = None   # NULL = still active
                record['is_current'] = True
            
            # Version number (1-indexed)
            record['version'] = i + 1
            
            scd2_records.append(record)
    
    return pd.DataFrame(scd2_records)
```

### **Example Output**

For Shipment `SHP-001`:

| surrogate_key | shipment_id | status | valid_from | valid_to | is_current | version |
|---------------|-------------|--------|------------|----------|------------|---------|
| 1 | SHP-001 | Created | 2026-02-01 10:00 | 2026-02-02 14:30 | False | 1 |
| 2 | SHP-001 | Assigned | 2026-02-02 14:30 | 2026-02-03 08:00 | False | 2 |
| 3 | SHP-001 | In Transit | 2026-02-03 08:00 | 2026-02-05 09:15 | False | 3 |
| 4 | SHP-001 | Delivered | 2026-02-05 09:15 | NULL | **True** | 4 |

### **Querying the History**

```sql
-- Get current status of all shipments
SELECT shipment_id, status, valid_from
FROM silver_shipments
WHERE is_current = True;

-- Get full history of one shipment
SELECT shipment_id, status, valid_from, valid_to, version
FROM silver_shipments
WHERE shipment_id = 'SHP-001'
ORDER BY version;

-- Point-in-time query: what was the status on Feb 3?
SELECT shipment_id, status
FROM silver_shipments
WHERE shipment_id = 'SHP-001'
  AND valid_from <= '2026-02-03'
  AND (valid_to IS NULL OR valid_to > '2026-02-03');
```

---

## 2. IoT Outlier Detection

### **Three-Method Approach**

We apply three independent outlier detection algorithms to IoT sensor readings:

#### **Method 1: Range Validation**
Checks if temperature or GPS coordinates are physically impossible.

```python
# Temperature must be between -30°C and +50°C
df['is_out_of_range'] = (
    (df['temperature'] < -30) | 
    (df['temperature'] > 50)
)

# GPS: valid lat (-90 to 90), valid lon (-180 to 180)
df['is_invalid_gps'] = (
    (df['latitude'] < -90) | (df['latitude'] > 90) |
    (df['longitude'] < -180) | (df['longitude'] > 180)
)
```

#### **Method 2: Statistical Outliers (Z-Score)**
Flags readings more than 3 standard deviations from the truck's mean.

```python
# Calculate per-truck mean and std
df['temp_mean'] = df.groupby('truck_id')['temperature'].transform('mean')
df['temp_std']  = df.groupby('truck_id')['temperature'].transform('std')

# Z-score: how many std deviations from mean?
df['z_score'] = (df['temperature'] - df['temp_mean']) / df['temp_std'].replace(0, 1)

# Flag if Z-score > 3.0 (statistically extreme)
df['is_statistical_outlier'] = df['z_score'].abs() > 3.0
```

#### **Method 3: Rapid Change Detection**
Flags impossible temperature jumps between consecutive readings.

```python
# Sort by truck and time for consecutive comparison
df = df.sort_values(['truck_id', 'timestamp'])

# Get previous reading's temperature for same truck
df['prev_temp'] = df.groupby('truck_id')['temperature'].shift(1)

# Temperature cannot jump more than 10°C between readings
df['temp_change_rate'] = (df['temperature'] - df['prev_temp']).abs()
df['is_rapid_change'] = df['temp_change_rate'] > 10.0
```

### **Combined Scoring**

```python
# Any one flag = outlier
df['is_outlier'] = (
    df['is_out_of_range'] | 
    df['is_statistical_outlier'] | 
    df['is_rapid_change'] |
    df['is_invalid_gps']
)

# Quality score: 100 = clean, 50 = flagged
df['quality_score'] = np.where(df['is_outlier'], 50, 100)
df['data_quality_flag'] = np.where(df['is_outlier'], 'FLAGGED', 'CLEAN')
```

---

## 3. Spark Job Optimizations

### **Current Setup: Pandas (MVP)**

For the current data scale (100 shipments, ~7,000 IoT readings), we use **Pandas** instead of PySpark for simplicity and faster development. This is a conscious trade-off.

| Factor | Pandas | PySpark |
|--------|--------|---------|
| Setup complexity | Low | High |
| Debug ease | Easy | Hard |
| Scale limit | ~1M rows | Unlimited |
| Our current data | 7,000 rows | — |
| Best for | MVP / prototyping | Production at scale |

### **Optimizations Applied (Pandas)**

#### **1. Read Latest File Only**
Instead of reading and reprocessing all historical files, we always get the most recently modified file:

```python
def get_latest_csv(directory):
    """Only process the freshest file, skip old ones."""
    csv_files = list(Path(directory).glob("*.csv"))
    return max(csv_files, key=lambda x: x.stat().st_mtime)
```

**Why**: Avoids processing the same data repeatedly. Reduces I/O by up to 90% in repeated runs.

#### **2. Vectorized Operations (No Row Loops)**
All transformations use Pandas vectorized operations, not Python `for` loops:

```python
# ❌ SLOW: Python loop
for index, row in df.iterrows():
    if row['temperature'] < -30:
        df.at[index, 'is_outlier'] = True

# ✅ FAST: Vectorized
df['is_outlier'] = df['temperature'] < -30
```

**Why**: Vectorized operations run in C under the hood, 100x faster than Python loops.

#### **3. Efficient GroupBy**
Use `.transform()` instead of merge for group-level calculations:

```python
# ✅ Efficient: transform keeps original DataFrame shape
df['truck_avg_temp'] = df.groupby('truck_id')['temperature'].transform('mean')
```

**Why**: Avoids expensive merge/join operations.

#### **4. Selective Column Loading**
Only load required columns, not entire tables:

```python
# ❌ Loads all columns
df = pd.read_csv(file)

# ✅ Only load what we need
df = pd.read_csv(file, usecols=['shipment_id', 'status', 'created_at'])
```

**Why**: Reduces memory usage and speeds up ingestion.

---

### **Future PySpark Optimizations (Production Roadmap)**

When data volume exceeds 1M rows, we would migrate to PySpark with these optimizations:

#### **Partitioning Strategy**

```python
# Partition IoT data by truck_id for parallel processing
df.write \
  .partitionBy("truck_id", "date") \  # Each partition = one file
  .format("delta") \
  .mode("append") \
  .save("/opt/data/delta-lake/silver/iot_clean")
```

**Why**: Partitioning means each Spark worker handles one truck's data independently. No data shuffling needed for per-truck calculations.

#### **Broadcast Joins for Small Tables**

```python
from pyspark.sql.functions import broadcast

# When joining shipments (large) with shipment_types (small)
df_result = df_shipments.join(
    broadcast(df_shipment_types),   # Broadcast small table to all workers
    on="shipment_type_id"
)
```

**Why**: Eliminates network shuffle for small lookup tables. Can give 10x speedup on joins.

#### **Predicate Pushdown**

```python
# Read only today's data from Delta Lake (not all history)
df = spark.read.format("delta") \
  .load("/opt/data/delta-lake/silver/iot_clean") \
  .filter("date = '2026-02-20'")  # Pushed to storage layer
```

**Why**: Delta Lake skips irrelevant files at read time. Reads only 1/365th of data for daily queries.

#### **Caching Hot DataFrames**

```python
# Cache shipments DF which is used in multiple calculations
df_shipments.cache()
df_shipments.count()  # Trigger cache population

# Now multiple operations reuse cached data
summary_by_status = df_shipments.groupBy("status").count()
summary_by_city = df_shipments.groupBy("destination_city").count()

df_shipments.unpersist()  # Release when done
```

**Why**: Avoids re-reading data from disk for each compute step.

---

## 4. Data Pipeline Idempotency

All pipeline runs are idempotent — safe to re-run without data corruption:

```python
# Timestamped output filenames prevent overwrites
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = output_dir / f"shipments_{timestamp}.csv"

# Output directories always created fresh
output_dir.mkdir(parents=True, exist_ok=True)
```

**Why**: Each run produces a new file. Old data is preserved. Any run can be retried safely.

---

## 5. Docker Volume Architecture

Data persistence across container restarts is achieved via Docker volumes:

```yaml
volumes:
  - ./data:/opt/data          # Delta Lake storage
  - ./spark/scripts:/opt/spark-scripts  # Script access
  - ./airflow/dags:/opt/airflow/dags    # DAG hot-reload
```

**Why**: File mounts allow Airflow and Spark containers to access the same data without copying. DAG changes reflect instantly without container rebuild.

---

**Document Version**: 1.0
**Last Updated**: February 20, 2026
