"""
SIMPLIFIED Medallion Architecture Pipeline - Airflow DAG
Uses PythonOperator to execute scripts directly (works in Docker environment)

Schedule: Daily at 2 AM
Owner: Data Engineering Team
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
import subprocess
import sys

# Default arguments
default_args = {
    'owner': 'data-eng',
    'depends_on_past': False,
    'email': ['alerts@smartlogistics.com'],
    'email_on_failure': False,  # Disabled for testing
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(hours=1),
}

# DAG definition
dag = DAG(
    'medallion_simplified',
    default_args=default_args,
    description='Simplified Medallion pipeline that works in Docker',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2026, 2, 1),
    catchup=False,
    max_active_runs=1,
    tags=['production', 'medallion', 'simplified'],
)

# ============================================================================
# PYTHON FUNCTIONS TO RUN SCRIPTS
# ============================================================================

def run_python_script(script_path):
    """Execute a Python script using subprocess"""
    print(f"Executing: {script_path}")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.returncode != 0:
            print("STDERR:")
            print(result.stderr)
            raise Exception(f"Script failed with return code: {result.returncode}")
        
        print(f"✓ Script completed successfully")
        return result.stdout
        
    except subprocess.TimeoutExpired:
        raise Exception(f"Script timed out after 30 minutes")
    except Exception as e:
        raise Exception(f"Script execution failed: {str(e)}")

def ingest_transactional(**context):
    """Bronze: Ingest PostgreSQL data"""
    return run_python_script("/opt/spark-scripts/bronze_ingest_transactional.py")

def ingest_iot(**context):
    """Bronze: Ingest IoT JSON data"""
    return run_python_script("/opt/spark-scripts/bronze_ingest_iot.py")

def transform_transactional(**context):
    """Silver: Transform transactional data with SCD2"""
    return run_python_script("/opt/spark-scripts/silver_transform_transactional.py")

def transform_iot(**context):
    """Silver: Clean and validate IoT data"""
    return run_python_script("/opt/spark-scripts/silver_transform_iot.py")

def generate_analytics(**context):
    """Gold: Generate analytics and alerts"""
    return run_python_script("/opt/spark-scripts/gold_analytics.py")

# ============================================================================
# TASK DEFINITIONS
# ============================================================================

start = DummyOperator(
    task_id='pipeline_start',
    dag=dag
)

# Bronze Layer
bronze_transactional = PythonOperator(
    task_id='bronze_ingest_transactional',
    python_callable=ingest_transactional,
    provide_context=True,
    dag=dag
)

bronze_iot = PythonOperator(
    task_id='bronze_ingest_iot',
    python_callable=ingest_iot,
    provide_context=True,
    dag=dag
)

bronze_complete = DummyOperator(
    task_id='bronze_complete',
    dag=dag
)

# Silver Layer
silver_transactional = PythonOperator(
    task_id='silver_transform_transactional',
    python_callable=transform_transactional,
    provide_context=True,
    dag=dag
)

silver_iot = PythonOperator(
    task_id='silver_transform_iot',
    python_callable=transform_iot,
    provide_context=True,
    dag=dag
)

silver_complete = DummyOperator(
    task_id='silver_complete',
    dag=dag
)

# Gold Layer
gold_analytics = PythonOperator(
    task_id='gold_generate_analytics',
    python_callable=generate_analytics,
    provide_context=True,
    dag=dag
)

complete = DummyOperator(
    task_id='pipeline_complete',
    dag=dag
)

# ============================================================================
# DAG FLOW
# ============================================================================

# Bronze: Run in parallel
start >> [bronze_transactional, bronze_iot] >> bronze_complete

# Silver: Run in parallel
bronze_complete >> [silver_transactional, silver_iot] >> silver_complete

# Gold: Generate analytics
silver_complete >> gold_analytics >> complete
