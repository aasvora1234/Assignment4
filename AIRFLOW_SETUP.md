# Setting Up Airflow with Custom Dependencies

## 📋 What We Changed

1. ✅ Created `airflow/requirements.txt` - Python package dependencies
2. ✅ Created `airflow/Dockerfile` - Custom Airflow image
3. ✅ Updated `docker-compose.yml` - Build custom image instead of official
4. ✅ Created `medallion_airflow_pipeline.py` - Working DAG

---

## 🚀 Step-by-Step Rebuild Process

### **Step 1: Stop Current Containers**

```powershell
docker-compose down
```

This will:
- Stop all running containers
- Remove the containers
- Keep your data volumes intact

---

### **Step 2: Build Custom Airflow Image **

```powershell
docker-compose build airflow-webserver airflow-scheduler
```

This will:
- Build the custom Airflow image from our Dockerfile
- Install pandas, psycopg2-binary, and numpy
- Tag it as `custom-airflow:2.8.0`

**Expected time: 3-5 minutes**

---

### **Step 3: Start All Services**

```powershell
docker-compose up -d
```

This will:
- Start all containers with the new custom image
- Initialize Airflow database (if needed)
- Start webserver and scheduler

**Expected time: 1-2 minutes**

---

### **Step 4: Wait for Airflow to Initialize**

```powershell
# Wait 60 seconds for Airflow to fully start
timeout /t 60
```

Or manually wait ~1 minute before accessing the UI.

---

### **Step 5: Verify Packages Are Installed**

```powershell
docker exec assignment4-airflow-scheduler-1 python -c "import pandas, psycopg2, numpy; print('✓ All packages installed successfully!')"
```

**Expected output:**
```
✓ All packages installed successfully!
```

---

### **Step 6: Access Airflow UI**

1. Open browser: http://localhost:8090
2. Login: `admin` / `admin`
3. Look for the DAG: **`medallion_airflow_pipeline`**

---

### **Step 7: Run the Pipeline in Airflow**

1. **Enable the DAG** - Toggle switch on the left
2. **Trigger it** - Click the Play button ▶️
3. **Monitor** - Click DAG name → Graph View
4. **Check logs** - Click on any task → Log

---

## 📊 What to Expect

### **DAG Structure:**
```
start → bronze_layer → silver_layer → gold_layer → complete
```

### **Execution Time:**
- Bronze: ~30 seconds
- Silver: ~30 seconds
- Gold: ~10 seconds
- **Total: ~2-3 minutes**

### **Success Indicators:**
- All tasks turn **green**
- Logs show "✓ layer complete" messages
- Files created in `/opt/data/delta-lake/`

---

## 🐛 Troubleshooting

### **Issue: Build fails**
```powershell
# Clean everything and rebuild
docker-compose down -v
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

### **Issue: DAG doesn't appear**
- Wait 30 seconds and refresh browser
- Check DAG file syntax:
  ```powershell
  docker exec assignment4-airflow-scheduler-1 cat /opt/airflow/dags/medallion_airflow_pipeline.py
  ```

### **Issue: Task fails**
- Click on failed task → Log
- Look for error at bottom of log
- Most common: Database connection (check `postgres` container is running)

---

## ✅ Quick Rebuild Script

Save this as `rebuild-airflow.ps1`:

```powershell
Write-Host "Rebuilding Airflow with custom dependencies..." -ForegroundColor Cyan

Write-Host "`n[1/5] Stopping containers..." -ForegroundColor Yellow
docker-compose down

Write-Host "`n[2/5] Building custom Airflow image..." -ForegroundColor Yellow
docker-compose build airflow-webserver airflow-scheduler

Write-Host "`n[3/5] Starting all services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "`n[4/5] Waiting for Airflow to initialize (60s)..." -ForegroundColor Yellow
timeout /t 60 /nobreak > $null

Write-Host "`n[5/5] Verifying installation..." -ForegroundColor Yellow
docker exec assignment4-airflow-scheduler-1 python -c "import pandas, psycopg2, numpy; print('✓ All packages installed!')"

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "✓ AIRFLOW REBUILT SUCCESSFULLY!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "`nAccess Airflow UI: http://localhost:8090" -ForegroundColor Cyan
Write-Host "Login: admin / admin`n" -ForegroundColor Cyan
```

Then run:
```powershell
.\rebuild-airflow.ps1
```

---

## 🎯 Summary

**What's Different Now:**
- ❌ Before: Airflow used official image (no pandas)
- ✅ Now: Custom image with pandas, psycopg2, numpy
- ✅ Result: DAGs can execute our Python scripts!

**Ready to rebuild?** Run the commands in Step 1-5! 🚀
