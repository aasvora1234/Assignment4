"""
Gold Layer - Analytics and Aggregations
Combines shipment data with IoT sensor readings to calculate temperature metrics,
detect violations, and generate alerts for business intelligence.
"""

from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col, avg, min as spark_min, max as spark_max, count, stddev,
    current_timestamp, lit, when, year, month, dayofmonth,
    concat_ws, round as spark_round, datediff, abs as spark_abs
)
from pyspark.sql.types import *
from datetime import datetime
import sys

# Configuration
SILVER_PATH = "/opt/data/delta-lake/silver"
GOLD_PATH = "/opt/data/delta-lake/gold"

# Temperature thresholds per shipment type (from business PRD)
TEMP_THRESHOLDS = {
    "Refrigerated": {"min": 2.0, "max": 8.0},
    "Frozen": {"min": -25.0, "max": -18.0},
    "Pharmaceutical": {"min": 2.0, "max": 8.0},
    "Perishable": {"min": 0.0, "max": 4.0},
    "Ambient": {"min": 15.0, "max": 25.0},
    "Dry Goods": {"min": -10.0, "max": 35.0}
}

def create_spark_session():
    """Create Spark session with Delta Lake support"""
    return SparkSession.builder \
        .appName("Gold-Analytics-Aggregation") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
        .getOrCreate()

def read_silver_table(spark, table_name):
    """Read table from Silver layer"""
    path = f"{SILVER_PATH}/{table_name}"
    return spark.read.format("delta").load(path)

def get_shipment_thresholds(spark):
    """Create a DataFrame with temperature thresholds per shipment type"""
    threshold_data = [
        ("Refrigerated", 2.0, 8.0),
        ("Frozen", -25.0, -18.0),
        ("Pharmaceutical", 2.0, 8.0),
        ("Perishable", 0.0, 4.0),
        ("Ambient", 15.0, 25.0),
        ("Dry Goods", -10.0, 35.0)
    ]
    
    schema = StructType([
        StructField("shipment_type", StringType(), False),
        StructField("min_temp_threshold", DoubleType(), False),
        StructField("max_temp_threshold", DoubleType(), False)
    ])
    
    return spark.createDataFrame(threshold_data, schema)

def calculate_shipment_temperature_stats(spark):
    """
    Join shipments with IoT readings to calculate temperature statistics per shipment
    """
    print("\nCalculating shipment temperature statistics...")
    
    # Read Silver data
    shipments = read_silver_table(spark, "shipments_scd2") \
        .filter(col("is_current") == True)  # Only current records
    
    iot_readings = read_silver_table(spark, "iot_sensor_readings_clean") \
        .filter(col("data_quality_flag") == "CLEAN")  # Only clean readings
    
    truck_assignments = read_silver_table(spark, "truck_assignments")
    
    print(f"  Shipments: {shipments.count()} current records")
    print(f"  IoT Readings: {iot_readings.count()} clean readings")
    print(f"  Truck Assignments: {truck_assignments.count()} assignments")
    
    # Join shipments with truck assignments
    shipments_with_trucks = shipments.alias("s").join(
        truck_assignments.alias("ta"),
        on=col("s.shipment_id") == col("ta.shipment_id"),
        how="inner"
    ).select(
        col("s.shipment_id"),
        col("s.order_id"),
        col("s.shipment_type"),
        col("s.status"),
        col("s.destination_city"),
        col("s.expected_delivery_date"),
        col("s.actual_delivery_date"),
        col("s.created_at"),
        col("ta.vehicle_id").alias("truck_id"),
        col("ta.assignment_start_time"),
        col("ta.assignment_end_time")
    )
    
    print(f"  Shipments with trucks: {shipments_with_trucks.count()}")
    
    # Join with IoT readings
    # Match readings within assignment time window
    shipment_readings = shipments_with_trucks.alias("st").join(
        iot_readings.alias("iot"),
        (col("st.truck_id") == col("iot.truck_id")) &
        (col("iot.timestamp") >= col("st.assignment_start_time")) &
        (
            (col("st.assignment_end_time").isNull()) |
            (col("iot.timestamp") <= col("st.assignment_end_time"))
        ),
        how="inner"
    )
    
    print(f"  Matched readings: {shipment_readings.count()}")
    
    # Calculate temperature statistics per shipment
    temp_stats = shipment_readings.groupBy(
        "shipment_id",
        "order_id",
        "shipment_type",
        "status",
        "destination_city",
        "expected_delivery_date",
        "actual_delivery_date",
        "created_at"
    ).agg(
        avg("temperature").alias("avg_temperature"),
        spark_min("temperature").alias("min_temperature"),
        spark_max("temperature").alias("max_temperature"),
        stddev("temperature").alias("temp_stddev"),
        count("*").alias("reading_count")
    )
    
    print(f"  Aggregated stats for {temp_stats.count()} shipments")
    
    return temp_stats

