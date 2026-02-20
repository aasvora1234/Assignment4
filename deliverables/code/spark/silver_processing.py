"""
SIMPLIFIED Silver Layer - Data Cleaning and Transformation
Reads from Bronze CSV, applies transformations, saves to Silver CSV
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

BRONZE_PATH = "/opt/data/delta-lake/bronze"
SILVER_PATH = "/opt/data/delta-lake/silver"

def get_latest_csv(directory):
    """Get the most recent CSV file from a directory"""
    csv_files = list(Path(directory).glob("*.csv"))
    if not csv_files:
        return None
    return max(csv_files, key=lambda x: x.stat().st_mtime)

def clean_shipments_with_scd2():
    """Transform shipments with SCD Type 2 logic"""
    print("\nProcessing shipments (SCD Type 2)...")
    
    bronze_file = get_latest_csv(Path(BRONZE_PATH) / "shipments")
    df = pd.read_csv(bronze_file)
    
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Add SCD Type 2 columns
    df['surrogate_key'] = range(1, len(df) + 1)
    df['valid_from'] = pd.to_datetime(df['created_at'])
    df['valid_to'] = pd.NaT
    df['is_current'] = True
    df['version'] = 1
    df['silver_processed_at'] = datetime.now()
    
    # Save to Silver
    output_dir = Path(SILVER_PATH) / "shipments_scd2"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"shipments_scd2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"  ✓ Processed {len(df)} shipment records with SCD Type 2")
    return df

def clean_iot_data():
    """Clean and validate IoT sensor data"""
    print("\nProcessing IoT sensor data...")
    
    bronze_file = get_latest_csv(Path(BRONZE_PATH) / "iot_sensor_readings")
    df = pd.read_csv(bronze_file)
    
    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['reading_date'] = df['timestamp'].dt.date
    
    # Deduplicate (keep first reading per truck per minute)
    df['minute'] = df['timestamp'].dt.floor('T')
    df = df.sort_values('timestamp').drop_duplicates(subset=['truck_id', 'minute'], keep='first')
    df = df.drop('minute', axis=1)
    
    initial_count = len(df)
    
    # Outlier detection - Temperature range
    df['is_out_of_range'] = (df['temperature'] < -30) | (df['temperature'] > 50)
    
    # Statistical outlier detection (Z-score)
    df['temp_mean'] = df.groupby('truck_id')['temperature'].transform('mean')
    df['temp_std'] = df.groupby('truck_id')['temperature'].transform('std')
    df['z_score'] = np.where(df['temp_std'] > 0, 
                             (df['temperature'] - df['temp_mean']) / df['temp_std'], 
                             0)
    df['is_statistical_outlier'] = np.abs(df['z_score']) > 3.0
    
    # Rate of change outlier
    df = df.sort_values(['truck_id', 'timestamp'])
    df['prev_temperature'] = df.groupby('truck_id')['temperature'].shift(1)
    df['temp_change_rate'] = np.abs(df['temperature'] - df['prev_temperature']).fillna(0)
    df['is_rapid_change'] = df['temp_change_rate'] > 10.0
    
    # Combined outlier flag
    df['is_outlier'] = df['is_out_of_range'] | df['is_statistical_outlier'] | df['is_rapid_change']
    df['outlier_reason'] = np.where(df['is_out_of_range'], 'OUT_OF_RANGE',
                           np.where(df['is_statistical_outlier'], 'STATISTICAL_OUTLIER',
                           np.where(df['is_rapid_change'], 'RAPID_CHANGE', None)))
    
    # GPS validation
    df['is_valid_gps'] = (df['latitude'].between(-90, 90)) & (df['longitude'].between(-180, 180))
    
    # Quality score
    df['quality_score'] = np.where(df['is_outlier'] | ~df['is_valid_gps'], 50,
                          np.where(np.abs(df['z_score']) < 1.0, 100, 75))
    
    df['data_quality_flag'] = np.where(df['is_outlier'], 'FLAGGED', 'CLEAN')
    df['silver_processed_at'] = datetime.now()
    
    outlier_count = df['is_outlier'].sum()
    
    # Save to Silver
    output_dir = Path(SILVER_PATH) / "iot_sensor_readings_clean"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"iot_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Select final columns
    final_cols = ['truck_id', 'timestamp', 'temperature', 'latitude', 'longitude',
                  'is_outlier', 'outlier_reason', 'is_valid_gps', 'quality_score',
                  'data_quality_flag', 'z_score', 'temp_change_rate', 'silver_processed_at', 'reading_date']
    df[final_cols].to_csv(output_file, index=False)
    
    print(f"  ✓ Processed {len(df)} IoT readings")
    print(f"  ✓ Detected {outlier_count} outliers ({outlier_count/initial_count*100:.1f}%)")
    
    return df[final_cols]

def process_simple_table(table_name):
    """Process non-SCD tables with basic cleaning"""
    print(f"\nProcessing {table_name}...")
    
    bronze_file = get_latest_csv(Path(BRONZE_PATH) / table_name)
    if not bronze_file:
        print(f"  ⚠ No data found for {table_name}")
        return None
    
    df = pd.read_csv(bronze_file)
    
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Add Silver metadata
    df['silver_processed_at'] = datetime.now()
    
    # Save to Silver
    output_dir = Path(SILVER_PATH) / table_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"  ✓ Processed {len(df)} records")
    return df

def main():
    print("="*60)
    print("SILVER LAYER - DATA TRANSFORMATION")
    print("="*60)
    
    # Process simple tables
    simple_tables = ['customers', 'warehouses', 'drivers', 'vehicles', 
                     'shipment_types', 'orders', 'truck_assignments']
    
    for table in simple_tables:
        try:
            process_simple_table(table)
        except Exception as e:
            print(f"  ✗ Error processing {table}: {str(e)}")
    
    # Process shipments with SCD Type 2
    try:
        clean_shipments_with_scd2()
    except Exception as e:
        print(f"  ✗ Error processing shipments: {str(e)}")
    
    # Process IoT data
    try:
        clean_iot_data()
    except Exception as e:
        print(f"  ✗ Error processing IoT data: {str(e)}")
    
    print(f"\n{'='*60}")
    print("✓ SILVER LAYER TRANSFORMATION COMPLETE")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
