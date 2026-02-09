"""
Working Medallion Pipeline - Airflow DAG
Uses simplified Python scripts with pandas (no PySpark dependency issues)

This DAG orchestrates the Bronze → Silver → Gold pipeline
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
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

def run_script(script_path, task_name):
    """Execute a Python script"""
    print(f"{'='*60}")
    print(f"Running {task_name}")
    print(f"Script: {script_path}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            ['/usr/bin/python3', script_path],
            capture_output=True,
            text=True,
            timeout=600,
            cwd='/opt'
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print("STDERR:", result.stderr)
            raise Exception(f"{task_name} failed with code {result.returncode}")
        
        print(f"✓ {task_name} completed successfully")
        
    except Exception as e:
        print(f"✗ Error in {task_name}: {str(e)}")
        raise

# DAG definition
with DAG(
    'medallion_working_pipeline',
    default_args=default_args,
    description='Working Medallion pipeline - Bronze → Silver → Gold',
    schedule_interval=None,  # Manual trigger
    start_date=datetime(2026, 2, 1),
    catchup=False,
    tags=['production', 'working', 'medallion'],
) as dag:

    # Start marker
    start = DummyOperator(task_id='start')

    # Bronze Layer
    bronze_ingest = PythonOperator(
        task_id='bronze_ingest_all',
        python_callable=run_script,
        op_args=['/opt/spark-scripts/bronze_simple.py', 'Bronze Ingestion'],
    )

    bronze_complete = DummyOperator(task_id='bronze_complete')

    # Silver Layer
    silver_transform = PythonOperator(
        task_id='silver_transform_all',
        python_callable=run_script,
        op_args=['/opt/spark-scripts/silver_simple.py', 'Silver Transformation'],
    )

    silver_complete = DummyOperator(task_id='silver_complete')

    # Gold Layer
    gold_analytics = PythonOperator(
        task_id='gold_analytics',
        python_callable=run_script,
        op_args=['/opt/spark-scripts/gold_minimal.py', 'Gold Analytics'],
    )

    # End marker
    complete = DummyOperator(task_id='pipeline_complete')

    # Define task flow
    start >> bronze_ingest >> bronze_complete
    bronze_complete >> silver_transform >> silver_complete
    silver_complete >> gold_analytics >> complete
