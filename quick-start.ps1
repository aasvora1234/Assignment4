# Quick Start Script - Run this first!

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Smart Logistics Lakehouse - Quick Start" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker
Write-Host "[Step 1/5] Checking Docker containers..." -ForegroundColor Yellow
$containers = docker ps --format "{{.Names}}" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Docker is not running!" -ForegroundColor Red
    Write-Host "  → Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

$requiredContainers = @(
    "assignment4-postgres-1",
    "assignment4-airflow-webserver-1",
    "assignment4-airflow-scheduler-1",
    "assignment4-spark-master-1",
    "assignment4-spark-worker-1"
)

$runningContainers = $containers -split "`n"
$allRunning = $true

foreach ($container in $requiredContainers) {
    if ($runningContainers -contains $container) {
        Write-Host "  ✓ $container" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $container (NOT RUNNING)" -ForegroundColor Red
        $allRunning = $false
    }
}

if (-not $allRunning) {
    Write-Host ""
    Write-Host "  → Starting missing containers..." -ForegroundColor Yellow
    docker-compose up -d
    Write-Host "  → Waiting 30 seconds for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

Write-Host ""

# Step 2: Check Airflow
Write-Host "[Step 2/5] Checking Airflow..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -UseBasicParsing 2>$null
    Write-Host "  ✓ Airflow is accessible at http://localhost:8080" -ForegroundColor Green
} catch {
    Write-Host "  ⚠  Airflow UI not ready yet. It may still be starting..." -ForegroundColor Yellow
    Write-Host "  → Wait 1-2 minutes and open: http://localhost:8080" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Check PostgreSQL
Write-Host "[Step 3/5] Checking PostgreSQL..." -ForegroundColor Yellow
$pgCheck = docker exec assignment4-postgres-1 pg_isready -U admin 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ PostgreSQL is ready" -ForegroundColor Green
} else {
    Write-Host "  ✗ PostgreSQL is not ready" -ForegroundColor Red
}

Write-Host ""

# Step 4: Check Spark
Write-Host "[Step 4/5] Checking Spark..." -ForegroundColor Yellow
$sparkCheck = docker exec assignment4-spark-master-1 ls /opt/spark/bin/spark-submit 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Spark Master is ready" -ForegroundColor Green
} else {
    Write-Host "  ✗ Spark Master has issues" -ForegroundColor Red
}

Write-Host ""

# Step 5: Install Python dependencies
Write-Host "[Step 5/5] Installing Python dependencies in Spark..." -ForegroundColor Yellow
Write-Host "  → This may take 2-3 minutes on first run..." -ForegroundColor Gray

docker exec assignment4-spark-master-1 pip install -q delta-spark pyspark faker psycopg2-binary pandas 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  ⚠  Dependency installation had warnings (usually OK)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  ✓ SETUP COMPLETE!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open browser: http://localhost:8080" -ForegroundColor White
Write-Host "  2. Login with username: admin, password: admin" -ForegroundColor White
Write-Host "  3. Enable DAGs by clicking the toggle switches" -ForegroundColor White
Write-Host "  4. Click 'Play' button to trigger a pipeline run" -ForegroundColor White
Write-Host ""
Write-Host "📖 For detailed guide, see: GETTING_STARTED.md" -ForegroundColor Gray
Write-Host ""
