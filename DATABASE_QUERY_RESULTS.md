# Database Query Results 📊
## Smart Logistics Database - Current State

---

## 📋 **All Tables in Database**

| Schema | Table Name |
|--------|------------|
| logistics | customers |
| logistics | drivers |
| logistics | orders |
| logistics | shipment_types |
| logistics | shipments |
| logistics | truck_assignments |
| logistics | vehicles |
| logistics | warehouses |

**Total: 8 Tables**

---

## 📊 **Row Counts by Table**

| Table Name | Row Count |
|------------|-----------|
| **orders** | 150 |
| **shipments** | 100 |
| **truck_assignments** | 85 |
| **vehicles** | 50 |
| **customers** | 50 |
| **drivers** | 30 |
| **shipment_types** | 6 |
| **warehouses** | 4 |

**Total Records: 475 rows**

---

## 📦 **Shipment Status Breakdown**

| Status | Count | Percentage |
|--------|-------|------------|
| **Delivered** | 52 | 52.00% |
| **In Transit** | 19 | 19.00% |
| **Out for Delivery** | 9 | 9.00% |
| **Created** | 8 | 8.00% |
| **Cancelled** | 7 | 7.00% |
| **Assigned** | 5 | 5.00% |

**Total Shipments: 100**

---

## 🗃️ **Shipments Table Structure**

| Column Name | Type | Description |
|-------------|------|-------------|
| shipment_id | UUID/ID | Unique shipment identifier |
| order_id | UUID/ID | Link to order |
| origin_warehouse_id | UUID/ID | Where it started |
| destination_city | String | Where it's going |
| shipment_type | String | Type (Refrigerated, Perishable, etc.) |
| status | String | Current status |
| expected_delivery_date | Timestamp | When it should arrive |
| actual_delivery_date | Timestamp | When it actually arrived |
| created_at | Timestamp | When created |
| updated_at | Timestamp | Last update |

---

## 👥 **Customers Table Structure**

| Column Name | Type |
|-------------|------|
| customer_id | UUID/ID |
| name | String |
| email | String |
| phone | String |
| address | String |
| city | String |
| created_at | Timestamp |

---

## 🔍 **Sample Queries You Can Run**

### **1. View All Shipments By Status**
```powershell
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT status, COUNT(*) FROM logistics.shipments GROUP BY status;"
```

### **2. View Recent Shipments**
```powershell
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT shipment_id, status, shipment_type, destination_city FROM logistics.shipments ORDER BY created_at DESC LIMIT 20;"
```

### **3. View All Customers**
```powershell
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT customer_id, name, email, city FROM logistics.customers LIMIT 20;"
```

### **4. View All Drivers**
```powershell
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT * FROM logistics.drivers LIMIT 20;"
```

### **5. View All Vehicles**
```powershell
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT * FROM logistics.vehicles LIMIT 20;"
```

### **6. View Shipment Types**
```powershell
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT * FROM logistics.shipment_types;"
```

### **7. Join Shipments with Customers**
```powershell
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT s.shipment_id, s.status, s.destination_city, c.name as customer_name FROM logistics.shipments s JOIN logistics.orders o ON s.order_id = o.order_id JOIN logistics.customers c ON o.customer_id = c.customer_id LIMIT 10;"
```

---

## 📈 **Database Summary**

✅ **Database Name**: postgres  
✅ **Schema**: logistics  
✅ **Total Tables**: 8  
✅ **Total Records**: 475+  
✅ **Main Data**:
- 50 Customers
- 150 Orders  
- 100 Shipments
- 30 Drivers
- 50 Vehicles
- 85 Truck Assignments

---

## 🎯 **Quick Access Commands**

### **Connect Interactively**
```powershell
docker exec -it assignment4-postgres-1 psql -U admin -d postgres
```

Then inside PostgreSQL:
```sql
SET search_path TO logistics;
\dt                           -- List tables
\d shipments                  -- Describe shipments table
SELECT * FROM shipments LIMIT 5;
\q                            -- Exit
```

### **One-Line Queries**
```powershell
# Quick count
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT COUNT(*) FROM logistics.shipments;"

# Status summary
docker exec assignment4-postgres-1 psql -U admin -d postgres -c "SELECT status, COUNT(*) FROM logistics.shipments GROUP BY status;"
```

---

**All queries executed successfully!** ✅

Your database is fully populated and ready to use!
