"""
✅ WORKING AIRFLOW DAG - Medallion Pipeline
Now works with custom Airflow image that has pandas installed!

This DAG executes: Bronze → Silver → Gold layers
Author: Data Engineering Team
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator

# Import path setup
import sys
sys.path.insert(0, '/opt/spark-scripts')

default_args = {
    'owner': 'data-eng',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

def execute_bronze():
    """Execute Bronze layer - Raw data ingestion"""
    print("="*70)
    print("BRONZE LAYER - Ingesting Raw Data")
    print("="*70)
    
    # Import dependencies
    import pandas as pd
    import psycopg2
    from pathlib import Path
    from datetime import datetime as dt
    import json
    
    # Configuration
    DB_CONFIG = {
        'host': 'postgres',
        'port': '5432',
        'database': 'postgres',
        'user': 'admin',
        'password': 'password'
    }
    
    BRONZE_PATH = Path("/opt/data/delta-lake/bronze")
    IOT_SOURCE = Path("/opt/data/iot_raw")
    
    # Ingest PostgreSQL tables
    tables = ['customers', 'warehouses', 'drivers', 'vehicles',
              'shipment_types', 'orders', 'shipments', 'truck_assignments']
    
    total = 0
    for table in tables:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            df = pd.read_sql(f"SELECT * FROM logistics.{table}", conn)
            conn.close()
            
            df['ingestion_timestamp'] = dt.now()
            df['source_system'] = 'PostgreSQL'
            df['source_table'] = table
            
            output_dir = BRONZE_PATH / table
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{table}_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(output_file, index=False)
            
            print(f"  ✓ {table}: {len(df)} records")
            total += len(df)
        except Exception as e:
            print(f"  ✗ Error with {table}: {str(e)}")
    
    # Ingest IoT data
    try:
        all_readings = []
        for json_file in IOT_SOURCE.glob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                all_readings.extend(data['sensor_readings'])
        
        df = pd.DataFrame(all_readings)
        df['ingestion_timestamp'] = dt.now()
        df['source_system'] = 'IoT_Sensors'
        
        output_dir = BRONZE_PATH / "iot_sensor_readings"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"iot_readings_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False)
        
        print(f"  ✓ IoT readings: {len(df)} records")
        total += len(df)
    except Exception as e:
        print(f"  ✗ Error with IoT data: {str(e)}")
    
    print(f"\n✓ Bronze layer complete - {total} total records ingested")

def execute_silver():
    """Execute Silver layer - Data transformation"""
    print("="*70)
    print("SILVER LAYER - Transforming Data")
    print("="*70)
    
    import pandas as pd
    import numpy as np
    from pathlib import Path
    from datetime import datetime as dt
    
    BRONZE_PATH = Path("/opt/data/delta-lake/bronze")
    SILVER_PATH = Path("/opt/data/delta-lake/silver")
    
    def get_latest_csv(directory):
        csv_files = list(Path(directory).glob("*.csv"))
        return max(csv_files, key=lambda x: x.stat().st_mtime) if csv_files else None
    
    # Process simple tables
    simple_tables = ['customers', 'warehouses', 'drivers', 'vehicles',
                     'shipment_types', 'orders', 'truck_assignments']
    
    for table in simple_tables:
        try:
            bronze_file = get_latest_csv(BRONZE_PATH / table)
            if bronze_file:
                df = pd.read_csv(bronze_file)
                df = df.drop_duplicates()
                df['silver_processed_at'] = dt.now()
                
                output_dir = SILVER_PATH / table
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"{table}_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(output_file, index=False)
                print(f"  ✓ {table}: {len(df)} records")
        except Exception as e:
            print(f"  ✗ {table}: {str(e)}")
    
    # Process shipments with SCD Type 2
    try:
        bronze_file = get_latest_csv(BRONZE_PATH / "shipments")
        df = pd.read_csv(bronze_file).drop_duplicates()
        
        df['surrogate_key'] = range(1, len(df) + 1)
        df['valid_from'] = pd.to_datetime(df['created_at'])
        df['valid_to'] = pd.NaT
        df['is_current'] = True
        df['version'] = 1
        df['silver_processed_at'] = dt.now()
        
        output_dir = SILVER_PATH / "shipments_scd2"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"shipments_scd2_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False)
        print(f"  ✓ shipments (SCD2): {len(df)} records")
    except Exception as e:
        print(f"  ✗ shipments: {str(e)}")
    
    # Process IoT with outlier detection
    try:
        bronze_file = get_latest_csv(BRONZE_PATH / "iot_sensor_readings")
        df = pd.read_csv(bronze_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Outlier detection
        df['is_out_of_range'] = (df['temperature'] < -30) | (df['temperature'] > 50)
        df['temp_mean'] = df.groupby('truck_id')['temperature'].transform('mean')
        df['temp_std'] = df.groupby('truck_id')['temperature'].transform('std')
        df['z_score'] = np.where(df['temp_std'] > 0,
                                (df['temperature'] - df['temp_mean']) / df['temp_std'], 0)
        df['is_statistical_outlier'] = np.abs(df['z_score']) > 3.0
        
        df = df.sort_values(['truck_id', 'timestamp'])
        df['prev_temperature'] = df.groupby('truck_id')['temperature'].shift(1)
        df['temp_change_rate'] = np.abs(df['temperature'] - df['prev_temperature']).fillna(0)
        df['is_rapid_change'] = df['temp_change_rate'] > 10.0
        
        df['is_outlier'] = df['is_out_of_range'] | df['is_statistical_outlier'] | df['is_rapid_change']
        df['is_valid_gps'] = (df['latitude'].between(-90, 90)) & (df['longitude'].between(-180, 180))
        df['quality_score'] = np.where(df['is_outlier'] | ~df['is_valid_gps'], 50, 100)
        df['data_quality_flag'] = np.where(df['is_outlier'], 'FLAGGED', 'CLEAN')
        df['silver_processed_at'] = dt.now()
        df['reading_date'] = df['timestamp'].dt.date
        
        output_dir = SILVER_PATH / "iot_sensor_readings_clean"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"iot_clean_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        cols = ['truck_id', 'timestamp', 'temperature', 'latitude', 'longitude',
                'is_outlier', 'is_valid_gps', 'quality_score', 'data_quality_flag',
                'z_score', 'temp_change_rate', 'silver_processed_at', 'reading_date']
        df[cols].to_csv(output_file, index=False)
        print(f"  ✓ IoT cleaned: {len(df)} records, {df['is_outlier'].sum()} outliers")
    except Exception as e:
        print(f"  ✗ IoT: {str(e)}")
    
    print("\n✓ Silver layer complete")

def execute_gold():
    """Execute Gold layer - Business analytics"""
    print("="*70)
    print("GOLD LAYER - Generating Analytics")
    print("="*70)
    
    import pandas as pd
    from pathlib import Path
    from datetime import datetime as dt
    
    SILVER_PATH = Path("/opt/data/delta-lake/silver")
    GOLD_PATH = Path("/opt/data/delta-lake/gold")
    
    # Get latest shipments file
    shipments_dir = SILVER_PATH / "shipments_scd2"
    csv_files = list(shipments_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"No shipments files found in {shipments_dir}")
        return
    
    shipments_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    print(f"Reading: {shipments_file}")
    
    # Load and process
    df = pd.read_csv(shipments_file)
    print(f"Loaded {len(df)} shipments")
    
    # Create summary
    summary = df.groupby('status').size().reset_index(name='count')
    summary['created_at'] = str(dt.now())
    
    # Save output
    output_dir = GOLD_PATH / "shipment_summary"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = dt.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"summary_{timestamp}.csv"
    
    summary.to_csv(str(output_file), index=False)
    
    print(f"\n✓ Gold layer complete!")
    print(f"✓ Processed {len(df)} shipments")
    print(f"✓ Saved to: {output_file}")
    print(f"\nSummary by Status:")
    print(summary.to_string(index=False))

# DAG definition
with DAG(
    'medallion_airflow_pipeline',
    default_args=default_args,
    description='✅ WORKING Medallion Pipeline in Airflow',
    schedule_interval=None,
    start_date=datetime(2026, 2, 6),
    catchup=False,
    tags=['production', 'medallion', 'airflow-ready'],
) as dag:

    start = DummyOperator(task_id='start')
    
    bronze = PythonOperator(
        task_id='bronze_layer',
        python_callable=execute_bronze,
    )
    
    silver = PythonOperator(
        task_id='silver_layer',
        python_callable=execute_silver,
    )
    
    gold = PythonOperator(
        task_id='gold_layer',
        python_callable=execute_gold,
    )
    
    complete = DummyOperator(task_id='complete')
    
    # Pipeline flow
    start >> bronze >> silver >> gold >> complete
