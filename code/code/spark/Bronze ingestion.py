"""
SIMPLIFIED Bronze Layer - Direct Python Ingestion
Uses pandas + psycopg2 instead of PySpark for simplicity
"""

import pandas as pd
import psycopg2
import json
from datetime import datetime
from pathlib import Path

# Configuration
DB_CONFIG = {
    'host': 'postgres',
    'port': '5432',
    'database': 'postgres',
    'user': 'admin',
    'password': 'password'
}

BRONZE_PATH = "/opt/data/delta-lake/bronze"
IOT_SOURCE = "/opt/data/iot_raw"

def read_postgres_to_csv(table_name):
    """Read table from PostgreSQL and save as CSV in Bronze layer"""
    print(f"\nIngesting {table_name}...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Read table
    query = f"SELECT * FROM logistics.{table_name}"
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Add audit columns
    df['ingestion_timestamp'] = datetime.now()
    df['source_system'] = 'PostgreSQL'
    df['source_table'] = table_name
    
    # Save to CSV (simpler than Delta)
    output_dir = Path(BRONZE_PATH) / table_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"  ✓ Ingested {len(df)} records to {output_file}")
    return len(df)

def read_iot_to_csv():
    """Read IoT JSON files and save as CSV"""
    print(f"\nIngesting IoT sensor data...")
    
    iot_dir = Path(IOT_SOURCE)
    all_readings = []
    
    for json_file in iot_dir.glob("*.json"):
        with open(json_file, 'r') as f:
            data = json.load(f)
            all_readings.extend(data['sensor_readings'])
    
    df = pd.DataFrame(all_readings)
    
    # Add audit columns
    df['ingestion_timestamp'] = datetime.now()
    df['source_system'] = 'IoT_Sensors'
    
    # Save to CSV
    output_dir = Path(BRONZE_PATH) / "iot_sensor_readings"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"iot_readings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"  ✓ Ingested {len(df)} IoT readings to {output_file}")
    return len(df)

def main():
    print("="*60)
    print("BRONZE LAYER - SIMPLIFIED INGESTION")
    print("="*60)
    
    tables = [
        'customers', 'warehouses', 'drivers', 'vehicles',
        'shipment_types', 'orders', 'shipments', 'truck_assignments'
    ]
    
    total_records = 0
    
    # Ingest transactional tables
    for table in tables:
        try:
            count = read_postgres_to_csv(table)
            total_records += count
        except Exception as e:
            print(f"  ✗ Error ingesting {table}: {str(e)}")
    
    # Ingest IoT data
    try:
        iot_count = read_iot_to_csv()
        total_records += iot_count
    except Exception as e:
        print(f"  ✗ Error ingesting IoT data: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"✓ BRONZE INGESTION COMPLETE")
    print(f"Total records ingested: {total_records}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
