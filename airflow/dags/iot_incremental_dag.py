"""
IoT Sensor Incremental Pipeline - Airflow DAG
Processes new IoT sensor data hourly for near-real-time monitoring.

Schedule: Every hour
Owner: Data Engineering Team
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.task_group import TaskGroup

# Default arguments
default_args = {
    'owner': 'data-eng',
    'depends_on_past': False,
    'email': ['alerts@smartlogistics.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=30),
}

# DAG definition
dag = DAG(
    'iot_incremental_pipeline',
    default_args=default_args,
    description='Hourly IoT sensor data processing for real-time monitoring',
    schedule_interval='0 * * * *',  # Every hour
    start_date=datetime(2026, 2, 1),
    catchup=False,
    max_active_runs=1,
    tags=['production', 'iot', 'real-time'],
)

# Spark submit command for incremental processing
SPARK_SUBMIT_CMD = """
docker exec assignment4-spark-master-1 /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --packages io.delta:delta-core_2.12:2.4.0 \
    --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
    --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
    --driver-memory 1g \
    --executor-memory 1g \
    {script_path}
"""

def check_critical_alerts(**context):
    """
    Check for critical temperature alerts and send immediate notifications
    In production: Query Gold layer for new critical alerts
    """
    print("Checking for critical temperature violations...")
    # Placeholder: In production, query Delta table
    critical_count = 0  # Would be actual count from database
    
    if critical_count > 0:
        print(f"⚠️  ALERT: {critical_count} critical temperature violations detected!")
        # Send to operations team via email/Slack/PagerDuty
    else:
        print("✓ No critical violations in this batch")
    
    return critical_count

# Tasks
start = DummyOperator(
    task_id='start_incremental_processing',
    dag=dag
)

ingest_new_iot = BashOperator(
    task_id='ingest_new_iot_data',
    bash_command=SPARK_SUBMIT_CMD.format(
        script_path='/opt/spark-scripts/bronze_ingest_iot.py'
    ),
    dag=dag
)

clean_iot = BashOperator(
    task_id='clean_iot_data',
    bash_command=SPARK_SUBMIT_CMD.format(
        script_path='/opt/spark-scripts/silver_transform_iot.py'
    ),
    dag=dag
)

update_analytics = BashOperator(
    task_id='update_analytics',
    bash_command=SPARK_SUBMIT_CMD.format(
        script_path='/opt/spark-scripts/gold_analytics.py'
    ),
    dag=dag
)

check_alerts = PythonOperator(
    task_id='check_critical_alerts',
    python_callable=check_critical_alerts,
    provide_context=True,
    dag=dag
)

complete = DummyOperator(
    task_id='incremental_complete',
    dag=dag
)

# Flow
start >> ingest_new_iot >> clean_iot >> update_analytics >> check_alerts >> complete
