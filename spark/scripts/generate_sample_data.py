import os
import random
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import psycopg2
from faker import Faker
import uuid

# Configuration
DB_HOST = "postgres" # Connect to postgres service within Docker network
DB_PORT = "5432"
DB_NAME = "postgres"  # Fixed: use postgres database, not smart_logistics
DB_USER = "admin"
DB_PASSWORD = "password"
IOT_DATA_DIR = "./data/iot_raw"
SEED = 42

fake = Faker('en_IN')
Faker.seed(SEED)
random.seed(SEED)
np.random.seed(SEED)

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def generate_customers(n=50):
    customers = []
    for _ in range(n):
        customers.append({
            'name': fake.name(),
            'email': fake.unique.email(),
            'phone': fake.unique.phone_number()[:20],
            'address': fake.address(),
            'city': fake.city()
        })
    return pd.DataFrame(customers)

def generate_vehicles(n=50):
    vehicles = []
    types = ['Refrigerated Truck', 'Standard Truck', 'Van']
    states = ['DL', 'MH', 'KA', 'TN', 'WB', 'UP']
    
    for _ in range(n):
        v_type = np.random.choice(types, p=[0.4, 0.4, 0.2])
        plate = f"{random.choice(states)}-{random.randint(1,99):02d}-{chr(random.randint(65,90))}{chr(random.randint(65,90))}-{random.randint(1000,9999)}"
        vehicles.append({
            'license_plate': plate,
            'vehicle_type': v_type,
            'capacity_kg': random.choice([1000, 3000, 5000, 10000]),
            'has_refrigeration': v_type == 'Refrigerated Truck',
            'status': np.random.choice(['AVAILABLE', 'IN_TRANSIT', 'MAINTENANCE'], p=[0.1, 0.8, 0.1])
        })
    return pd.DataFrame(vehicles)

def generate_drivers(n=30):
    drivers = []
    for _ in range(n):
        drivers.append({
            'name': fake.name(),
            'phone_number': fake.unique.phone_number()[:20],
            'license_number': f"LIC-{fake.unique.bothify(text='??#####')}",
            'status': np.random.choice(['ACTIVE', 'INACTIVE'], p=[0.9, 0.1]),
            'rating': round(random.uniform(3.5, 5.0), 1)
        })
    return pd.DataFrame(drivers)

def generate_orders_and_shipments(conn, n_orders=150, n_shipments=100):
    # Fetch existing IDs
    cur = conn.cursor()
    cur.execute("SELECT customer_id FROM logistics.customers")
    customer_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT warehouse_id FROM logistics.warehouses")
    warehouse_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT type_name FROM logistics.shipment_types")
    shipment_types = [r[0] for r in cur.fetchall()]
    cur.close()

    orders = []
    shipments = []
    assignments = []
    
    start_date = datetime.now() - timedelta(days=14)
    
    # Generate Orders
    for _ in range(n_orders):
        o_id = f"ORD-{fake.unique.bothify(text='??####')}"
        orders.append({
            'order_id': o_id,
            'customer_id': random.choice(customer_ids),
            'order_date': fake.date_time_between(start_date=start_date, end_date='now'),
            'total_amount': round(random.uniform(5000, 50000), 2),
            'priority': random.choice(['STANDARD', 'EXPRESS']),
            'status': 'PROCESSING'
        })

    orders_df = pd.DataFrame(orders)
    
    # Generate Shipments linked to orders
    used_orders = random.sample(orders, n_shipments)
    
    cities = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Pune', 'Hyderabad', 'Ahmedabad']
    statuses = ['Delivered', 'In Transit', 'Out for Delivery', 'Assigned', 'Created', 'Cancelled']
    status_weights = [0.5, 0.15, 0.12, 0.08, 0.05, 0.10] # 50% Delivered, Sum = 1.0

    for order in used_orders:
        s_id = f"SHP-{fake.unique.bothify(text='??####')}"
        s_type = np.random.choice(shipment_types)
        status = np.random.choice(statuses, p=status_weights)
        origin = random.choice(warehouse_ids)
        dest = random.choice(cities)
        
        create_time = order['order_date'] + timedelta(hours=random.randint(1, 24))
        
        expected_delivery = create_time + timedelta(days=random.randint(1, 5))
        actual_delivery = None
        if status == 'Delivered':
            actual_delivery = expected_delivery + timedelta(hours=random.randint(-12, 24))
        
        shipments.append({
            'shipment_id': s_id,
            'order_id': order['order_id'],
            'origin_warehouse_id': origin,
            'destination_city': dest,
            'shipment_type': s_type,
            'status': status,
            'expected_delivery_date': expected_delivery,
            'actual_delivery_date': actual_delivery,
            'created_at': create_time
        })

    return pd.DataFrame(orders_df), pd.DataFrame(shipments)

