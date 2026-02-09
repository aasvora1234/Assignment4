"""
Bronze Layer - Transactional Data Ingestion
Ingests raw data from PostgreSQL into Delta Lake Bronze layer
with minimal transformations and full audit trail.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit, col
from pyspark.sql.types import *
from datetime import datetime
import sys

# Configuration
POSTGRES_HOST = "postgres"
POSTGRES_PORT = "5432"
POSTGRES_DB = "smart_logistics"
POSTGRES_USER = "admin"
POSTGRES_PASSWORD = "password"
BRONZE_PATH = "/opt/data/delta-lake/bronze"
DLQ_PATH = "/opt/data/delta-lake/bronze/rejected_records"

def create_spark_session():
    """Create Spark session with Delta Lake support"""
    return SparkSession.builder \
        .appName("Bronze-Transactional-Ingestion") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0,org.postgresql:postgresql:42.6.0") \
        .getOrCreate()

def read_postgres_table(spark, table_name, schema_name="logistics"):
    """Read a table from PostgreSQL"""
    jdbc_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", f"{schema_name}.{table_name}") \
        .option("user", POSTGRES_USER) \
        .option("password", POSTGRES_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .load()
    
    return df

def add_audit_columns(df, source_table):
    """Add metadata columns for auditing"""
    return df \
        .withColumn("ingestion_timestamp", current_timestamp()) \
        .withColumn("source_system", lit("PostgreSQL")) \
        .withColumn("source_table", lit(source_table)) \
        .withColumn("ingestion_date", current_timestamp().cast("date"))

def write_to_bronze(df, table_name, partition_col="ingestion_date"):
    """Write DataFrame to Delta Lake Bronze layer"""
    output_path = f"{BRONZE_PATH}/{table_name}"
    
    try:
        df.write \
            .format("delta") \
            .mode("append") \
            .partitionBy(partition_col) \
            .option("mergeSchema", "true") \
            .save(output_path)
        
        print(f"✓ Successfully wrote {df.count()} records to {table_name}")
        return True
    except Exception as e:
        print(f"✗ Error writing to {table_name}: {str(e)}")
        write_to_dlq(df, table_name, str(e))
        return False

def write_to_dlq(df, table_name, error_msg):
    """Write failed records to Dead Letter Queue"""
    try:
        dlq_df = df \
            .withColumn("failed_table", lit(table_name)) \
            .withColumn("error_message", lit(error_msg)) \
            .withColumn("failed_timestamp", current_timestamp())
        
        dlq_df.write \
            .format("delta") \
            .mode("append") \
            .save(DLQ_PATH)
        
        print(f"✓ Wrote {df.count()} failed records to DLQ")
    except Exception as dlq_error:
        print(f"✗ Critical: Failed to write to DLQ: {str(dlq_error)}")

def ingest_table(spark, table_name):
    """Complete ingestion pipeline for a single table"""
    print(f"\n{'='*60}")
    print(f"Ingesting: {table_name}")
    print(f"{'='*60}")
    
    try:
        # Read from PostgreSQL
        df = read_postgres_table(spark, table_name)
        print(f"Read {df.count()} records from PostgreSQL")
        
        # Add audit columns
        df_with_audit = add_audit_columns(df, table_name)
        
        # Write to Bronze
        success = write_to_bronze(df_with_audit, table_name)
        
        return success
    except Exception as e:
        print(f"✗ Failed to ingest {table_name}: {str(e)}")
        return False

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("BRONZE LAYER - TRANSACTIONAL DATA INGESTION")
    print("="*60 + "\n")
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # List of tables to ingest
    tables = [
        "customers",
        "warehouses", 
        "drivers",
        "vehicles",
        "shipment_types",
        "orders",
        "shipments",
        "truck_assignments"
    ]
    
    results = {}
    
    for table in tables:
        results[table] = ingest_table(spark, table)
    
    # Summary
    print(f"\n{'='*60}")
    print("INGESTION SUMMARY")
    print(f"{'='*60}")
    
    successful = sum(1 for v in results.values() if v)
    failed = len(results) - successful
    
    print(f"✓ Successful: {successful}/{len(tables)}")
    print(f"✗ Failed: {failed}/{len(tables)}")
    
    if failed > 0:
        print("\nFailed tables:")
        for table, success in results.items():
            if not success:
                print(f"  - {table}")
    
    spark.stop()
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
