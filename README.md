# 📊 Reporting Pipeline - Hiring Data Analysis  

## **📌 Introduction**  
This project is a **data pipeline and reporting system** designed to process, store, analyze, and visualize hiring data. It enables **bulk data insertion**, **metric calculations**, **backups**, and **interactive visualizations**.  

The system is built with **FastAPI**, **PostgreSQL (Amazon RDS)**, and **AWS S3**, ensuring scalability and efficiency for handling large datasets.  

---

## **📌 Key Features**  

✔ **FastAPI-based REST API** for inserting, querying, and visualizing hiring data.  
✔ **PostgreSQL (RDS) Database** for structured storage and efficient querying.  
✔ **Data migration script** to transfer CSV data into the database.  
✔ **backup system** using AWS S3 (AVRO format).  
✔ **Data restore functionality** to recover hiring records.  
✔ **Visualization endpoints** to generate dynamic hiring trend charts.  
✔ **metrics endpoints** to generate  hiring metrics.  
✔ **Dockerized deployment** for easy setup and scalability.  

---

## **📌 Technology Stack**  

| **Component**   | **Technology Used** |
|---------------|-----------------|
| **Backend API** | FastAPI (Python) |
| **Database** | PostgreSQL (AWS RDS) |
| **Data Migration** | Pandas, AsyncPG |
| **Backup & Restore** | AVRO, AWS S3, Boto3 |
| **Data Visualization** | Matplotlib, Seaborn |
| **Deployment** | Docker, AWS EC2 |
| **Logging & Monitoring** | AWS CloudWatch |
 

---

## **📌 Prerequisites**  

Ensure the following dependencies are installed before proceeding:  

### **1️⃣ System Requirements**  
- **Operating System**: Linux / macOS / Windows (WSL Recommended)  
- **Python**: `3.8`  
- **Docker**: Installed and running  
- **Git**: Installed and configured  
- **AWS CLI**: Configured with access to AWS services  

### **Required Python Packages**  
This project uses **Pip and Virtual Environments** for package management.  

- `fastapi` - Web framework  
- `asyncpg` - Asynchronous PostgreSQL client  
- `pandas` - Data processing  
- `boto3` - AWS SDK for Python  
- `fastavro` - AVRO file handling  
- `matplotlib` & `seaborn` - Data visualization  




---

## **📌 Architecture Overview**  

The system follows a **modular design**, allowing efficient data processing and reporting.  

# 📊 Reporting Pipeline Architecture

## **Overview**
This document describes the architecture of the **Reporting Pipeline**, including its **components, interactions, and design decisions**.  

---

## **System Architecture**

```plaintext
                    +------------------------------------------------+
                    |             🖥️  User/Client                    |
                    | (Sends API requests via FastAPI)              |
                    +------------------------------------------------+
                                    |
                                    v
+--------------------------------------------------------------------------+
|                🚀 FASTAPI APPLICATION (EC2 + Docker)                     |
|--------------------------------------------------------------------------|
|  📌 API Endpoints                                                        |
|  - /insert (Insert Data)                                                 |
|  - /metrics/hired-employees-by-quarter (Hiring Metrics)                  |
|  - /metrics/departments-above-average-hiring (Dept Hiring Metrics)        |
|  - /visuals/hired-employees-by-quarter (Graph Visualization)              |
|  - /visuals/departments-above-average-hiring (Graph Visualization)        |
|                                                                          |
|  📌 Core Functionalities                                                 |
|  - Data Validation (Pydantic)                                            |
|  - Asynchronous DB Operations (AsyncPG)                                  |
|  - Logging & Monitoring (AWS CloudWatch)                                 |
|  - Environment Variables (.env)                                          |
|                                                                          |
|  📌 Backup & Restore Scripts (Executed from EC2)                         |
|  - backup.py → Extracts data → Converts to AVRO → Uploads to S3         |
|  - restore.py → Fetches from S3 → Converts AVRO → Inserts to DB         |
+--------------------------------------------------------------------------+
                                    |
                                    v
+--------------------------------------------------------------------------+
|                        🛢️ PostgreSQL Database (AWS RDS)                    |
|--------------------------------------------------------------------------|
|  📌 Database Tables                                                      |
|  - departments (id, department)                                          |
|  - jobs (id, job)                                                        |
|  - hired_employees (id, name, hire_datetime, department_id, job_id)      |
|                                                                          |
|  📌 Data Relationships                                                   |
|  - hired_employees references departments (department_id → id)           |
|  - hired_employees references jobs (job_id → id)                         |
|                                                                          |
|  📌 Performance Optimizations                                            |
|  - Indexing on foreign keys                                              |
|  - Optimized queries for analytics                                       |
+--------------------------------------------------------------------------+
                                    |
                                    v
+--------------------------------------------------------------------------+
|                         ☁️ AWS SERVICES                                   |
|--------------------------------------------------------------------------|
|  📌 Amazon S3 → Data Backup Storage                                     |
|  - Stores AVRO backups for recovery                                    |
|  - Used by backup.py & restore.py                                      |
|                                                                          |
|  📌 AWS CloudWatch → Logging & Monitoring                               |
|  - Logs FastAPI API requests & errors                                  |
|  - Logs backup & restore process errors                                |
+--------------------------------------------------------------------------+

```


