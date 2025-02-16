import boto3
import pandas as pd
import psycopg2
import io
import os
import logging
import watchtower
from dotenv import load_dotenv
import os

env_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(env_path)

S3_BUCKET = "data-pipeline-migration-gb"
CLOUDWATCH_LOG_GROUP = "data-migration-logs"

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

s3_client = boto3.client("s3")
cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group=CLOUDWATCH_LOG_GROUP)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),        # Log to console
        cloudwatch_handler              # Send logs to CloudWatch
    ]
)

FILES = {
    "departments": "departments.csv",
    "jobs": "jobs.csv",
    "hired_employees": "hired_employees.csv"
}


def read_csv_from_s3(file_key, column_names):
    """Read CSV file from S3 into a Pandas DataFrame with predefined column names"""
    logging.info(f"Downloading {file_key} from S3...")
    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=file_key)
    df = pd.read_csv(io.BytesIO(obj["Body"].read()),
                     encoding="utf-8", names=column_names)
    logging.info(
        f"Successfully loaded {file_key} into DataFrame with {len(df)} records.")
    return df


def validate_data(data, table_name):
    """Validate data: check for missing values and log rejected rows"""
    logging.info(f"Validating data for {table_name}...")
    if data.isnull().values.any():
        failed_rows = data[data.isnull().any(axis=1)]
        failed_rows.to_csv("failed_records.log", mode="a",
                           header=False, index=False)
        logging.warning(
            f"{len(failed_rows)} invalid rows found in {table_name}. Logged to failed_records.log.")
        data = data.dropna()
    logging.info(
        f"Validation complete for {table_name}. {len(data)} valid records remain.")
    return data


def insert_data(cursor, table_name, data):
    """Insert data into PostgreSQL in batches"""
    if data.empty:
        logging.warning(
            f"No valid data to insert for {table_name}. Skipping...")
        return

    columns = ", ".join(data.columns)
    placeholders = ", ".join(["%s"] * len(data.columns))
    insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    batch_size = 500
    for i in range(0, len(data), batch_size):
        batch = [tuple(row) for row in data.iloc[i:i+batch_size].to_numpy()]
        cursor.executemany(insert_query, batch)
        logging.info(f"Inserted {len(batch)} records into {table_name}.")


def upload_log_to_s3(log_file, s3_key):
    """Uploads a log file to S3 and deletes it after upload"""
    if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
        try:
            s3_client.upload_file(log_file, S3_BUCKET, s3_key)
            logging.info(f"Log file uploaded to s3://{S3_BUCKET}/{s3_key}")
            os.remove(log_file)
        except Exception as e:
            logging.error(f"Failed to upload {log_file} to S3: {e}")


def migrate():
    """Migrate data from S3 to PostgreSQL securely and upload logs"""
    conn = None
    try:
        logging.info("Starting data migration...")
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )
        cursor = conn.cursor()
        logging.info(
            f"Connected to PostgreSQL at {DB_HOST}:{DB_PORT}, Database: {DB_NAME}")

        # Load, validate, and insert departments
        logging.info("Migrating departments...")
        departments_df = read_csv_from_s3(
            FILES["departments"], ["id", "department"])
        departments_df = validate_data(departments_df, "departments")
        insert_data(cursor, "departments", departments_df)

        # Load, validate, and insert jobs
        logging.info("Migrating jobs...")
        jobs_df = read_csv_from_s3(FILES["jobs"], ["id", "job"])
        jobs_df = validate_data(jobs_df, "jobs")
        insert_data(cursor, "jobs", jobs_df)

        # Load, validate, and insert hired employees
        logging.info("Migrating hired employees...")
        hired_df = read_csv_from_s3(FILES["hired_employees"], [
                                    "id", "name", "hire_datetime", "department_id", "job_id"])
        hired_df = validate_data(hired_df, "hired_employees")
        insert_data(cursor, "hired_employees", hired_df)

        conn.commit()
        logging.info("Migration completed successfully!")

    except Exception as e:
        logging.error(f"Migration failed: {e}")

    finally:
        if conn is not None:
            conn.close()
            logging.info("Connection closed.")

        upload_log_to_s3("failed_records.log", "logs/failed_records.log")


if __name__ == "__main__":
    migrate()
