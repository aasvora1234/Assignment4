"""
Bronze Layer - IoT Sensor Data Ingestion
Ingests raw JSON sensor readings into Delta Lake Bronze layer
with schema validation and error handling.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit, col, input_file_name, to_date
from pyspark.sql.types import *
from datetime import datetime
import sys

# Configuration
IOT_SOURCE_PATH = "/opt/data/iot_raw"
BRONZE_PATH = "/opt/data/delta-lake/bronze"
DLQ_PATH = "/opt/data/delta-lake/bronze/rejected_records"

def create_spark_session():
    """Create Spark session with Delta Lake support"""
    return SparkSession.builder \
        .appName("Bronze-IoT-Ingestion") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
        .getOrCreate()

def define_iot_schema():
    """Define expected schema for IoT sensor data"""
    return StructType([
        StructField("truck_id", IntegerType(), True),
        StructField("timestamp", StringType(), True),  # Will be converted later
        StructField("temperature", DoubleType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True)
    ])

def read_iot_files(spark):
    """Read all JSON files from IoT source directory"""
    schema = define_iot_schema()
    
    try:
        df = spark.read \
            .schema(schema) \
            .option("mode", "PERMISSIVE") \
            .option("columnNameOfCorruptRecord", "_corrupt_record") \
            .json(f"{IOT_SOURCE_PATH}/*.json")
        
        # Add source file name
        df = df.withColumn("source_file", input_file_name())
        
        return df
    except Exception as e:
        print(f"✗ Error reading IoT files: {str(e)}")
        return None

def validate_and_clean(df):
    """Validate IoT data and separate good/bad records"""
    # Filter out corrupt records
    good_records = df.filter(col("_corrupt_record").isNull())
    bad_records = df.filter(col("_corrupt_record").isNotNull())
    
    # Additional validation: non-null critical fields
    good_records = good_records.filter(
        col("truck_id").isNotNull() & 
        col("timestamp").isNotNull() &
        col("temperature").isNotNull()
    )
    
    return good_records, bad_records

def add_audit_columns(df):
    """Add metadata columns for auditing"""
    return df \
        .withColumn("ingestion_timestamp", current_timestamp()) \
        .withColumn("source_system", lit("IoT-Sensors")) \
        .withColumn("reading_date", to_date(col("timestamp")))

def write_to_bronze(df, table_name="iot_sensor_readings"):
    """Write DataFrame to Delta Lake Bronze layer"""
    output_path = f"{BRONZE_PATH}/{table_name}"
    
    try:
        df.write \
            .format("delta") \
            .mode("append") \
            .partitionBy("reading_date") \
            .option("mergeSchema", "true") \
            .save(output_path)
        
        print(f"✓ Successfully wrote {df.count()} records to {table_name}")
        return True
    except Exception as e:
        print(f"✗ Error writing to {table_name}: {str(e)}")
        write_to_dlq(df, table_name, str(e))
        return False

def write_to_dlq(df, source, error_msg):
    """Write failed records to Dead Letter Queue"""
    try:
        dlq_df = df \
            .withColumn("failed_source", lit(source)) \
            .withColumn("error_message", lit(error_msg)) \
            .withColumn("failed_timestamp", current_timestamp())
        
        dlq_df.write \
            .format("delta") \
            .mode("append") \
            .save(DLQ_PATH)
        
        print(f"✓ Wrote {df.count()} failed records to DLQ")
    except Exception as dlq_error:
        print(f"✗ Critical: Failed to write to DLQ: {str(dlq_error)}")

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("BRONZE LAYER - IOT SENSOR DATA INGESTION")
    print("="*60 + "\n")
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # Read IoT files
    print("Reading IoT sensor JSON files...")
    df = read_iot_files(spark)
    
    if df is None:
        print("✗ No data to process. Exiting.")
        spark.stop()
        return 1
    
    total_records = df.count()
    print(f"Found {total_records} total records")
    
    # Validate and separate good/bad records
    print("\nValidating records...")
    good_df, bad_df = validate_and_clean(df)
    
    good_count = good_df.count()
    bad_count = bad_df.count()
    
    print(f"✓ Valid records: {good_count}")
    print(f"✗ Invalid records: {bad_count}")
    
    # Process bad records to DLQ
    if bad_count > 0:
        print("\nWriting invalid records to DLQ...")
        write_to_dlq(bad_df, "iot_sensor_readings", "Schema validation failed or corrupt record")
    
    # Add audit columns to good records
    if good_count > 0:
        print("\nAdding audit columns...")
        good_df = add_audit_columns(good_df)
        
        # Write to Bronze
        print("\nWriting to Bronze layer...")
        success = write_to_bronze(good_df)
    else:
        print("\n✗ No valid records to write to Bronze")
        success = False
    
    # Summary
    print(f"\n{'='*60}")
    print("INGESTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total Records: {total_records}")
    print(f"✓ Successfully Ingested: {good_count}")
    print(f"✗ Rejected to DLQ: {bad_count}")
    print(f"Success Rate: {(good_count/total_records*100):.2f}%")
    
    spark.stop()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
