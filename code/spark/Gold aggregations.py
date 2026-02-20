"""
SIMPLIFIED Gold Layer - Analytics and Alerts
Joins shipments with IoT data to generate business insights
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

SILVER_PATH = "/opt/data/delta-lake/silver"
GOLD_PATH = "/opt/data/delta-lake/gold"

# Temperature thresholds per shipment type
TEMP_THRESHOLDS = {
    'Refrigerated': {'min': 2.0, 'max': 8.0},
    'Frozen': {'min': -25.0, 'max': -18.0},
    'Pharmaceutical': {'min': 2.0, 'max': 8.0},
    'Perishable': {'min': 0.0, 'max': 4.0},
    'Ambient': {'min': 15.0, 'max': 25.0},
    'Dry Goods': {'min': -10.0, 'max': 35.0}
}

def get_latest_csv(directory):
    """Get the most recent CSV file from a directory"""
    csv_files = list(Path(directory).glob("*.csv"))
    if not csv_files:
        return None
    return max(csv_files, key=lambda x: x.stat().st_mtime)

def generate_shipment_analytics():
    """Join shipments with IoT data and calculate temperature metrics"""
    print("\nGenerating shipment analytics...")
    
    # Load data with error handling
    shipments_file = get_latest_csv(Path(SILVER_PATH) / "shipments_scd2")
    iot_file = get_latest_csv(Path(SILVER_PATH) / "iot_sensor_readings_clean")
    assignments_file = get_latest_csv(Path(SILVER_PATH) / "truck_assignments")
    
    if not all([shipments_file, iot_file, assignments_file]):
        print("  ✗ Missing required Silver layer files")
        print(f"    Shipments: {'✓' if shipments_file else '✗'}")
        print(f"    IoT Data: {'✓' if iot_file else '✗'}")
        print(f"    Truck Assignments: {'✓' if assignments_file else '✗'}")
        return None
    
    shipments = pd.read_csv(shipments_file)
    iot_data = pd.read_csv(iot_file)
    truck_assignments = pd.read_csv(assignments_file)
    
    # Parse timestamps
    shipments['created_at'] = pd.to_datetime(shipments['created_at'])
    shipments['expected_delivery_date'] = pd.to_datetime(shipments['expected_delivery_date'])
    shipments['actual_delivery_date'] = pd.to_datetime(shipments['actual_delivery_date'])
    
    iot_data['timestamp'] = pd.to_datetime(iot_data['timestamp'])
    truck_assignments['assignment_start_time'] = pd.to_datetime(truck_assignments['assignment_start_time'])
    truck_assignments['assignment_end_time'] = pd.to_datetime(truck_assignments['assignment_end_time'])
    
    # Filter clean IoT readings
    iot_clean = iot_data[iot_data['data_quality_flag'] == 'CLEAN'].copy()
    
    print(f"  Loaded {len(shipments)} shipments")
    print(f"  Loaded {len(iot_clean)} clean IoT readings")
    print(f"  Loaded {len(truck_assignments)} truck assignments")
    
    # Join shipments with truck assignments
    shipments_with_trucks = shipments.merge(
        truck_assignments,
        left_on='shipment_id',
        right_on='shipment_id',
        how='inner'
    )
    
    print(f"  Joined {len(shipments_with_trucks)} shipments with trucks")
    
    # Join with IoT readings (within assignment time window)
    analytics = []
    
    for idx, shipment in shipments_with_trucks.iterrows():
        # Filter IoT readings for this truck within assignment period
        truck_readings = iot_clean[
            (iot_clean['truck_id'] == shipment['vehicle_id']) &
            (iot_clean['timestamp'] >= shipment['assignment_start_time']) &
            ((shipment['assignment_end_time'].isna()) | 
             (iot_clean['timestamp'] <= shipment['assignment_end_time']))
        ]
        
        if len(truck_readings) == 0:
            continue
        
        # Calculate temperature statistics
        temp_stats = {
            'shipment_id': shipment['shipment_id'],
            'order_id': shipment['order_id'],
            'shipment_type': shipment['shipment_type'],
            'status': shipment['status'],
            'destination_city': shipment['destination_city'],
            'created_at': shipment['created_at'],
            'expected_delivery_date': shipment['expected_delivery_date'],
            'actual_delivery_date': shipment['actual_delivery_date'],
            'avg_temperature': truck_readings['temperature'].mean(),
            'min_temperature': truck_readings['temperature'].min(),
            'max_temperature': truck_readings['temperature'].max(),
            'temp_stddev': truck_readings['temperature'].std(),
            'reading_count': len(truck_readings)
        }
        
        analytics.append(temp_stats)
    
    analytics_df = pd.DataFrame(analytics)
    
    print(f"  Generated analytics for {len(analytics_df)} shipments")
    
    # Add temperature thresholds
    analytics_df['min_temp_threshold'] = analytics_df['shipment_type'].map(
        lambda x: TEMP_THRESHOLDS.get(x, {}).get('min', -30)
    )
    analytics_df['max_temp_threshold'] = analytics_df['shipment_type'].map(
        lambda x: TEMP_THRESHOLDS.get(x, {}).get('max', 50)
    )
    
    # Calculate deviations
    analytics_df['temp_deviation_min'] = np.where(
        analytics_df['min_temperature'] < analytics_df['min_temp_threshold'],
        analytics_df['min_temp_threshold'] - analytics_df['min_temperature'],
        0.0
    )
    
    analytics_df['temp_deviation_max'] = np.where(
        analytics_df['max_temperature'] > analytics_df['max_temp_threshold'],
        analytics_df['max_temperature'] - analytics_df['max_temp_threshold'],
        0.0
    )
    
    analytics_df['max_deviation'] = np.maximum(
        analytics_df['temp_deviation_min'],
        analytics_df['temp_deviation_max']
    )
    
    # Classify violation severity
    analytics_df['violation_severity'] = np.where(
        analytics_df['max_deviation'] == 0, None,
        np.where(analytics_df['max_deviation'] <= 2.0, 'Minor',
        np.where(analytics_df['max_deviation'] <= 5.0, 'Major', 'Critical'))
    )
    
    analytics_df['has_violation'] = analytics_df['violation_severity'].notna()
    
    # Calculate delivery metrics
    analytics_df['delivery_duration_days'] = (
        (analytics_df['actual_delivery_date'] - analytics_df['created_at']).dt.total_seconds() / 86400
    )
    
    analytics_df['is_on_time'] = np.where(
        analytics_df['actual_delivery_date'].notna() & analytics_df['expected_delivery_date'].notna(),
        analytics_df['actual_delivery_date'] <= analytics_df['expected_delivery_date'],
        None
    )
    
    # Temperature compliance score
    analytics_df['temp_compliance_score'] = np.where(
        ~analytics_df['has_violation'], 100,
        np.where(analytics_df['violation_severity'] == 'Minor', 70,
        np.where(analytics_df['violation_severity'] == 'Major', 40, 0))
    )
    
    # Add time dimensions
    analytics_df['year'] = analytics_df['created_at'].dt.year
    analytics_df['month'] = analytics_df['created_at'].dt.month
    analytics_df['day'] = analytics_df['created_at'].dt.day
    analytics_df['gold_processed_at'] = datetime.now()
    
    # Round numeric columns
    numeric_cols = ['avg_temperature', 'min_temperature', 'max_temperature', 
                    'temp_stddev', 'max_deviation', 'delivery_duration_days']
    for col in numeric_cols:
        if col in analytics_df.columns:
            analytics_df[col] = analytics_df[col].round(2)
    
    # Save analytics
    output_dir = Path(GOLD_PATH) / "shipment_analytics"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    analytics_df.to_csv(output_file, index=False)
    
    print(f"  ✓ Saved {len(analytics_df)} analytics records")
    
    # Print summary
    violation_count = analytics_df['has_violation'].sum()
    print(f"\n  Temperature Violations: {violation_count}/{len(analytics_df)} shipments ({violation_count/len(analytics_df)*100:.1f}%)")
    
    if violation_count > 0:
        print("\n  Severity Breakdown:")
        print(analytics_df['violation_severity'].value_counts().to_string())
    
    return analytics_df

def generate_temperature_alerts(analytics_df):
    """Generate alerts for temperature violations"""
    print("\nGenerating temperature alerts...")
    
    # Filter for violations only
    alerts_df = analytics_df[analytics_df['has_violation'] == True].copy()
    
    if len(alerts_df) == 0:
        print("  ✓ No violations detected - no alerts generated")
        return None
    
    # Create alert records
    alerts_df['alert_id'] = 'TEMP_ALERT-' + alerts_df['shipment_id']
    alerts_df['deviation_celsius'] = alerts_df['max_deviation']
    
    alerts_df['recommended_action'] = np.where(
        alerts_df['violation_severity'] == 'Critical', 'IMMEDIATE ACTION REQUIRED',
        np.where(alerts_df['violation_severity'] == 'Major', 'REVIEW REQUIRED', 'MONITOR')
    )
    
    alerts_df['alert_generated_at'] = datetime.now()
    
    # Select final columns
    alert_cols = ['alert_id', 'shipment_id', 'order_id', 'shipment_type', 
                  'destination_city', 'violation_severity', 'deviation_celsius',
                  'avg_temperature', 'min_temp_threshold', 'max_temp_threshold',
                  'recommended_action', 'alert_generated_at', 'year', 'month']
    
    final_alerts = alerts_df[alert_cols]
    
    # Save alerts
    output_dir = Path(GOLD_PATH) / "temperature_alerts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    final_alerts.to_csv(output_file, index=False)
    
    print(f"  ✓ Generated {len(final_alerts)} temperature alerts")
    
    return final_alerts

def main():
    print("="*60)
    print("GOLD LAYER - ANALYTICS AND ALERTS")
    print("="*60)
    
    try:
        # Generate analytics
        analytics_df = generate_shipment_analytics()
        
        if analytics_df is None:
            print("\n✗ Analytics generation failed - check Silver layer files")
            return
        
        # Generate alerts
        alerts_df = generate_temperature_alerts(analytics_df)
        
        print(f"\n{'='*60}")
        print("✓ GOLD LAYER PROCESSING COMPLETE")
        print(f"{'='*60}")
        
        print("\nSummary by Shipment Type:")
        summary = analytics_df.groupby('shipment_type').agg({
            'shipment_id': 'count',
            'avg_temperature': 'mean',
            'temp_compliance_score': 'mean'
        }).round(1)
        summary.columns = ['shipment_count', 'avg_temp', 'avg_compliance']
        print(summary.to_string())
        print()
        
    except Exception as e:
        print(f"\n✗ Error during Gold layer processing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
