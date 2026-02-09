# Smart Logistics Tracking Lakehouse

A **Local-First Lakehouse** implementation for tracking logistics data, combining transactional records (PostgreSQL) with IoT sensor telemetry (JSON) using a Medallion Architecture (Bronze/Silver/Gold).

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB+ RAM allocated to Docker
- Python 3.9+ (for local script testing)

### Setup
1. **Configure Environment**
   ```bash
   # .env file is already created with defaults
   ```

2. **Start Infrastructure**
   ```bash
   docker-compose up -d
   ```
   *Wait ~3-5 minutes for all services to initialize.*

3. **Access Interfaces**
   - **Airflow UI:** [http://localhost:8090](http://localhost:8090) (User: `admin`, Pass: `admin`)
   - **Spark Master:** [http://localhost:8080](http://localhost:8080)
   - **Spark Worker:** [http://localhost:8081](http://localhost:8081)

## 📂 Project Structure
- `airflow/`: DAGs and orchestration config
- `spark/`: PySpark processing scripts
- `data/`: 
  - `delta-lake/`: Bronze/Silver/Gold pattern storage
  - `iot_raw/`: Input folder for JSON sensor files
  - `postgres/`: Persisted database data
- `tasks/`: Implementation task breakdown

## 🏗 Architecture
- **Source:** PostgreSQL (Orders/Shipments), IoT Files (Sensors)
- **Ingestion:** Spark (Raw -> Bronze)
- **Transformation:** Spark (Bronze -> Silver with SCD Type 2)
- **Aggregation:** Spark (Silver -> Gold with Analytics)
- **Orchestration:** Apache Airflow (LocalExecutor)

## 🛠 Tech Stack
- **Compute:** Apache Spark 3.5.0
- **Storage:** Delta Lake 3.0.0
- **Orchestration:** Apache Airflow 2.8.0
- **Database:** PostgreSQL 15
