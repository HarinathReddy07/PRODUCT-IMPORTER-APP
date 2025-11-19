"""
Database initialization script.
Run this script to create all database tables.
"""
from models import init_db, create_tables
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Initializing database connection...")
        init_db()
        logger.info("Creating database tables...")
        create_tables()
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

