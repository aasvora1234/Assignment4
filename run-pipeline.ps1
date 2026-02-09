Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Smart Logistics Lakehouse - Pipeline Execution" -ForegroundColor Cyan
Write-Host "   Medallion Architecture: Bronze → Silver → Gold" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`n[1/5] Generating sample data..." -ForegroundColor Yellow
Write-Host "     (100 shipments + 7,210 IoT readings)`n" -ForegroundColor Gray

docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/generate_sample_data.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Data generation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/5] Running Bronze layer (Raw Ingestion)..." -ForegroundColor Yellow
Write-Host "     (Ingesting from PostgreSQL + IoT JSON files)`n" -ForegroundColor Gray

docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/bronze_simple.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Bronze layer failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/5] Running Silver layer (Transformation)..." -ForegroundColor Yellow
Write-Host "     (SCD Type 2 + Outlier Detection)`n" -ForegroundColor Gray

docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/silver_simple.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Silver layer failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[4/5] Running Gold layer (Analytics)..." -ForegroundColor Yellow
Write-Host "     (Business Insights + Temperature Alerts)`n" -ForegroundColor Gray

docker exec assignment4-spark-master-1 python3 /opt/spark-scripts/gold_minimal.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Gold layer failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[5/5] Verifying results..." -ForegroundColor Yellow

$verification = docker exec assignment4-spark-master-1 python3 -c "from pathlib import Path; bronze = len(list(Path('/opt/data/delta-lake/bronze').glob('*/*.csv'))); silver = len(list(Path('/opt/data/delta-lake/silver').glob('*/*.csv'))); gold = len(list(Path('/opt/data/delta-lake/gold').glob('*/*.csv'))); print(f'Bronze: {bronze}|Silver: {silver}|Gold: {gold}')"

$parts = $verification -split '\|'

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "   ✓ PIPELINE COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

Write-Host "`nData Files Created:" -ForegroundColor Cyan
Write-Host "  • Bronze Layer: $($parts[0])" -ForegroundColor White
Write-Host "  • Silver Layer: $($parts[1])" -ForegroundColor White
Write-Host "  • Gold Layer:   $($parts[2])" -ForegroundColor White

Write-Host "`nResults Location:" -ForegroundColor Cyan
Write-Host "  ./data/delta-lake/bronze/" -ForegroundColor White
Write-Host "  ./data/delta-lake/silver/" -ForegroundColor White
Write-Host "  ./data/delta-lake/gold/" -ForegroundColor White

Write-Host "`n✓ You can now analyze the data in the Gold layer!" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan
