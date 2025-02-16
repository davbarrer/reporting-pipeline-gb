import asyncpg
import boto3
import fastavro
import pandas as pd
import os
import logging
import watchtower
from datetime import datetime
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(env_path)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = "data-pipeline-backup-gb"

LOG_GROUP = "data-backup-logs"
LOG_STREAM = f"backup-script-{datetime.today().strftime('%Y-%m-%d')}"

cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group=LOG_GROUP)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),        # Log to console
        cloudwatch_handler              # Send logs to CloudWatch
    ]
)
logger = logging.getLogger(__name__)


async def get_db_connection():
    try:
        conn = await asyncpg.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        logger.info("Successfully connected to the PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


async def fetch_table_data(table_name):
    """Fetches all data from a given PostgreSQL table and ensures correct column names."""
    conn = None
    try:
        conn = await get_db_connection()

        # Fetch column names first
        col_query = f"""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = '{table_name}' ORDER BY ordinal_position
        """
        col_rows = await conn.fetch(col_query)
        columns = [row["column_name"]
                   for row in col_rows]

        if not columns:
            logger.error(
                f"No columns found for {table_name}. Check table name.")
            return pd.DataFrame()

        # Fetch actual data
        query = f"SELECT * FROM {table_name}"
        rows = await conn.fetch(query)

        if not rows:
            logger.warning(
                f"No data found in {table_name}. Skipping backup.")
            return pd.DataFrame()

        # Convert data to DataFrame with correct column names
        df = pd.DataFrame(rows, columns=columns)

        logger.info(
            f"Successfully fetched {len(df)} rows from {table_name}.")

        return df
    except Exception as e:
        logger.error(f"Failed to fetch data from {table_name}: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            await conn.close()
            logger.info(
                f"Database connection closed for table {table_name}.")


def save_as_avro(df, table_name):
    """Converts a Pandas DataFrame into an AVRO file with correct data types."""
    if df.empty:
        logger.warning(
            f"No data found in table {table_name}, skipping backup.")
        return None

    avro_filename = f"{table_name}_backup.avro"

    dtype_mapping = {
        "int64": "int",
        "float64": "float",
        "bool": "boolean",
        # Ensure datetime columns are stored as string
        "datetime64[ns]": "string",
        "object": "string"
    }

    # Convert datetime columns to proper ISO format
    if "hire_datetime" in df.columns:
        df["hire_datetime"] = df["hire_datetime"].astype(
            str)  # Force conversion to string
        df["hire_datetime"] = df["hire_datetime"].apply(
            lambda x: x.replace(" ", "T") + "Z")  # Ensure correct ISO 8601 format

    schema = {
        "type": "record",
        "name": table_name,
        "fields": [
            {"name": col, "type": dtype_mapping.get(
                str(df[col].dtype), "string")}
            for col in df.columns
        ]
    }

    records = df.to_dict(orient="records")

    try:
        with open(avro_filename, "wb") as out_file:
            fastavro.writer(out_file, schema, records)
        logger.info(f"AVRO file created: {avro_filename}")
        return avro_filename
    except Exception as e:
        logger.error(f"Failed to create AVRO file for {table_name}: {e}")
        return None


def upload_to_s3(file_path, table_name):
    if file_path is None:
        return

    try:
        s3_client = boto3.client(
            "s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
        s3_filename = f"{table_name}_backup.avro"

        s3_client.upload_file(file_path, S3_BUCKET, s3_filename)
        logger.info(
            f"Uploaded {file_path} to s3://{S3_BUCKET}/{s3_filename}")

        os.remove(file_path)
        logger.info(f"Deleted local file: {file_path}")

    except Exception as e:
        logger.error(f"Failed to upload {file_path} to S3: {e}")


def download_from_s3(table_name, local_path):
    try:
        s3_client = boto3.client(
            "s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
        s3_filename = f"{table_name}_backup.avro"

        s3_client.download_file(S3_BUCKET, s3_filename, local_path)
        logger.info(f"Downloaded {s3_filename} from S3 to {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Failed to download {s3_filename}: {e}")
        return None
