Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Rebuilding Airflow with Custom Dependencies" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`n[1/5] Stopping containers..." -ForegroundColor Yellow
docker-compose down

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to stop containers" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/5] Building custom Airflow image (this may take 3-5 minutes)..." -ForegroundColor Yellow
Write-Host "     Installing: pandas, psycopg2-binary, numpy`n" -ForegroundColor Gray
docker-compose build airflow-webserver airflow-scheduler

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/5] Starting all services..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host "`n[4/5] Waiting for Airflow to initialize (60 seconds)..." -ForegroundColor Yellow
timeout /t 60 /nobreak > $null

Write-Host "`n[5/5] Verifying package installation..." -ForegroundColor Yellow
$verification = docker exec assignment4-airflow-scheduler-1 python -c "import pandas, psycopg2, numpy; print('SUCCESS')" 2>&1

if ($verification -like "*SUCCESS*") {
    Write-Host "`n============================================================" -ForegroundColor Green
    Write-Host "   ✓ AIRFLOW REBUILT SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    
    Write-Host "`nPackages Installed:" -ForegroundColor Cyan
    Write-Host "  ✓ pandas" -ForegroundColor White
    Write-Host "  ✓ psycopg2-binary" -ForegroundColor White
    Write-Host "  ✓ numpy" -ForegroundColor White
    
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    Write-Host "  1. Open browser: http://localhost:8090" -ForegroundColor White
    Write-Host "  2. Login: admin / admin" -ForegroundColor White
    Write-Host "  3. Find DAG: medallion_airflow_pipeline" -ForegroundColor White
    Write-Host "  4. Enable toggle and trigger it!" -ForegroundColor White
    Write-Host "`n============================================================`n" -ForegroundColor Cyan
} else {
    Write-Host "`n✗ Package verification failed" -ForegroundColor Red
    Write-Host "Error: $verification" -ForegroundColor Red
    exit 1
}
