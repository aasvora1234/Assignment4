"""
Silver Layer - IoT Sensor Data Transformation
Applies data cleaning, outlier detection, and deduplication for IoT sensor readings.
"""

from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col, current_timestamp, lit, row_number,
    avg, stddev, abs as spark_abs, when,
    to_timestamp, unix_timestamp, lag
)
from pyspark.sql.types import *
from datetime import datetime
import sys

# Configuration
BRONZE_PATH = "/opt/data/delta-lake/bronze"
SILVER_PATH = "/opt/data/delta-lake/silver"

# Outlier thresholds (degrees Celsius)
TEMP_THRESHOLDS = {
    "min_valid": -30.0,  # Absolute minimum
    "max_valid": 50.0,   # Absolute maximum
    "z_score_threshold": 3.0  # Standard deviations for outlier detection
}

def create_spark_session():
    """Create Spark session with Delta Lake support"""
    return SparkSession.builder \
        .appName("Silver-IoT-Transform") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
        .getOrCreate()

def read_bronze_iot(spark):
    """Read IoT sensor data from Bronze layer"""
    path = f"{BRONZE_PATH}/iot_sensor_readings"
    return spark.read.format("delta").load(path)

def convert_timestamps(df):
    """Convert timestamp strings to proper timestamp type"""
    return df.withColumn(
        "timestamp_converted",
        to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSS")
    ).withColumn(
        "reading_date",
        col("timestamp_converted").cast("date")
    )

def deduplicate_readings(df):
    """Remove duplicate sensor readings"""
    print("  Deduplicating sensor readings...")
    
    initial_count = df.count()
    
    # Define window for detecting duplicates
    # Same truck, same second = duplicate
    window_spec = Window.partitionBy(
        "truck_id",
        unix_timestamp("timestamp_converted").cast("long") // 60  # Group by minute
    ).orderBy("timestamp_converted")
    
    # Keep only the first reading per minute per truck
    df_deduped = df \
        .withColumn("row_num", row_number().over(window_spec)) \
        .filter(col("row_num") == 1) \
        .drop("row_num")
    
    final_count = df_deduped.count()
    duplicates_removed = initial_count - final_count
    
    print(f"    Removed {duplicates_removed} duplicate readings")
    print(f"    Deduplication rate: {(duplicates_removed/initial_count*100):.2f}%")
    
    return df_deduped

def detect_outliers(df):
    """
    Detect temperature outliers using multiple methods:
    1. Absolute range check
    2. Z-score (statistical outlier)
    3. Rate of change check
    """
    print("  Detecting temperature outliers...")
    
    # 1. Absolute range outliers
    df = df.withColumn(
        "is_out_of_range",
        (col("temperature") < TEMP_THRESHOLDS["min_valid"]) |
        (col("temperature") > TEMP_THRESHOLDS["max_valid"])
    )
    
    # 2. Calculate Z-score for each truck
    window_truck = Window.partitionBy("truck_id")
    
    df = df.withColumn(
        "temp_mean",
        avg("temperature").over(window_truck)
    ).withColumn(
        "temp_stddev",
        stddev("temperature").over(window_truck)
    ).withColumn(
        "z_score",
        when(
            col("temp_stddev") > 0,
            (col("temperature") - col("temp_mean")) / col("temp_stddev")
        ).otherwise(0.0)
    ).withColumn(
        "is_statistical_outlier",
        spark_abs(col("z_score")) > TEMP_THRESHOLDS["z_score_threshold"]
    )
    
    # 3. Rate of change outlier (sudden spike/drop)
    window_time = Window.partitionBy("truck_id").orderBy("timestamp_converted")
    
    df = df.withColumn(
        "prev_temperature",
        lag("temperature", 1).over(window_time)
    ).withColumn(
        "temp_change_rate",
        when(
            col("prev_temperature").isNotNull(),
            spark_abs(col("temperature") - col("prev_temperature"))
        ).otherwise(0.0)
    ).withColumn(
        "is_rapid_change",
        col("temp_change_rate") > 10.0  # More than 10°C change
    )
    
    # Combined outlier flag
    df = df.withColumn(
        "is_outlier",
        col("is_out_of_range") | 
        col("is_statistical_outlier") | 
        col("is_rapid_change")
    ).withColumn(
        "outlier_reason",
        when(col("is_out_of_range"), "OUT_OF_RANGE")
        .when(col("is_statistical_outlier"), "STATISTICAL_OUTLIER")
        .when(col("is_rapid_change"), "RAPID_CHANGE")
        .otherwise(None)
    )
    
    # Count outliers
    outlier_count = df.filter(col("is_outlier") == True).count()
    total_count = df.count()
    
    print(f"    Detected {outlier_count} outliers ({(outlier_count/total_count*100):.2f}%)")
    
    # Breakdown by type
    print("    Outlier breakdown:")
    print(f"      - Out of range: {df.filter(col('is_out_of_range')).count()}")
    print(f"      - Statistical: {df.filter(col('is_statistical_outlier')).count()}")
    print(f"      - Rapid change: {df.filter(col('is_rapid_change')).count()}")
    
    return df

