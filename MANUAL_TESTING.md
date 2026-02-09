# Manual Testing Guide - Run Pipeline Without Airflow

Since we're having issues with Airflow package installations, let's test the pipeline **manually first** to verify everything works.

## ✅ Step 1: Generate Sample Data

First, let's create the sample data in PostgreSQL and IoT JSON files:

```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/generate_sample_data.py
```

**Expected output:**
```
=== Smart Logistics - Sample Data Generator ===
✓ Connected to PostgreSQL
✓ Initialized schema
✓ Generated 100 customers
✓ Generated 100 shipments  
✓ Generated ~7,210 IoT sensor readings
✓ Sample data generation complete!
```

---

## ✅ Step 2: Run Bronze Layer (Ingest Raw Data)

### Ingest PostgreSQL Tables:
```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/bronze_ingest_transactional.py
```

### Ingest IoT JSON Files:
```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/bronze_ingest_iot.py
```

**Expected output:**
```
Successfully wrote X records to Bronze layer
```

---

## ✅ Step 3: Run Silver Layer (Clean & Transform)

### Transform Transactional Data (with SCD Type 2):
```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/silver_transform_transactional.py
```

### Clean IoT Sensor Data:
```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/silver_transform_iot.py
```

**Expected output:**
```
Detected X outliers
Deduplication rate: XX%
✓ Wrote X records to Silver
```

---

## ✅ Step 4: Run Gold Layer (Analytics & Alerts)

### Generate Analytics & Temperature Alerts:
```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/gold_analytics.py
```

**Expected output:**
```
Violations detected: X/Y shipments
Generated X alerts
✓ Successfully wrote to Gold layer
```

---

## 📊 Step 5: Verify Results

### Check Delta Lake Structure:
```powershell
ls ./data/delta-lake/bronze
ls ./data/delta-lake/silver  
ls ./data/delta-lake/gold
```

You should see folders for each table.

---

## 🎯 Why Manual Testing First?

1. ✅ **Verify scripts work** independently
2. ✅ **See DetailedOutput logs and errors clearly
3. ✅ **Understand the pipeline** flow
4. ✅ **Debug issues** easier
5. ✅ **Once working**, we can fix Airflow orchestration

---

## 🔄 Full Pipeline (All Steps in Order):

```powershell
# Step 1: Generate data
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/generate_sample_data.py

# Step 2: Bronze layer
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/bronze_ingest_transactional.py
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/bronze_ingest_iot.py

# Step 3: Silver layer
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/silver_transform_transactional.py
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/silver_transform_iot.py

# Step 4: Gold layer
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/gold_analytics.py
```

---

## 🎓 What You'll Learn:

- How data flows through the Medallion Architecture
- How SCD Type 2 tracks historical changes
- How outlier detection identifies bad sensor readings
- How analytics combine shipments with IoT data
- How alerts are generated for temperature violations

**Start with Step 1 and run each command. Share the output if you encounter any errors!** 🚀
