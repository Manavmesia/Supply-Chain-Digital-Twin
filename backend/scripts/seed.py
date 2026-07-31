import asyncio
import os

# Add parent directory to path to resolve imports
import sys

import structlog
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, "")

from app.core.config import settings

logger = structlog.get_logger()


async def seed_database():
    logger.info("Starting database seeding...")

    # Locate the seed SQL file
    # If running from backend/ scripts, it will look up a level
    seed_file_path = "sql/03_seed.sql"
    if not os.path.exists(seed_file_path):
        seed_file_path = "../sql/03_seed.sql"

    if not os.path.exists(seed_file_path):
        logger.error("Could not find sql/03_seed.sql file!")
        return

    logger.info(f"Loading seed data from {seed_file_path}")
    with open(seed_file_path) as f:
        sql_content = f.read()

    # Create engine and execute statements
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.connect() as conn:
            # Get underlying raw asyncpg connection
            raw_conn = await conn.get_raw_connection()
            # asyncpg connection execute runs multi-statement scripts natively
            await raw_conn.driver_connection.execute(sql_content)
            logger.info("Database seeding completed successfully!")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
