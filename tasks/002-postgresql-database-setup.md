# Task 002: PostgreSQL Database Setup

## Objective
Design and create the complete PostgreSQL database schema for transactional data with all 5 core tables, relationships, and reference data.

## Scope

### 1. Database Schema Design
- Design schema for 5 core tables (Shipments, Orders, Vehicles, Warehouses, Drivers)
- Define primary keys, foreign keys, and indexes
- Establish referential integrity constraints
- Define data types for all columns
- Set up NOT NULL constraints and default values

### 2. Supporting Tables
- Create Customers table for order references
- Create Shipment Types reference table with temperature thresholds
- Create Truck Assignments mapping table (shipment to vehicle/driver)
- Create any additional lookup/dimension tables needed

### 3. Table Implementation
- Create SQL DDL statements for all tables
- Define sequences for auto-incrementing IDs
- Set up indexes on foreign keys and frequently queried columns
- Add check constraints for business rules (e.g., dates, valid statuses)

### 4. Database Initialization Script
- Create init script that runs on PostgreSQL container startup
- Set up database and schema creation
- Create all tables in proper dependency order
- Add necessary indexes and constraints
- Configure database settings for optimal performance

### 5. Reference Data
- Define shipment statuses (Created, Assigned, In Transit, Out for Delivery, Delivered, Cancelled, Returned, Failed Delivery)
- Define shipment types (Refrigerated, Frozen, Pharmaceutical, Perishable, Ambient, Dry Goods)
- Create temperature threshold mappings for each shipment type
- Load reference data into respective tables

## Success Criteria
- All 5 core tables created successfully
- Foreign key relationships properly established
- Reference data loaded correctly
- Database initializes successfully on container startup
- Schema supports all business requirements from PRD
- No orphan records possible due to proper constraints

## Dependencies
- Task 001 completed (Docker infrastructure ready)
- PostgreSQL service running in Docker

## Deliverables
- SQL DDL scripts for all tables
- init_postgres.sql initialization script
- Reference data insert statements
- Database schema diagram (ERD)
- Documentation of all table structures and relationships
