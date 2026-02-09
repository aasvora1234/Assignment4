# Airflow Pipeline Troubleshooting Guide

## 🔍 How to Check What's Failing

Since you mentioned the pipeline is failing in Airflow, here's how to find the exact error:

### **Step 1: Identify the Failed Task**

In the Airflow UI (http://localhost:8090):

1. Click on the DAG name: `medallion_airflow_pipeline`
2. Look at the **Graph View**
3. Find which task box is **RED** ❌
   - `bronze_layer`?
   - `silver_layer`?
   - `gold_layer`?

### **Step 2: View the Error Log**

1. **Click on the RED task box**
2. Click the **"Log"** button at the top
3. **Scroll all the way to the bottom** of the log
4. Look for lines with:
   - `ERROR:`
   - `Exception:`
   - `Traceback:`
   - `failed`

### **Step 3: Copy the Error**

Copy the last 20-30 lines of the log (the error message) and share it with me.

---

## 🔧 Common Issues & Quick Fixes

### **Issue 1: ModuleNotFoundError: No module named 'pandas'**

**Solution**: Rebuild Airflow with custom image
```powershell
.\rebuild-airflow.ps1
```

### **Issue 2: Permission denied / Cannot write to /opt/data**

**Cause**: Airflow container doesn't have write access to shared volumes

**Solution**: Fix permissions
```powershell
docker exec -u root assignment4-airflow-scheduler-1 chmod -R 777 /opt/data
```

### **Issue 3: No such file or directory**

**Cause**: Bronze/Silver files don't exist yet

**Solution**: Generate sample data first
```powershell
docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/generate_sample_data.py
```

### **Issue 4: Database connection refused**

**Cause**: PostgreSQL not accessible from Airflow

**Solution**: Check if postgres container is running
```powershell
docker ps | Select-String postgres
```

---

## 🎯 Quick Test

Run this command to test if bronze layer works from Airflow:

```powershell
docker exec assignment4-airflow-scheduler-1 airflow tasks test medallion_airflow_pipeline bronze_layer 2026-02-09
```

**Expected**: Should see "✓ Bronze layer complete"  
**If fails**: Will show the exact error

---

## 📊 Alternative: Use Manual Execution

If Airflow continues to have issues, you can use the proven working approach:

```powershell
.\run-pipeline.ps1
```

This runs the exact same code but outside of Airflow, and we know it works!

---

## ❓ What To Share With Me

To help you fix the issue, please share:

1. **Which task failed?** (bronze/silver/gold)
2. **The error message** (last 20 lines of the log)
3. **Screenshot** (optional but helpful)

Then I can provide the exact fix!