def detect_temperature_violations(df, thresholds_df):
    """
    Detect temperature violations by comparing actual temperatures against thresholds
    """
    print("\nDetecting temperature violations...")
    
    # Join with thresholds
    df_with_thresholds = df.join(
        thresholds_df,
        on="shipment_type",
        how="left"
    )
    
    # Calculate deviation from acceptable range
    df_violations = df_with_thresholds.withColumn(
        "temp_deviation_min",
        when(
            col("min_temperature") < col("min_temp_threshold"),
            col("min_temp_threshold") - col("min_temperature")
        ).otherwise(0.0)
    ).withColumn(
        "temp_deviation_max",
        when(
            col("max_temperature") > col("max_temp_threshold"),
            col("max_temperature") - col("max_temp_threshold")
        ).otherwise(0.0)
    ).withColumn(
        "max_deviation",
        when(
            col("temp_deviation_min") > col("temp_deviation_max"),
            col("temp_deviation_min")
        ).otherwise(col("temp_deviation_max"))
    )
    
    # Classify violation severity
    df_violations = df_violations.withColumn(
        "violation_severity",
        when(col("max_deviation") == 0, None)
        .when(col("max_deviation") <= 2.0, "Minor")
        .when(col("max_deviation") <= 5.0, "Major")
        .otherwise("Critical")
    ).withColumn(
        "has_violation",
        col("violation_severity").isNotNull()
    )
    
    # Count violations
    violation_count = df_violations.filter(col("has_violation") == True).count()
    total_shipments = df_violations.count()
    
    print(f"  Violations detected: {violation_count}/{total_shipments} shipments ({(violation_count/total_shipments*100):.1f}%)")
    
    # Breakdown by severity
    print("  Severity breakdown:")
    df_violations.groupBy("violation_severity").count().show()
    
    return df_violations

def generate_shipment_analytics(df):
    """Create final shipment analytics fact table"""
    print("\nGenerating shipment analytics table...")
    
    # Add calculated fields
    analytics_df = df.withColumn(
        "delivery_duration_days",
        when(
            col("actual_delivery_date").isNotNull(),
            datediff(col("actual_delivery_date"), col("created_at"))
        ).otherwise(None)
    ).withColumn(
        "is_on_time",
        when(
            col("actual_delivery_date").isNotNull() & col("expected_delivery_date").isNotNull(),
            col("actual_delivery_date") <= col("expected_delivery_date")
        ).otherwise(None)
    ).withColumn(
        "temp_compliance_score",
        when(
            col("has_violation") == False,
            lit(100)
        ).when(
            col("violation_severity") == "Minor",
            lit(70)
        ).when(
            col("violation_severity") == "Major",
            lit(40)
        ).otherwise(lit(0))
    )
    
    # Add time dimensions
    analytics_df = analytics_df.withColumn(
        "year",
        year(col("created_at"))
    ).withColumn(
        "month",
        month(col("created_at"))
    ).withColumn(
        "day",
        dayofmonth(col("created_at"))
    )
    
    # Add metadata
    analytics_df = analytics_df.withColumn(
        "gold_processed_at",
        current_timestamp()
    )
    
    # Select and order final columns
    final_df = analytics_df.select(
        "shipment_id",
        "order_id",
        "shipment_type",
        "status",
        "destination_city",
        "created_at",
        "expected_delivery_date",
        "actual_delivery_date",
        "delivery_duration_days",
        "is_on_time",
        spark_round("avg_temperature", 2).alias("avg_temperature"),
        spark_round("min_temperature", 2).alias("min_temperature"),
        spark_round("max_temperature", 2).alias("max_temperature"),
        spark_round("temp_stddev", 2).alias("temp_stddev"),
        "reading_count",
        "min_temp_threshold",
        "max_temp_threshold",
        spark_round("max_deviation", 2).alias("max_deviation"),
        "has_violation",
        "violation_severity",
        "temp_compliance_score",
        "year",
        "month",
        "day",
        "gold_processed_at"
    )
    
    return final_df

