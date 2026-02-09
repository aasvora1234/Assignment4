"""
Silver Layer - Transactional Data Transformation
Applies data cleaning, validation, and SCD Type 2 for shipments table.
"""

from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col, current_timestamp, lit, row_number, lag, lead,
    coalesce, when, md5, concat_ws, monotonically_increasing_id,
    max as spark_max, min as spark_min
)
from pyspark.sql.types import *
from datetime import datetime
import sys

# Configuration
BRONZE_PATH = "/opt/data/delta-lake/bronze"
SILVER_PATH = "/opt/data/delta-lake/silver"

def create_spark_session():
    """Create Spark session with Delta Lake support"""
    return SparkSession.builder \
        .appName("Silver-Transactional-Transform") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
        .getOrCreate()

def read_bronze_table(spark, table_name):
    """Read table from Bronze layer"""
    path = f"{BRONZE_PATH}/{table_name}"
    return spark.read.format("delta").load(path)

def clean_and_validate(df, table_name):
    """Apply data cleaning and validation rules"""
    # Remove exact duplicates
    df = df.dropDuplicates()
    
    # Basic null handling - log but don't drop
    print(f"  Null check for {table_name}:")
    for column in df.columns:
        null_count = df.filter(col(column).isNull()).count()
        if null_count > 0:
            print(f"    - {column}: {null_count} nulls")
    
    return df

def implement_scd2_shipments(spark, bronze_df):
    """
    Implement SCD Type 2 for shipments table
    Tracks historical changes in shipment status
    """
    print("\n  Implementing SCD Type 2 for shipments...")
    
    # Read existing Silver shipments (if exists)
    silver_path = f"{SILVER_PATH}/shipments_scd2"
    
    try:
        existing_df = spark.read.format("delta").load(silver_path)
        print(f"  Found {existing_df.count()} existing records in Silver")
    except:
        print("  No existing Silver data - initial load")
        existing_df = None
    
    # Prepare incoming records
    incoming_df = bronze_df.select(
        col("shipment_id"),
        col("order_id"),
        col("origin_warehouse_id"),
        col("destination_city"),
        col("shipment_type"),
        col("status"),
        col("expected_delivery_date"),
        col("actual_delivery_date"),
        col("created_at"),
        col("updated_at"),
        col("ingestion_timestamp")
    )
    
    if existing_df is None:
        # Initial load - all records are new
        print("  Performing initial SCD2 load...")
        
        result_df = incoming_df \
            .withColumn("surrogate_key", monotonically_increasing_id()) \
            .withColumn("valid_from", col("created_at")) \
            .withColumn("valid_to", lit(None).cast(TimestampType())) \
            .withColumn("is_current", lit(True)) \
            .withColumn("version", lit(1)) \
            .withColumn("record_created_at", current_timestamp())
        
        return result_df
    
    else:
        # Incremental load - detect changes
        print("  Performing incremental SCD2 merge...")
        
        # Get current records
        current_records = existing_df.filter(col("is_current") == True)
        
        # Create business key for matching
        incoming_with_key = incoming_df.withColumn(
            "business_key",
            md5(concat_ws("|", col("shipment_id"), col("status")))
        )
        
        current_with_key = current_records.withColumn(
            "business_key",
            md5(concat_ws("|", col("shipment_id"), col("status")))
        )
        
        # Detect changed records
        changed_records = incoming_with_key.alias("incoming").join(
            current_with_key.alias("current"),
            on="shipment_id",
            how="left"
        ).filter(
            (col("incoming.business_key") != col("current.business_key")) |
            (col("current.business_key").isNull())
        ).select("incoming.*")
        
        changed_count = changed_records.count()
        print(f"  Detected {changed_count} changed/new records")
        
        if changed_count == 0:
            print("  No changes detected - returning existing data")
            return existing_df
        
        # Close out old records
        closed_records = current_with_key.alias("current").join(
            changed_records.alias("changed"),
            on="shipment_id",
            how="inner"
        ).select(
            col("current.surrogate_key"),
            col("current.shipment_id"),
            col("current.order_id"),
            col("current.origin_warehouse_id"),
            col("current.destination_city"),
            col("current.shipment_type"),
            col("current.status"),
            col("current.expected_delivery_date"),
            col("current.actual_delivery_date"),
            col("current.created_at"),
            col("current.updated_at"),
            col("current.ingestion_timestamp"),
            col("current.valid_from"),
            current_timestamp().alias("valid_to"),
            lit(False).alias("is_current"),
            col("current.version"),
            col("current.record_created_at")
        )
        
        # Create new records with incremented version
        window_spec = Window.partitionBy("shipment_id").orderBy(col("version").desc())
        
        max_versions = current_with_key.select(
            "shipment_id",
            spark_max("version").alias("max_version")
        ).groupBy("shipment_id").agg(spark_max("max_version").alias("max_version"))
        
        new_records = changed_records.alias("changed").join(
            max_versions.alias("versions"),
            on="shipment_id",
            how="left"
        ).select(
            (monotonically_increasing_id() + 1000000).alias("surrogate_key"),
            col("changed.shipment_id"),
            col("changed.order_id"),
            col("changed.origin_warehouse_id"),
            col("changed.destination_city"),
            col("changed.shipment_type"),
            col("changed.status"),
            col("changed.expected_delivery_date"),
            col("changed.actual_delivery_date"),
            col("changed.created_at"),
            col("changed.updated_at"),
            col("changed.ingestion_timestamp"),
            col("changed.updated_at").alias("valid_from"),
            lit(None).cast(TimestampType()).alias("valid_to"),
            lit(True).alias("is_current"),
            (coalesce(col("versions.max_version"), lit(0)) + 1).alias("version"),
            current_timestamp().alias("record_created_at")
        )
        
        # Combine: unchanged + closed + new
        unchanged_records = existing_df.join(
            changed_records,
            on="shipment_id",
            how="left_anti"
        )
        
        result_df = unchanged_records \
            .union(closed_records) \
            .union(new_records)
        
        print(f"  Final record count: {result_df.count()}")
        
        return result_df

