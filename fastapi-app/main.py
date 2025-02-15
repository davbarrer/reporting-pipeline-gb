from fastapi import FastAPI, HTTPException, Depends
from models.request import InsertRequest
from models.response import InsertResponse
import asyncpg
import traceback
from datetime import datetime
from dotenv import load_dotenv
import os

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

app = FastAPI()

# Database Connection Settings
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Dependency: Get Database Connection (Auto-Close After Request)


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

                    print(f"Inserted record with ID: {inserted_id}")

        return {
            "success": True if valid_records else False,
            "message": f"{len(valid_records)} records inserted into {request.table}",
            "failed_records": failed_records
        }

    except Exception as e:
        error_message = f"Internal Server Error: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/")
def home():
    return {"message": "FastAPI on EC2 is working yes sir!"}