def assign_trucks(conn, shipments_df):
    cur = conn.cursor()
    cur.execute("SELECT vehicle_id, has_refrigeration FROM logistics.vehicles")
    vehicles = cur.fetchall() # List of (id, bool)
    
    cur.execute("SELECT driver_id FROM logistics.drivers WHERE status='ACTIVE'")
    driver_ids = [r[0] for r in cur.fetchall()]
    cur.close()
    
    assignments = []
    
    # Needs matching: Refrigerated shipments need refrigerated trucks
    ref_trucks = [v[0] for v in vehicles if v[1]]
    std_trucks = [v[0] for v in vehicles] # Standard can perform non-ref jobs, or ref can too
    
    for _, row in shipments_df.iterrows():
        if row['status'] in ['Created', 'Cancelled']:
            continue
            
        shipment_type = row['shipment_type']
        is_cold = shipment_type in ['Refrigerated', 'Frozen', 'Pharmaceutical']
        
        # Pick truck
        if is_cold:
            if not ref_trucks: continue
            truck_id = random.choice(ref_trucks)
        else:
            truck_id = random.choice(std_trucks)
            
        driver_id = random.choice(driver_ids)
        
        start_time = row['created_at'] + timedelta(hours=4) # Assignment time
        end_time = row['actual_delivery_date'] if row['status'] == 'Delivered' else None
        
        assignments.append({
            'shipment_id': row['shipment_id'],
            'vehicle_id': truck_id,
            'driver_id': driver_id,
            'assignment_start_time': start_time,
            'assignment_end_time': end_time,
            'status': 'COMPLETED' if end_time else 'ACTIVE',
            'shipment_type': shipment_type # Used for generating IoT data later
        })
        
    return pd.DataFrame(assignments)

def generate_iot_data(assignments_df):
    if not os.path.exists(IOT_DATA_DIR):
        os.makedirs(IOT_DATA_DIR)
        
    readings_total = 0
    errors_count = 0
    
    print(f"Generating IoT data for {len(assignments_df)} trips...")
    
    for idx, trip in assignments_df.iterrows():
        try:
            # Validate vehicle_id first
            if pd.isna(trip['vehicle_id']):
                continue
            
            vehicle_id = int(float(trip['vehicle_id']))  # Convert via float first
            
            # Validate timestamps
            start = trip['assignment_start_time']
            if pd.isna(start):
                continue
                
            # Handle end time properly
            end = trip['assignment_end_time']
            if pd.isna(end) or end is None:
                end = datetime.now()
            
            # Calculate duration
            duration_hours = (end - start).total_seconds() / 3600
            if duration_hours < 1: 
                duration_hours = 1
            
            # Generate readings
            num_readings = int(duration_hours * 2)
            if num_readings > 100: 
                num_readings = 100
            if num_readings < 5: 
                num_readings = 5
            
            timestamps = [start + timedelta(minutes=i*30) for i in range(num_readings)]
            
            # Temperature profile
            s_type = str(trip['shipment_type'])
            target_temp = 20.0
            
            if s_type == 'Refrigerated': 
                target_temp = 5.0
            elif s_type == 'Frozen': 
                target_temp = -20.0
            elif s_type == 'Pharmaceutical': 
                target_temp = 4.0
            elif s_type == 'Perishable': 
                target_temp = 2.0
            
            # Introduce failures in 10%
            has_failure = random.random() < 0.1
            
            readings = []
            lat, lon = 28.7041, 77.1025
            
            for ts in timestamps:
                lat -= 0.05
                lon -= 0.03
                
                current_temp = np.random.normal(target_temp, 0.5)
                
                if has_failure and ts > (start + timedelta(hours=duration_hours/2)):
                    current_temp += random.uniform(5, 15)
                
                reading = {
                    "truck_id": vehicle_id,
                    "timestamp": ts.isoformat(),
                    "temperature": round(float(current_temp), 2),
                    "latitude": round(float(lat), 6),
                    "longitude": round(float(lon), 6)
                }
                readings.append(reading)
            
            # Save to file
            if readings:
                filename = f"truck_{vehicle_id}_{start.strftime('%Y%m%d%H%M')}.json"
                filepath = os.path.join(IOT_DATA_DIR, filename)
                with open(filepath, 'w') as f:
                    json.dump(readings, f)
                
                readings_total += len(readings)
        
        except Exception as e:
            errors_count += 1
            print(f"Warning: Skipped trip due to error: {str(e)}")
            continue
    
    print(f"Successfully generated {readings_total} readings with {errors_count} skipped trips.")
    return readings_total