def generate_alerts(spark, analytics_df):
    """Generate alerts for critical temperature violations"""
    print("\nGenerating temperature alerts...")
    
    # Filter for violations only
    alerts = analytics_df.filter(col("has_violation") == True).select(
        concat_ws("-", lit("TEMP_ALERT"), col("shipment_id")).alias("alert_id"),
        col("shipment_id"),
        col("order_id"),
        col("shipment_type"),
        col("destination_city"),
        col("violation_severity"),
        col("max_deviation").alias("deviation_celsius"),
        col("avg_temperature"),
        col("min_temp_threshold"),
        col("max_temp_threshold"),
        when(
            col("violation_severity") == "Critical",
            lit("IMMEDIATE ACTION REQUIRED")
        ).when(
            col("violation_severity") == "Major",
            lit("REVIEW REQUIRED")
        ).otherwise(
            lit("MONITOR")
        ).alias("recommended_action"),
        current_timestamp().alias("alert_generated_at"),
        col("year"),
        col("month")
    )
    
    alert_count = alerts.count()
    print(f"  Generated {alert_count} alerts")
    
    return alerts

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("GOLD LAYER - ANALYTICS AND AGGREGATIONS")
    print("="*60 + "\n")
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # Step 1: Get temperature thresholds
        thresholds_df = get_shipment_thresholds(spark)
        
        # Step 2: Calculate shipment temperature stats
        temp_stats_df = calculate_shipment_temperature_stats(spark)
        
        # Step 3: Detect violations
        violations_df = detect_temperature_violations(temp_stats_df, thresholds_df)
        
        # Step 4: Generate analytics
        analytics_df = generate_shipment_analytics(violations_df)
        
        # Step 5: Write shipment analytics
        print("\nWriting shipment analytics to Gold layer...")
        analytics_path = f"{GOLD_PATH}/shipment_analytics"
        
        analytics_df.write \
            .format("delta") \
            .mode("overwrite") \
            .partitionBy("year", "month") \
            .option("overwriteSchema", "true") \
            .save(analytics_path)
        
        print(f"  ✓ Wrote {analytics_df.count()} analytics records")
        
        # Step 6: Generate and write alerts
        alerts_df = generate_alerts(spark, analytics_df)
        
        if alerts_df.count() > 0:
            print("\nWriting temperature alerts to Gold layer...")
            alerts_path = f"{GOLD_PATH}/temperature_alerts"
            
            alerts_df.write \
                .format("delta") \
                .mode("overwrite") \
                .partitionBy("year", "month") \
                .option("overwriteSchema", "true") \
                .save(alerts_path)
            
            print(f"  ✓ Wrote {alerts_df.count()} alerts")
        
        # Summary statistics
        print(f"\n{'='*60}")
        print("GOLD LAYER SUMMARY")
        print(f"{'='*60}")
        
        print("\nShipment Analytics:")
        analytics_df.groupBy("shipment_type").agg(
            count("*").alias("shipment_count"),
            spark_round(avg("avg_temperature"), 1).alias("avg_temp"),
            spark_round(avg("temp_compliance_score"), 0).alias("avg_compliance")
        ).show()
        
        print("\nViolation Summary:")
        analytics_df.groupBy("violation_severity").count().show()
        
        print("\n✓ Gold layer processing complete!")
        
    except Exception as e:
        print(f"\n✗ Error during Gold layer processing: {str(e)}")
        import traceback
        traceback.print_exc()
        spark.stop()
        return 1
    
    spark.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
