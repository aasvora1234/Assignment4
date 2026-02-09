# Task 003: Sample Data Generation

## Objective
Create realistic, synthetic sample data for all tables and IoT sensor readings covering 2 weeks of operations with proper distributions and patterns.

## Scope

### 1. Transactional Data Generation
- Generate 50 customers with realistic Indian names, addresses, and phone numbers
- Generate 150 orders with realistic amounts (₹5,000 - ₹50,000)
- Generate 100 shipments across different types and statuses
- Generate 50 vehicles with Indian license plates (DL/MH/KA/TN formats)
- Generate 30 drivers with Indian names and valid license numbers
- Generate 20 warehouses in major Indian cities

### 2. Shipment Distribution Strategy
- Distribute shipments across types: 30% Refrigerated, 20% Frozen, 15% Pharmaceutical, 20% Perishable, 10% Ambient, 5% Dry Goods
- Distribute statuses: 50% Delivered, 15% In Transit, 12% Out for Delivery, 8% Assigned, 5% Created, 5% Cancelled, 3% Returned, 2% Failed Delivery
- Create realistic date ranges spanning 2 weeks (2026-01-23 to 2026-02-06)

### 3. Truck Assignment Generation
- Generate 120 truck assignments (1.2x shipments to account for reassignments)
- Include 10% of shipments with mid-route truck changes
- Set realistic assignment start and end times
- Ensure no overlapping assignments for the same truck

### 4. IoT Sensor Data Generation
- Generate 1200+ sensor readings (approximately 12 per shipment)
- Sample readings every 15-30 minutes during transit
- Include realistic gaps in data to simulate real-world conditions
- Match sensor timestamps to truck assignment time windows

### 5. Realistic Patterns Implementation
- Temperature data with normal distributions per shipment type
- Intentional violations in 10% of shipments
- Realistic GPS routes for major Indian city pairs (Delhi-Mumbai, Bangalore-Chennai, etc.)
- GPS waypoints progressing logically over time
- Status transitions at realistic intervals based on shipment duration

### 6. Data Quality Assurance
- Use deterministic random seed (seed=42) for reproducibility
- Maintain referential integrity across all generated data
- Validate foreign key relationships before insertion
- Ensure no null values in critical fields
- Cross-check data distributions match specifications

### 7. Data Loading Scripts
- Create script to populate PostgreSQL tables
- Create script to generate IoT JSON files in proper format
- Implement batch insertion for performance
- Add validation checks after loading

## Success Criteria
- All tables populated with correct record counts
- Data distributions match technical specifications
- Referential integrity maintained (no orphan records)
- Temperature patterns realistic with appropriate violations
- GPS routes geographically accurate
- Status transitions follow logical progression
- IoT files created in correct format and structure
- Data generation is reproducible (same seed = same data)

## Dependencies
- Task 002 completed (PostgreSQL schema ready)
- Python environment with required libraries (Faker, pandas, numpy)

## Deliverables
- generate_sample_data.py master script
- Separate modules for each data type generation
- IoT JSON file generator
- Data validation scripts
- Documentation of data generation logic and distributions
- Sample output files for verification
