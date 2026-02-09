# Task 001: Project Setup and Infrastructure

## Objective
Set up the foundational project structure, Docker environment, and core infrastructure components for the Smart Logistics Tracking Lakehouse.

## Scope

### 1. Project Directory Structure
- Create complete directory hierarchy for the project
- Set up folders for Airflow, Spark, data storage, scripts, and documentation
- Organize delta-lake storage directories (bronze, silver, gold)
- Create directories for IoT raw data ingestion and PostgreSQL data volumes

### 2. Docker Compose Configuration
- Configure PostgreSQL service (postgres:15 image)
- Configure Spark cluster (master and worker nodes using bitnami/spark:3.5.0)
- Configure Airflow services (webserver, scheduler, init using apache/airflow:2.8.0)
- Set up service dependencies and networking
- Configure volume mounts for persistent storage
- Define resource allocation (memory, CPU) for each service
- Set up environment variables and secrets management

### 3. Environment Configuration
- Create `.env` file with all required environment variables
- Configure database credentials (PostgreSQL user, password, database name)
- Set Airflow configuration (executor type, connections, fernet key)
- Configure Spark settings (master URL, worker resources)
- Define Delta Lake storage paths

### 4. Docker Network and Volumes
- Create Docker network for service communication
- Define persistent volumes for PostgreSQL data
- Define volumes for Delta Lake storage
- Set up volumes for Airflow DAGs, logs, and plugins
- Configure volumes for Spark scripts and logs

### 5. Dependencies and Libraries
- List required Python packages (PySpark, Delta Lake, Faker, pandas, etc.)
- Specify Spark-Delta Lake JAR dependencies
- Configure Airflow requirements.txt
- Set up requirements for data generation scripts

## Success Criteria
- All project directories created with proper structure
- Docker Compose file validates successfully
- All services defined with correct images and versions
- Environment variables properly configured
- Volume mounts correctly defined
- Ready for docker-compose up command

## Dependencies
- Docker Desktop installed and running
- WSL2 enabled (for Windows)
- At least 8GB RAM available for Docker
- 20GB free disk space

## Deliverables
- Complete directory structure
- docker-compose.yml file
- .env file (with placeholders)
- .gitignore file
- requirements.txt for Python dependencies
- README.md with setup prerequisites
