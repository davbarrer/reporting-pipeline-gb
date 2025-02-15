import asyncio
import logging
from utils import fetch_table_data, save_as_avro, upload_to_s3

logger = logging.getLogger(__name__)

TABLES = ["departments", "jobs", "hired_employees"]


async def backup_table(table_name):
    logger.info(f"Starting backup for table: {table_name}")

    df = await fetch_table_data(table_name)
    if df.empty:
        return

    avro_file = save_as_avro(df, table_name)
    if not avro_file:
        return

    upload_to_s3(avro_file, table_name)


async def main():
    """Runs backup for all tables."""
    logger.info("Starting full database backup process...")
    await asyncio.gather(*(backup_table(table) for table in TABLES))
    logger.info("Backup process completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
