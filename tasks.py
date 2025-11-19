"""
Celery tasks for asynchronous processing.
"""
import csv
import io
from typing import Dict, List, Any
from celery import Task
from celery_app import celery_app
from models import Product, Base, SessionLocal, init_db
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
def get_webhook_utils():
    """Lazy import webhook utilities."""
    from webhook_utils import trigger_webhooks
    return trigger_webhooks


class ProgressTask(Task):
    """
    Custom task class that tracks progress.
    """
    _progress = 0
    _status = "pending"
    _message = ""

    def update_progress(self, progress: int, status: str = None, message: str = None):
        """Update task progress."""
        self._progress = progress
        if status:
            self._status = status
        if message:
            self._message = message
        self.update_state(
            state="PROGRESS",
            meta={"progress": progress, "status": self._status, "message": self._message}
        )

    @property
    def progress(self):
        return self._progress

    @property
    def status(self):
        return self._status

    @property
    def message(self):
        return self._message


@celery_app.task(bind=True, base=ProgressTask)
def process_csv_import(self, file_content: str, filename: str) -> Dict[str, Any]:
    """
    Process CSV file and import products into database.
    
    Args:
        file_content: CSV file content as string
        filename: Original filename
        
    Returns:
        Dictionary with import results
    """
    try:
        # Initialize database connection
        init_db()
        db = SessionLocal()
        
        self.update_progress(5, "parsing", "Parsing CSV file...")
        
        # Parse CSV content
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        # Validate required columns
        required_columns = {"sku", "name"}
        if not required_columns.issubset(set(csv_reader.fieldnames or [])):
            db.close()
            return {
                "success": False,
                "error": f"CSV must contain columns: {', '.join(required_columns)}",
                "processed": 0,
                "created": 0,
                "updated": 0,
                "errors": []
            }
        
        self.update_progress(10, "validating", "Validating data...")
        
        # Process rows in batches for better performance
        batch_size = 1000
        batch = []
        processed = 0
        created = 0
        updated = 0
        errors = []
        total_rows = sum(1 for _ in csv.DictReader(io.StringIO(file_content)))
        
        # Reset reader
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        self.update_progress(15, "importing", f"Importing {total_rows} products...")
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
            try:
                # Extract and clean data
                sku = str(row.get("sku", "")).strip()
                name = str(row.get("name", "")).strip()
                description = str(row.get("description", "")).strip() if row.get("description") else None
                
                # Validate required fields
                if not sku:
                    errors.append(f"Row {row_num}: SKU is required")
                    continue
                
                if not name:
                    errors.append(f"Row {row_num}: Name is required")
                    continue
                
                # Check if product exists (case-insensitive SKU)
                existing_product = db.query(Product).filter(
                    func.lower(Product.sku) == sku.lower()
                ).first()
                
                if existing_product:
                    # Update existing product
                    existing_product.name = name
                    existing_product.description = description
                    # Note: active status is not in CSV, so we don't update it
                    updated += 1
                else:
                    # Create new product
                    new_product = Product(
                        sku=sku,
                        name=name,
                        description=description,
                        active=True  # Default to active
                    )
                    batch.append(new_product)
                    created += 1
                
                processed += 1
                
                # Commit in batches
                if len(batch) >= batch_size:
                    try:
                        db.bulk_save_objects(batch)
                        db.commit()
                        batch = []
                    except IntegrityError as e:
                        db.rollback()
                        errors.append(f"Batch error: {str(e)}")
                
                # Update progress every 1000 rows
                if processed % 1000 == 0:
                    progress = 15 + int((processed / total_rows) * 80)
                    self.update_progress(
                        progress,
                        "importing",
                        f"Processed {processed}/{total_rows} products..."
                    )
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                logger.error(f"Error processing row {row_num}: {str(e)}")
                continue
        
        # Commit remaining batch
        if batch:
            try:
                db.bulk_save_objects(batch)
                db.commit()
            except IntegrityError as e:
                db.rollback()
                errors.append(f"Final batch error: {str(e)}")
        
        self.update_progress(95, "finalizing", "Finalizing import...")
        
        # Trigger webhooks for bulk import
        try:
            trigger_webhooks = get_webhook_utils()
            trigger_webhooks("product.bulk_import", {
                "processed": processed,
                "created": created,
                "updated": updated,
                "filename": filename
            })
        except Exception as e:
            logger.error(f"Error triggering webhooks: {str(e)}")
        
        db.close()
        
        self.update_progress(100, "complete", "Import completed successfully!")
        
        return {
            "success": True,
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors[:100],  # Limit error list
            "total_errors": len(errors)
        }
        
    except Exception as e:
        logger.error(f"Error in CSV import task: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "processed": processed if 'processed' in locals() else 0,
            "created": created if 'created' in locals() else 0,
            "updated": updated if 'updated' in locals() else 0,
            "errors": errors if 'errors' in locals() else []
        }


@celery_app.task
def bulk_delete_products() -> Dict[str, Any]:
    """
    Delete all products from database.
    
    Returns:
        Dictionary with deletion results
    """
    try:
        init_db()
        db = SessionLocal()
        
        count = db.query(Product).count()
        db.query(Product).delete()
        db.commit()
        
        # Trigger webhooks
        try:
            trigger_webhooks = get_webhook_utils()
            trigger_webhooks("product.bulk_delete", {"deleted_count": count})
        except Exception as e:
            logger.error(f"Error triggering webhooks: {str(e)}")
        
        db.close()
        
        return {
            "success": True,
            "deleted_count": count
        }
        
    except Exception as e:
        logger.error(f"Error in bulk delete task: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "deleted_count": 0
        }

