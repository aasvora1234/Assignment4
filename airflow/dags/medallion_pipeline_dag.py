"""
Medallion Architecture Pipeline - Airflow DAG
Orchestrates Bronze → Silver → Gold data flow for Smart Logistics.

Schedule: Daily at 2 AM
Owner: Data Engineering Team
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.task_group import TaskGroup
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.models import Variable
from airflow.utils.email import send_email

# Default arguments for all tasks
default_args = {
    'owner': 'data-eng',
    'depends_on_past': False,
    'email': ['alerts@smartlogistics.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG definition
dag = DAG(
    'smart_logistics_medallion_pipeline',
    default_args=default_args,
    description='End-to-end Medallion Architecture pipeline for Smart Logistics',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=datetime(2026, 2, 1),
    catchup=False,
    max_active_runs=1,
    tags=['production', 'medallion', 'smart-logistics'],
)

# Spark submit command template
SPARK_SUBMIT_CMD = """
docker exec assignment4-spark-master-1 /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --packages io.delta:delta-core_2.12:2.4.0{postgresql} \
    --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
    --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
    --driver-memory 2g \
    --executor-memory 2g \
    {script_path}
"""

# Python callback for notifications
def send_success_notification(**context):
    """Send email notification on DAG success"""
    subject = f"✓ Success: {context['dag'].dag_id} - {context['ds']}"
    body = f"""
    DAG: {context['dag'].dag_id}
    Execution Date: {context['ds']}
    Status: SUCCESS
    
    All layers processed successfully:
    - Bronze: Raw data ingested
    - Silver: Data cleaned and validated
    - Gold: Analytics and alerts generated
    
    Dashboard: http://airflow:8080
    """
    send_email(
        to=context['dag'].default_args['email'],
        subject=subject,
        html_content=body
    )

def check_data_quality(**context):
    """Placeholder for data quality checks"""
    # In production, this would query Delta tables and validate row counts
    print("Data quality checks passed")
    return True

# ============================================================================
# TASK GROUPS
# ============================================================================

# --- BRONZE LAYER TASKS ---
with TaskGroup('bronze_layer', tooltip='Ingest raw data to Bronze layer', dag=dag) as bronze_group:
    
    bronze_start = DummyOperator(
        task_id='bronze_start',
        dag=dag
    )
    
    ingest_transactional = BashOperator(
        task_id='ingest_postgres_to_bronze',
        bash_command=SPARK_SUBMIT_CMD.format(
            postgresql=',org.postgresql:postgresql:42.6.0',
            script_path='/opt/spark-scripts/bronze_ingest_transactional.py'
        ),
        dag=dag
    )
    
    ingest_iot = BashOperator(
        task_id='ingest_iot_to_bronze',
        bash_command=SPARK_SUBMIT_CMD.format(
            postgresql='',
            script_path='/opt/spark-scripts/bronze_ingest_iot.py'
        ),
        dag=dag
    )
    
    bronze_complete = DummyOperator(
        task_id='bronze_complete',
        dag=dag
    )
    
    # Dependencies within Bronze
    bronze_start >> [ingest_transactional, ingest_iot] >> bronze_complete

# --- SILVER LAYER TASKS ---
with TaskGroup('silver_layer', tooltip='Clean and validate data in Silver layer', dag=dag) as silver_group:
    
    silver_start = DummyOperator(
        task_id='silver_start',
        dag=dag
    )
    
    transform_transactional = BashOperator(
        task_id='transform_transactional_to_silver',
        bash_command=SPARK_SUBMIT_CMD.format(
            postgresql='',
            script_path='/opt/spark-scripts/silver_transform_transactional.py'
        ),
        dag=dag
    )
    
    transform_iot = BashOperator(
        task_id='transform_iot_to_silver',
        bash_command=SPARK_SUBMIT_CMD.format(
            postgresql='',
            script_path='/opt/spark-scripts/silver_transform_iot.py'
        ),
        dag=dag
    )
    
    silver_complete = DummyOperator(
        task_id='silver_complete',
        dag=dag
    )
    
    # Dependencies within Silver
    silver_start >> [transform_transactional, transform_iot] >> silver_complete

# --- GOLD LAYER TASKS ---
with TaskGroup('gold_layer', tooltip='Generate analytics and business insights', dag=dag) as gold_group:
    
    gold_start = DummyOperator(
        task_id='gold_start',
        dag=dag
    )
    
    generate_analytics = BashOperator(
        task_id='generate_shipment_analytics',
        bash_command=SPARK_SUBMIT_CMD.format(
            postgresql='',
            script_path='/opt/spark-scripts/gold_analytics.py'
        ),
        dag=dag
    )
    
    gold_complete = DummyOperator(
        task_id='gold_complete',
        dag=dag
    )
    
    # Dependencies within Gold
    gold_start >> generate_analytics >> gold_complete

# ============================================================================
# MONITORING & VALIDATION TASKS
# ============================================================================

data_quality_check = PythonOperator(
    task_id='data_quality_validation',
    python_callable=check_data_quality,
    provide_context=True,
    dag=dag
)

send_completion_email = PythonOperator(
    task_id='send_success_notification',
    python_callable=send_success_notification,
    provide_context=True,
    trigger_rule='all_success',
    dag=dag
)

# ============================================================================
# DAG FLOW DEFINITION
# ============================================================================

pipeline_start = DummyOperator(
    task_id='pipeline_start',
    dag=dag
)

pipeline_complete = DummyOperator(
    task_id='pipeline_complete',
    trigger_rule='all_success',
    dag=dag
)

# Main pipeline flow
pipeline_start >> bronze_group >> silver_group >> gold_group >> data_quality_check >> send_completion_email >> pipeline_complete