def apply_data_quality_rules(df):
    """Apply business rules and data quality checks"""
    print("  Applying data quality rules...")
    
    # Flag invalid GPS coordinates
    df = df.withColumn(
        "is_valid_gps",
        (col("latitude").between(-90, 90)) &
        (col("longitude").between(-180, 180))
    )
    
    invalid_gps = df.filter(col("is_valid_gps") == False).count()
    if invalid_gps > 0:
        print(f"    Warning: {invalid_gps} readings have invalid GPS coordinates")
    
    # Overall quality score (0-100)
    df = df.withColumn(
        "quality_score",
        when(
            col("is_outlier") | ~col("is_valid_gps"), 
            lit(50)  # Low quality
        ).when(
            col("z_score").isNull() | (spark_abs(col("z_score")) < 1.0),
            lit(100)  # High quality
        ).otherwise(
            lit(75)  # Medium quality
        )
    )
    
    return df

def add_silver_metadata(df):
    """Add Silver layer metadata columns"""
    return df \
        .withColumn("silver_processed_at", current_timestamp()) \
        .withColumn("data_quality_flag", 
            when(col("is_outlier"), "FLAGGED")
            .otherwise("CLEAN")
        )

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("SILVER LAYER - IOT SENSOR DATA TRANSFORMATION")
    print("="*60 + "\n")
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # Read Bronze data
        print("Reading Bronze IoT data...")
        bronze_df = read_bronze_iot(spark)
        initial_count = bronze_df.count()
        print(f"  Read {initial_count} records")
        
        # Step 1: Convert timestamps
        print("\nStep 1: Converting timestamps...")
        df = convert_timestamps(bronze_df)
        
        # Step 2: Deduplicate
        print("\nStep 2: Deduplication...")
        df = deduplicate_readings(df)
        
        # Step 3: Detect outliers
        print("\nStep 3: Outlier detection...")
        df = detect_outliers(df)
        
        # Step 4: Data quality rules
        print("\nStep 4: Data quality validation...")
        df = apply_data_quality_rules(df)
        
        # Step 5: Add metadata
        print("\nStep 5: Adding Silver metadata...")
        df = add_silver_metadata(df)
        
        # Select final columns
        final_df = df.select(
            "truck_id",
            col("timestamp_converted").alias("timestamp"),
            "temperature",
            "latitude",
            "longitude",
            "is_outlier",
            "outlier_reason",
            "is_valid_gps",
            "quality_score",
            "data_quality_flag",
            "z_score",
            "temp_change_rate",
            "silver_processed_at",
            "reading_date"
        )
        
        # Write to Silver
        print("\nWriting to Silver layer...")
        output_path = f"{SILVER_PATH}/iot_sensor_readings_clean"
        
        final_df.write \
            .format("delta") \
            .mode("overwrite") \
            .partitionBy("reading_date") \
            .option("overwriteSchema", "true") \
            .save(output_path)
        
        final_count = final_df.count()
        
        print(f"\n{'='*60}")
        print("TRANSFORMATION SUMMARY")
        print(f"{'='*60}")
        print(f"Initial records: {initial_count}")
        print(f"Final records: {final_count}")
        print(f"Data retention: {(final_count/initial_count*100):.2f}%")
        print(f"✓ Successfully wrote to Silver layer")
        
    except Exception as e:
        print(f"\n✗ Error during transformation: {str(e)}")
        import traceback
        traceback.print_exc()
        spark.stop()
        return 1
    
    spark.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
