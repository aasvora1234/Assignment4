# 🚀 Complete Guide: Running Your Smart Logistics Lakehouse

This guide will walk you through every step to check, run, and monitor your data pipeline.

---

## ✅ **Step 1: Verify All Services Are Running**

First, let's make sure Docker containers are up and running.

### **1.1 Check Container Status**

Open your PowerShell terminal and run:

```powershell
docker ps
```

You should see **5 running containers**:
- `assignment4-postgres-1`
- `assignment4-airflow-webserver-1`
- `assignment4-airflow-scheduler-1`
- `assignment4-spark-master-1`
- `assignment4-spark-worker-1`

### **1.2 If Containers Are NOT Running**

If you don't see all containers, start them:

```powershell
cd "c:\Users\aasvo\Downloads\Aas Docs (1)-20240809T065604Z-001\Aas Docs (1)\AI Native\Assignment 4"
docker-compose up -d
```

Wait 2-3 minutes for all services to initialize.

---

## 🌐 **Step 2: Access Airflow Web UI**

### **2.1 Open Your Browser**

Go to: **http://localhost:8080**

### **2.2 Login to Airflow**

- **Username**: `admin`
- **Password**: `admin`

(These are set in your `.env` file)

### **2.3 What You Should See**

You'll see the Airflow dashboard with a list of DAGs (Data Pipelines).

---

## 📋 **Step 3: Find Your DAGs**

On the main Airflow page, you should see **3 DAGs**:

1. **`smart_logistics_medallion_pipeline`** (Main daily pipeline)
2. **`iot_incremental_pipeline`** (Hourly IoT processing)
3. **`data_quality_monitoring`** (Quality checks)

### **3.1 Enable the DAGs**

By default, DAGs are **paused** (turned off). To enable them:

1. Look for the **toggle switch** (on/off button) on the left of each DAG name
2. Click it to turn it **ON** (should turn blue/green)
3. Do this for all 3 DAGs

---

## ▶️ **Step 4: Run Your First Pipeline (Manual Trigger)**

Let's run the main pipeline manually to test it.

### **4.1 Trigger the Pipeline**

1. Find **`smart_logistics_medallion_pipeline`** in the list
2. Click the **"Play" button** (▶️) on the right side
3. Select **"Trigger DAG"** from the dropdown

### **4.2 What Happens Next**

- The DAG will start running immediately
- You'll see the status change to **"running"** (green spinning icon)

---

## 👀 **Step 5: Monitor Pipeline Execution**

### **5.1 View DAG Details**

1. Click on the DAG name: **`smart_logistics_medallion_pipeline`**
2. You'll see a **Graph View** showing all tasks

### **5.2 Understanding the Graph**

- **Green boxes** = Task completed successfully ✅
- **Orange/Yellow boxes** = Task is running 🔄
- **Red boxes** = Task failed ❌
- **Grey boxes** = Task hasn't started yet ⏳

### **5.3 Check Task Status**

The pipeline will run tasks in this order:

```
1. Bronze Layer (Ingest Data)
   └─ ingest_postgres_to_bronze
   └─ ingest_iot_to_bronze

2. Silver Layer (Clean Data)
   └─ transform_transactional_to_silver
   └─ transform_iot_to_silver

3. Gold Layer (Analytics)
   └─ generate_shipment_analytics

4. Validation
   └─ data_quality_validation
   └─ send_success_notification
```

---

## 📊 **Step 6: View Task Logs (Detailed Output)**

If you want to see what's happening inside a task:

### **6.1 Open Task Logs**

1. Click on any task box (e.g., `ingest_postgres_to_bronze`)
2. Click **"Log"** button at the top
3. You'll see detailed execution logs

### **6.2 What to Look For in Logs**

- **Success messages**: `✓ Successfully wrote X records`
- **Error messages**: `✗ Error: ...`
- **Counts**: Number of records processed

---

## 🛠️ **Step 7: Troubleshooting Common Issues**

### **Issue 1: DAG Not Showing Up**