def main():
    print("Connecting to DB...")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect. Exiting.")
        return

    try:
        cur = conn.cursor()
        
        print("Generating Customers...")
        cust_df = generate_customers()
        for _, r in cust_df.iterrows():
            cur.execute("INSERT INTO logistics.customers (name, email, phone, address, city) VALUES (%s, %s, %s, %s, %s)",
                       (r['name'], r['email'], r['phone'], r['address'], r['city']))
        
        print("Generating Drivers...")
        drv_df = generate_drivers()
        for _, r in drv_df.iterrows():
            cur.execute("INSERT INTO logistics.drivers (name, phone_number, license_number, status, rating) VALUES (%s, %s, %s, %s, %s)",
                       (r['name'], r['phone_number'], r['license_number'], r['status'], r['rating']))

        print("Generating Vehicles...")
        veh_df = generate_vehicles()
        for _, r in veh_df.iterrows():
            cur.execute("INSERT INTO logistics.vehicles (license_plate, vehicle_type, capacity_kg, has_refrigeration, status) VALUES (%s, %s, %s, %s, %s)",
                       (r['license_plate'], r['vehicle_type'], r['capacity_kg'], r['has_refrigeration'], r['status']))
        
        conn.commit() # Commit parents first

        print("Generating Orders & Shipments...")
        ord_df, shp_df = generate_orders_and_shipments(conn)
        
        for _, r in ord_df.iterrows():
            cur.execute("INSERT INTO logistics.orders (order_id, customer_id, order_date, total_amount, priority, status) VALUES (%s, %s, %s, %s, %s, %s)",
                       (r['order_id'], r['customer_id'], r['order_date'], r['total_amount'], r['priority'], r['status']))
            
        for _, r in shp_df.iterrows():
            actual_delivery = r['actual_delivery_date']
            if pd.isna(actual_delivery): # Handles NaT and None
                actual_delivery = None
                
            cur.execute("""INSERT INTO logistics.shipments 
                        (shipment_id, order_id, origin_warehouse_id, destination_city, shipment_type, status, expected_delivery_date, actual_delivery_date, created_at) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                       (r['shipment_id'], r['order_id'], r['origin_warehouse_id'], r['destination_city'], r['shipment_type'], r['status'], 
                        r['expected_delivery_date'], actual_delivery, r['created_at']))

        print("Generating Truck Assignments...")
        assign_df = assign_trucks(conn, shp_df)
        for _, r in assign_df.iterrows():
            end_time = r['assignment_end_time']
            if pd.isna(end_time):
                end_time = None
                
            cur.execute("""INSERT INTO logistics.truck_assignments 
                        (shipment_id, vehicle_id, driver_id, assignment_start_time, assignment_end_time, status) 
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                       (r['shipment_id'], r['vehicle_id'], r['driver_id'], r['assignment_start_time'], end_time, r['status']))

        conn.commit()
        print("Transactional Data Loaded!")
        
        print("Generating IoT Sensor Data...")
        total_readings = generate_iot_data(assign_df)
        print(f"Generated {total_readings} sensor readings in JSON files.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
