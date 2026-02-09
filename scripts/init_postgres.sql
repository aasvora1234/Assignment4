-- Smart Logistics Tracking - Database Initialization Script
-- Version 1.0

-- Create Schema
CREATE SCHEMA IF NOT EXISTS logistics;

-- ==========================================
-- 1. Reference Tables (Lookup Data)
-- ==========================================

-- Warehouse Locations
CREATE TABLE logistics.warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    pincode VARCHAR(20),
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    capacity_sqft INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Drivers
CREATE TABLE logistics.drivers (
    driver_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    rating DECIMAL(3, 2) DEFAULT 5.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vehicles (Trucks)
CREATE TABLE logistics.vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    license_plate VARCHAR(20) UNIQUE NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL CHECK (vehicle_type IN ('Refrigerated Truck', 'Standard Truck', 'Van')),
    capacity_kg INT NOT NULL,
    has_refrigeration BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE', 'IN_TRANSIT', 'MAINTENANCE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shipment Types & Thresholds
CREATE TABLE logistics.shipment_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    min_temperature DECIMAL(5, 2),
    max_temperature DECIMAL(5, 2),
    description TEXT
);

-- ==========================================
-- 2. Transactional Tables
-- ==========================================

-- Customers
CREATE TABLE logistics.customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders
CREATE TABLE logistics.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id INT REFERENCES logistics.customers(customer_id),
    order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    priority VARCHAR(20) DEFAULT 'STANDARD',
    status VARCHAR(20) DEFAULT 'PENDING'
);

-- Shipments
CREATE TABLE logistics.shipments (
    shipment_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) REFERENCES logistics.orders(order_id),
    origin_warehouse_id INT REFERENCES logistics.warehouses(warehouse_id),
    destination_city VARCHAR(100) NOT NULL,
    shipment_type VARCHAR(50) REFERENCES logistics.shipment_types(type_name),
    status VARCHAR(50) NOT NULL,
    expected_delivery_date TIMESTAMP,
    actual_delivery_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Truck Assignments (Mapping shipment to truck/driver for a time period)
CREATE TABLE logistics.truck_assignments (
    assignment_id SERIAL PRIMARY KEY,
    shipment_id VARCHAR(50) REFERENCES logistics.shipments(shipment_id),
    vehicle_id INT REFERENCES logistics.vehicles(vehicle_id),
    driver_id INT REFERENCES logistics.drivers(driver_id),
    assignment_start_time TIMESTAMP NOT NULL,
    assignment_end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'COMPLETED', 'CANCELLED')),
    CONSTRAINT unique_active_assignment_per_truck UNIQUE (vehicle_id, assignment_end_time) -- Partial Logic enforced in app
);

-- ==========================================
-- 3. Initial Data Loading (Seed Data)
-- ==========================================

-- Load Shipment Types with Temperature Thresholds
INSERT INTO logistics.shipment_types (type_name, min_temperature, max_temperature, description) VALUES
('Refrigerated', 2.0, 8.0, 'Perishables, Vaccines, Dairy'),
('Frozen', -25.0, -18.0, 'Ice Cream, Frozen Meat'),
('Pharmaceutical', 2.0, 8.0, 'Temperature sensitive drugs'),
('Perishable', 0.0, 4.0, 'Fruits, Vegetables'),
('Ambient', 15.0, 25.0, 'Chocolates, Cosmetics, Electronics'),
('Dry Goods', -10.0, 35.0, 'Furniture, Clothing, Non-perishables');

-- Load sample Warehouses
INSERT INTO logistics.warehouses (name, city, state, latitude, longitude, capacity_sqft) VALUES
('North Zone Hub', 'Delhi', 'Delhi', 28.6139, 77.2090, 50000),
('West Zone Hub', 'Mumbai', 'Maharashtra', 19.0760, 72.8777, 75000),
('South Zone Hub', 'Bangalore', 'Karnataka', 12.9716, 77.5946, 60000),
('East Zone Hub', 'Kolkata', 'West Bengal', 22.5726, 88.3639, 45000);

-- Indexes for performance
CREATE INDEX idx_shipments_order_id ON logistics.shipments(order_id);
CREATE INDEX idx_shipments_status ON logistics.shipments(status);
CREATE INDEX idx_assignments_shipment_id ON logistics.truck_assignments(shipment_id);
CREATE INDEX idx_assignments_time_range ON logistics.truck_assignments(assignment_start_time, assignment_end_time);

COMMIT;