def process_simple_table(spark, table_name):
    """Process non-SCD tables - simple cleaning and validation"""
    print(f"\nProcessing {table_name}...")
    
    df = read_bronze_table(spark, table_name)
    print(f"  Read {df.count()} records from Bronze")
    
    # Clean and validate
    df = clean_and_validate(df, table_name)
    
    # Add Silver metadata
    df = df \
        .withColumn("silver_processed_at", current_timestamp()) \
        .withColumn("created_date", col("created_at").cast("date"))
    
    # Write to Silver
    output_path = f"{SILVER_PATH}/{table_name}"
    
    df.write \
        .format("delta") \
        .mode("overwrite") \
        .partitionBy("created_date") \
        .option("overwriteSchema", "true") \
        .save(output_path)
    
    print(f"  ✓ Wrote {df.count()} records to Silver")
    return True

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("SILVER LAYER - TRANSACTIONAL DATA TRANSFORMATION")
    print("="*60 + "\n")
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # Process simple tables
    simple_tables = [
        "customers",
        "warehouses",
        "drivers",
        "vehicles",
        "shipment_types",
        "orders",
        "truck_assignments"
    ]
    
    for table in simple_tables:
        try:
            process_simple_table(spark, table)
        except Exception as e:
            print(f"  ✗ Error processing {table}: {str(e)}")
    
    # Process shipments with SCD Type 2
    print(f"\nProcessing shipments (SCD Type 2)...")
    try:
        bronze_shipments = read_bronze_table(spark, "shipments")
        print(f"  Read {bronze_shipments.count()} records from Bronze")
        
        silver_shipments = implement_scd2_shipments(spark, bronze_shipments)
        
        # Write to Silver
        output_path = f"{SILVER_PATH}/shipments_scd2"
        
        silver_shipments.write \
            .format("delta") \
            .mode("overwrite") \
            .partitionBy("is_current") \
            .option("overwriteSchema", "true") \
            .save(output_path)
        
        print(f"  ✓ Wrote {silver_shipments.count()} records to Silver (with SCD2)")
    except Exception as e:
        print(f"  ✗ Error processing shipments: {str(e)}")
    
    print(f"\n{'='*60}")
    print("TRANSFORMATION COMPLETE")
    print(f"{'='*60}\n")
    
    spark.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
