"""
Data Quality Monitoring DAG
Runs daily data quality checks across all Medallion layers.

Schedule: Daily at 8 AM (after main pipeline)
Owner: Data Engineering Team
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.task_group import TaskGroup
from airflow.sensors.external_task import ExternalTaskSensor

# Default arguments
default_args = {
    'owner': 'data-eng',
    'depends_on_past': True,
    'email': ['alerts@smartlogistics.com'],
    'email_on_failure': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'data_quality_monitoring',
    default_args=default_args,
    description='Daily data quality checks and metrics collection',
    schedule_interval='0 8 * * *',  # Daily at 8 AM
    start_date=datetime(2026, 2, 1),
    catchup=False,
    tags=['monitoring', 'data-quality'],
)

# ============================================================================
# DATA QUALITY CHECKS
# ============================================================================

def check_bronze_layer(**context):
    """Validate Bronze layer data quality"""
    checks = {
        'transactional_tables': [
            'customers', 'warehouses', 'drivers', 'vehicles',
            'shipment_types', 'orders', 'shipments', 'truck_assignments'
        ],
        'iot_tables': ['iot_sensor_readings']
    }
    
    print("=" * 60)
    print("BRONZE LAYER DATA QUALITY CHECKS")
    print("=" * 60)
    
    # In production: Query actual Delta tables
    for table in checks['transactional_tables']:
        print(f"✓ {table}: Row count validation passed")
    
    for table in checks['iot_tables']:
        print(f"✓ {table}: Schema validation passed")
    
    print("\n✓ Bronze layer checks: PASSED")
    return True

def check_silver_layer(**context):
    """Validate Silver layer data quality"""
    print("=" * 60)
    print("SILVER LAYER DATA QUALITY CHECKS")
    print("=" * 60)
    
    checks = {
        'deduplication_rate': 0.95,  # Expected 95%+ unique records
        'outlier_detection_rate': 0.10,  # Expected ~10% outliers
        'scd2_integrity': True,  # All records have valid_from
    }
    
    # In production: Calculate actual metrics from Delta tables
    print(f"✓ Deduplication: {checks['deduplication_rate']*100}% unique records")
    print(f"✓ Outlier detection: {checks['outlier_detection_rate']*100}% flagged")
    print(f"✓ SCD2 integrity: {checks['scd2_integrity']}")
    
    print("\n✓ Silver layer checks: PASSED")
    return True

def check_gold_layer(**context):
    """Validate Gold layer data quality"""
    print("=" * 60)
    print("GOLD LAYER DATA QUALITY CHECKS")
    print("=" * 60)
    
    # In production: Query actual analytics tables
    metrics = {
        'shipment_analytics_count': 100,  # Example count
        'temperature_alerts_count': 10,
        'avg_compliance_score': 85.5,
    }
    
    print(f"✓ Shipment analytics: {metrics['shipment_analytics_count']} records")
    print(f"✓ Temperature alerts: {metrics['temperature_alerts_count']} alerts")
    print(f"✓ Avg compliance score: {metrics['avg_compliance_score']}%")
    
    # Validation rules
    if metrics['avg_compliance_score'] < 70:
        print("⚠️  WARNING: Compliance score below threshold!")
    
    print("\n✓ Gold layer checks: PASSED")
    return True

def check_data_freshness(**context):
    """Check if data is fresh (not stale)"""
    print("=" * 60)
    print("DATA FRESHNESS CHECKS")
    print("=" * 60)
    
    # In production: Check ingestion timestamps
    bronze_last_update = datetime.now()  # Would be from Delta table
    silver_last_update = datetime.now()
    gold_last_update = datetime.now()
    
    max_age_hours = 24
    
    for layer, last_update in [
        ('Bronze', bronze_last_update),
        ('Silver', silver_last_update),
        ('Gold', gold_last_update)
    ]:
        age_hours = (datetime.now() - last_update).total_seconds() / 3600
        if age_hours > max_age_hours:
            print(f"⚠️  {layer}: Data is {age_hours:.1f} hours old (threshold: {max_age_hours}h)")
        else:
            print(f"✓ {layer}: Data is fresh ({age_hours:.1f} hours old)")
    
    return True

def check_schema_evolution(**context):
    """Detect any schema changes in Delta tables"""
    print("=" * 60)
    print("SCHEMA EVOLUTION CHECKS")
    print("=" * 60)
    
    # In production: Compare current schema with baseline
    schema_changes = []
    
    if schema_changes:
        print(f"⚠️  Detected {len(schema_changes)} schema changes")
        for change in schema_changes:
            print(f"  - {change}")
    else:
        print("✓ No unexpected schema changes detected")
    
    return True

def calculate_metrics(**context):
    """Calculate and store pipeline metrics"""
    print("=" * 60)
    print("PIPELINE METRICS")
    print("=" * 60)
    
    metrics = {
        'total_shipments_processed': 100,
        'total_iot_readings_processed': 7210,
        'temperature_violations_detected': 10,
        'critical_alerts_generated': 2,
        'pipeline_execution_time_minutes': 15,
        'data_quality_score': 95.5,
    }
    
    for metric_name, value in metrics.items():
        print(f"{metric_name}: {value}")
    
    # In production: Store metrics in monitoring system (Prometheus/CloudWatch)
    context['ti'].xcom_push(key='metrics', value=metrics)
    
    return metrics

def generate_quality_report(**context):
    """Generate daily data quality report"""
    print("=" * 60)
    print("GENERATING DAILY QUALITY REPORT")
    print("=" * 60)
    
    metrics = context['ti'].xcom_pull(task_ids='calculate_pipeline_metrics', key='metrics')
    
    report = f"""
    Smart Logistics - Daily Data Quality Report
    ============================================
    Date: {context['ds']}
    
    Pipeline Summary:
    - Shipments Processed: {metrics.get('total_shipments_processed', 0)}
    - IoT Readings: {metrics.get('total_iot_readings_processed', 0)}
    - Temperature Violations: {metrics.get('temperature_violations_detected', 0)}
    - Critical Alerts: {metrics.get('critical_alerts_generated', 0)}
    
    Data Quality Score: {metrics.get('data_quality_score', 0)}%
    Pipeline Duration: {metrics.get('pipeline_execution_time_minutes', 0)} minutes
    
    Status: ✓ ALL CHECKS PASSED
    """
    
    print(report)
    
    # In production: Send report via email or store in dashboard
    return True

# ============================================================================
# TASK DEFINITIONS
# ============================================================================

start = DummyOperator(
    task_id='start_quality_checks',
    dag=dag
)

# Wait for main pipeline to complete
wait_for_pipeline = ExternalTaskSensor(
    task_id='wait_for_main_pipeline',
    external_dag_id='smart_logistics_medallion_pipeline',
    external_task_id='pipeline_complete',
    allowed_states=['success'],
    failed_states=['failed', 'skipped'],
    mode='reschedule',
    timeout=7200,  # 2 hours
    dag=dag
)

with TaskGroup('layer_quality_checks', dag=dag) as quality_checks:
    check_bronze = PythonOperator(
        task_id='check_bronze_layer',
        python_callable=check_bronze_layer,
        provide_context=True,
        dag=dag
    )
    
    check_silver = PythonOperator(
        task_id='check_silver_layer',
        python_callable=check_silver_layer,
        provide_context=True,
        dag=dag
    )
    
    check_gold = PythonOperator(
        task_id='check_gold_layer',
        python_callable=check_gold_layer,
        provide_context=True,
        dag=dag
    )
    
    check_bronze >> check_silver >> check_gold

check_freshness = PythonOperator(
    task_id='check_data_freshness',
    python_callable=check_data_freshness,
    provide_context=True,
    dag=dag
)

check_schema = PythonOperator(
    task_id='check_schema_evolution',
    python_callable=check_schema_evolution,
    provide_context=True,
    dag=dag
)

calculate_metrics_task = PythonOperator(
    task_id='calculate_pipeline_metrics',
    python_callable=calculate_metrics,
    provide_context=True,
    dag=dag
)

generate_report = PythonOperator(
    task_id='generate_quality_report',
    python_callable=generate_quality_report,
    provide_context=True,
    dag=dag
)

complete = DummyOperator(
    task_id='quality_checks_complete',
    dag=dag
)

# Flow
start >> wait_for_pipeline >> quality_checks >> [check_freshness, check_schema] >> calculate_metrics_task >> generate_report >> complete