**Solution**: Airflow scans for DAGs every 30 seconds. Wait a minute and refresh the page.

### **Issue 2: Task Fails with "ModuleNotFoundError"**

**Solution**: Install Python packages in Spark container:

```powershell
docker exec assignment4-spark-master-1 pip install delta-spark pyspark faker psycopg2-binary pandas
```

### **Issue 3: Can't Access Airflow UI (localhost:8080)**

**Solution**: Check if Airflow is running:

```powershell
docker logs assignment4-airflow-webserver-1
```

If you see errors, restart the container:

```powershell
docker-compose restart airflow-webserver
```

### **Issue 4: Task Stuck in "Running" State**

**Solution**: Click the task → Click **"Mark Success"** or **"Mark Failed"** to unstuck it.

---

## 📈 **Step 8: View Your Data (Delta Lake Tables)**

After the pipeline runs successfully, your data will be in Delta Lake format.

### **8.1 Check Delta Lake Directory**

```powershell
ls ./data/delta-lake/bronze
ls ./data/delta-lake/silver
ls ./data/delta-lake/gold
```

You should see folders for each table.

### **8.2 View Table Contents (Advanced)**

To query the data, you'll need to run Python/PySpark scripts. Here's a quick example:

```python
# Connect to Delta table
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("QueryDelta") \
    .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
    .getOrCreate()

# Read table
df = spark.read.format("delta").load("./data/delta-lake/gold/shipment_analytics")
df.show(10)
```

---

## 🔄 **Step 9: Schedule Automatic Runs**

Your DAGs are already configured to run automatically:

- **Main Pipeline**: Daily at 2:00 AM
- **IoT Incremental**: Every hour
- **Quality Checks**: Daily at 8:00 AM

**No action needed!** Just keep Docker running.

---

## 📧 **Step 10: Email Notifications (Optional)**

To receive email alerts on failures:

1. Edit `.env` file
2. Update `AIRFLOW__SMTP__SMTP_HOST` settings
3. Restart Airflow:

```powershell
docker-compose restart airflow-webserver airflow-scheduler
```

---

## 🎯 **Quick Reference Commands**

### **Start Everything**
```powershell
docker-compose up -d
```

### **Stop Everything**
```powershell
docker-compose down
```

### **View All Container Logs**
```powershell
docker-compose logs -f
```

### **Check Airflow Scheduler Logs**
```powershell
docker logs -f assignment4-airflow-scheduler-1
```

### **Manually Run Data Generation**
```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/generate_sample_data.py
```

---

## 🎓 **Understanding Your Pipeline**

### **Bronze Layer** (Raw Data)
- **Input**: PostgreSQL tables + IoT JSON files
- **Output**: Delta Lake tables (raw, unchanged)
- **Purpose**: Historical record of all data

### **Silver Layer** (Cleaned Data)
- **Input**: Bronze tables
- **Output**: Deduplicated, validated data
- **Purpose**: Analytics-ready data
- **Special**: SCD Type 2 for shipment tracking

### **Gold Layer** (Business Insights)
- **Input**: Silver tables
- **Output**: Aggregated analytics + alerts
- **Purpose**: Business dashboards and reporting

---

## 🆘 **Getting Help**

If something doesn't work:

1. **Check container logs** first:
   ```powershell
   docker logs assignment4-airflow-scheduler-1
   ```

2. **Restart specific service**:
   ```powershell
   docker-compose restart airflow-scheduler
   ```

3. **Full system restart**:
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

---

## ✅ **Success Checklist**

- [ ] All 5 Docker containers running
- [ ] Airflow UI accessible at http://localhost:8080
- [ ] 3 DAGs visible in Airflow
- [ ] DAGs enabled (toggle ON)
- [ ] Main pipeline executed successfully
- [ ] Delta Lake folders created in `./data/delta-lake/`
- [ ] No red (failed) tasks in Graph View

---

**You're all set! 🎉**

Your Smart Logistics Lakehouse is now running. The pipeline will automatically process data daily, detect temperature violations, and generate alerts for your operations team.
