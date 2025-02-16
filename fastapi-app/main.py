from fastapi import FastAPI, HTTPException, Depends
from models.request import InsertRequest
from models.response import InsertResponse
import asyncpg
import traceback
from datetime import datetime
from dotenv import load_dotenv
import logging
import os

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

app = FastAPI()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def get_db():
    conn = await asyncpg.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        yield conn
    finally:
        await conn.close()

TABLE_SCHEMAS = {
    "departments": ["department"],
    "jobs": ["job"],
    "hired_employees": ["name", "hire_datetime", "department_id", "job_id"],
}


@app.get("/")
async def home():
    return {
        "message": "Welcome to the Reporting API! refer to the /docs endpoint for more info",
        "status": "running",
        "endpoints": [
            "/insert",
            "/metrics/hired-employees-by-quarter",
            "/metrics/departments-above-average-hiring",
            "/docs",
        ]
    }


@app.post("/insert", response_model=InsertResponse)
async def insert_data(request: InsertRequest, db=Depends(get_db)):
    try:
        if request.table not in TABLE_SCHEMAS:
            raise HTTPException(status_code=400, detail="Invalid table name")

        required_fields = TABLE_SCHEMAS[request.table]
        valid_records = []
        failed_records = []

        async with db.transaction():  # SOne transaction for all inserts
            for record in request.data:
                if not all(field in record for field in required_fields):
                    failed_records.append(record)
                    continue

                # Validate `department_id` and `job_id` for `hired_employees`
                if request.table == "hired_employees":
                    try:
                        record["hire_datetime"] = datetime.fromisoformat(
                            record["hire_datetime"].replace("Z", "+00:00"))
                    except ValueError:
                        failed_records.append(record)
                        continue

                    dep_exists = await db.fetchval("SELECT COUNT(*) FROM departments WHERE id = $1", record["department_id"])
                    job_exists = await db.fetchval("SELECT COUNT(*) FROM jobs WHERE id = $1", record["job_id"])

                    if dep_exists == 0 or job_exists == 0:
                        failed_records.append(record)
                        continue

                valid_records.append(record)

            if valid_records:
                for record in valid_records:
                    columns = ", ".join(required_fields)
                    values_placeholders = ", ".join(
                        f"${i+1}" for i in range(len(required_fields)))
                    sql_query = f"INSERT INTO {request.table} ({columns}) VALUES ({values_placeholders}) RETURNING id"
                    inserted_id = await db.fetchval(sql_query, *tuple(record[field] for field in required_fields))

                    logger.info(f"Inserted record with ID: {inserted_id}")

        return {
            "success": True if valid_records else False,
            "message": f"{len(valid_records)} records inserted into {request.table}",
            "failed_records": failed_records
        }

    except Exception as e:
        error_message = f"Internal Server Error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/metrics/hired-employees-by-quarter")
async def get_hired_employees_by_quarter(db: asyncpg.Connection = Depends(get_db)):
    """Returns the number of employees hired per job and department in 2021, grouped by quarter."""

    query = """
    SELECT 
        d.department AS department, 
        j.job AS job, 
        COUNT(CASE WHEN EXTRACT(QUARTER FROM he.hire_datetime) = 1 THEN 1 END) AS Q1,
        COUNT(CASE WHEN EXTRACT(QUARTER FROM he.hire_datetime) = 2 THEN 1 END) AS Q2,
        COUNT(CASE WHEN EXTRACT(QUARTER FROM he.hire_datetime) = 3 THEN 1 END) AS Q3,
        COUNT(CASE WHEN EXTRACT(QUARTER FROM he.hire_datetime) = 4 THEN 1 END) AS Q4
    FROM hired_employees he
    JOIN departments d ON he.department_id = d.id
    JOIN jobs j ON he.job_id = j.id
    WHERE EXTRACT(YEAR FROM he.hire_datetime) = 2021
    GROUP BY d.department, j.job
    ORDER BY d.department ASC, j.job ASC;
    """

    try:
        logger.info("Executing query to fetch hired employees by quarter")
        results = await db.fetch(query)
        logger.info(
            f"Query executed successfully, retrieved {len(results)} records")
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {"error": "Internal Server Error"}


@app.get("/metrics/departments-above-average-hiring")
async def get_departments_above_average(db: asyncpg.Connection = Depends(get_db)):
    """Returns departments that hired more employees than the 2021 average."""

    query = """
    WITH department_hiring AS (
        SELECT 
            he.department_id AS id, 
            d.department, 
            COUNT(he.id) AS hired
        FROM hired_employees he
        JOIN departments d ON he.department_id = d.id
        WHERE EXTRACT(YEAR FROM he.hire_datetime) = 2021
        GROUP BY he.department_id, d.department
    ),
    average_hiring AS (
        SELECT AVG(hired) AS avg_hires FROM department_hiring
    )
    SELECT 
        dh.id, 
        dh.department, 
        dh.hired
    FROM department_hiring dh
    JOIN average_hiring ah ON dh.hired > ah.avg_hires
    ORDER BY dh.hired DESC;
    """

    try:
        logger.info(
            "Executing query to fetch departments with above-average hiring")
        results = await db.fetch(query)
        logger.info(
            f"Query executed successfully, retrieved {len(results)} records")
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {"error": "Internal Server Error"}
