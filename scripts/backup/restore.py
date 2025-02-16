import asyncio
import fastavro
import pandas as pd
import os
import sys
import logging
from datetime import datetime
from utils import get_db_connection, download_from_s3
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(env_path)

logger = logging.getLogger(__name__)

VALID_TABLES = {"departments", "jobs", "hired_employees"}


async def restore_table(table_name):
    """Restores a specific table from its AVRO backup in S3."""
    logger.info(f"Starting restore for table: {table_name}")

    if table_name not in VALID_TABLES:
        logger.error(
            f"Invalid table name: {table_name}. Allowed: {VALID_TABLES}")
        return

    # Download the AVRO file from S3
    local_file = f"{table_name}_backup.avro"
    download_success = download_from_s3(table_name, local_file)

    if not download_success:
        logger.error(f"No backup found for {table_name}, skipping restore.")
        return

    try:
        with open(local_file, "rb") as f:
            reader = fastavro.reader(f)
            records = [record for record in reader]

        if not records:
            logger.warning(
                f"No data in {table_name}_backup.avro, skipping restore.")
            return

        df = pd.DataFrame(records)
        logger.info(
            f"Loaded {len(df)} records from {table_name}_backup.avro")

    except Exception as e:
        logger.error(f"Failed to read AVRO file {local_file}: {e}")
        return

    # Convert `hire_datetime` to datetime object
    if "hire_datetime" in df.columns:
        # Ensure all datetimes are parsed correctly (removes 'Z' and applies UTC)
        df["hire_datetime"] = df["hire_datetime"].str.replace(
            "Z", "", regex=False)
        df["hire_datetime"] = pd.to_datetime(
            df["hire_datetime"], format="%Y-%m-%dT%H:%M:%S%z", utc=True)
        logger.info(f"Converted hire_datetime to datetime object")

    conn = await get_db_connection()
    try:
        # Generate SQL query dynamically
        columns = ", ".join(df.columns)
        values_placeholder = ", ".join(
            [f"${i+1}" for i in range(len(df.columns))])
        conflict_clause = ", ".join(
            [f"{col}=EXCLUDED.{col}" for col in df.columns])

        sql_query = f"""
        INSERT INTO {table_name} ({columns})
        VALUES ({values_placeholder})
        ON CONFLICT (id) DO UPDATE SET {conflict_clause};
        """

        await conn.executemany(sql_query, df.itertuples(index=False, name=None))
        logger.info(
            f"Successfully restored {len(df)} records into {table_name}")
        os.remove(f"{table_name}_backup.avro")
        logger.info(f"Deleted local file: {table_name}_backup.avro")

    except Exception as e:
        logger.error(f"Restore failed for {table_name}: {e}")

    finally:
        await conn.close()
        logger.info(f"Database connection closed for table {table_name}")


async def main():
    """Runs the restore process for a specific table passed via command line."""
    if len(sys.argv) < 2:
        logger.error(
            "No table name provided. Usage: python restore.py <table_name>")
        return

    table_name = sys.argv[1]
    await restore_table(table_name)


if __name__ == "__main__":
    asyncio.run(main())
