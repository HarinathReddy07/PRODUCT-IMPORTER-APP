"""
FastAPI application for REST API endpoints.
"""
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from models import Product, Webhook, get_db, init_db
from tasks import bulk_delete_products
from webhook_utils import trigger_webhooks, test_webhook
from celery.result import AsyncResult
from celery_app import celery_app
from config import ITEMS_PER_PAGE
from datetime import datetime

app = FastAPI(
    title="Product Importer API",
    description="REST API for product management and webhook configuration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class ProductCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    active: Optional[bool] = None


class BulkDeleteRequest(BaseModel):
    product_ids: List[int] = Field(..., min_items=1)


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: Optional[str]
    active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=1000)
    event_type: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    secret: Optional[str] = None


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(None, min_length=1, max_length=1000)
    event_type: Optional[str] = Field(None, min_length=1, max_length=100)
    enabled: Optional[bool] = None
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    id: int
    url: str
    event_type: str
    enabled: bool
    secret: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Statistics endpoint
@app.get("/api/statistics")
def get_statistics(db: Session = Depends(get_db)):
    """
    Get product statistics for dashboard.
    """
    try:
        init_db()
        total_products = db.query(Product).count()
        active_products = db.query(Product).filter(Product.active == True).count()
        inactive_products = db.query(Product).filter(Product.active == False).count()
        
        return {
            "total_products": total_products,
            "active_products": active_products,
            "inactive_products": inactive_products
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Product endpoints
@app.get("/api/products", response_model=Dict[str, Any])
def get_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(ITEMS_PER_PAGE, ge=1, le=100),
    sku: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get paginated list of products with optional filtering.
    """
    try:
        init_db()
        query = db.query(Product)
        
        # Apply filters
        if sku:
            query = query.filter(func.lower(Product.sku).contains(sku.lower()))
        if name:
            query = query.filter(Product.name.contains(name))
        if description:
            query = query.filter(Product.description.contains(description))
        if active is not None:
            query = query.filter(Product.active == active)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        products = query.order_by(Product.id.desc()).offset(offset).limit(per_page).all()
        
        return {
            "items": [product.to_dict() for product in products],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Get a single product by ID.
    """
    try:
        init_db()
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product.
    """
    try:
        init_db()
        # Check if SKU already exists (case-insensitive)
        existing = db.query(Product).filter(
            func.lower(Product.sku) == product.sku.lower()
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")
        
        new_product = Product(
            sku=product.sku,
            name=product.name,
            description=product.description,
            active=product.active
        )
        
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        
        # Trigger webhook
        trigger_webhooks("product.created", {
            "product": new_product.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return new_product
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db)):
    """
    Update an existing product.
    """
    try:
        init_db()
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Update fields
        if product_update.name is not None:
            product.name = product_update.name
        if product_update.description is not None:
            product.description = product_update.description
        if product_update.active is not None:
            product.active = product_update.active
        
        product.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(product)
        
        # Trigger webhook
        trigger_webhooks("product.updated", {
            "product": product.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return product
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a product.
    """
    try:
        init_db()
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product_dict = product.to_dict()
        db.delete(product)
        db.commit()
        
        # Trigger webhook
        trigger_webhooks("product.deleted", {
            "product": product_dict,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products/bulk-delete")
def bulk_delete(request: BulkDeleteRequest, db: Session = Depends(get_db)):
    """
    Delete multiple selected products.
    """
    try:
        init_db()
        product_ids = request.product_ids
        
        # Get products to delete (for webhook)
        products_to_delete = db.query(Product).filter(Product.id.in_(product_ids)).all()
        product_dicts = [p.to_dict() for p in products_to_delete]
        
        # Delete products
        deleted_count = db.query(Product).filter(Product.id.in_(product_ids)).delete(synchronize_session=False)
        db.commit()
        
        # Trigger webhooks for each deleted product
        for product_dict in product_dicts:
            trigger_webhooks("product.deleted", {
                "product": product_dict,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Also trigger bulk delete webhook
        trigger_webhooks("product.bulk_delete", {
            "deleted_count": deleted_count,
            "product_ids": product_ids,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "success": True,
            "deleted_count": deleted_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """
    Get status of an async task.
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        response = {
            "task_id": task_id,
            "state": task_result.state,
            "result": task_result.result if task_result.ready() else None
        }
        
        if task_result.state == "PROGRESS":
            response["progress"] = task_result.info.get("progress", 0) if task_result.info else 0
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Webhook endpoints
@app.get("/api/webhooks", response_model=List[WebhookResponse])
def get_webhooks(db: Session = Depends(get_db)):
    """
    Get all webhooks.
    """
    try:
        init_db()
        webhooks = db.query(Webhook).order_by(Webhook.id.desc()).all()
        return webhooks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/webhooks/{webhook_id}", response_model=WebhookResponse)
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """
    Get a single webhook by ID.
    """
    try:
        init_db()
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return webhook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webhooks", response_model=WebhookResponse, status_code=201)
def create_webhook(webhook: WebhookCreate, db: Session = Depends(get_db)):
    """
    Create a new webhook.
    """
    try:
        init_db()
        new_webhook = Webhook(
            url=webhook.url,
            event_type=webhook.event_type,
            enabled=webhook.enabled,
            secret=webhook.secret
        )
        
        db.add(new_webhook)
        db.commit()
        db.refresh(new_webhook)
        
        return new_webhook
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/webhooks/{webhook_id}", response_model=WebhookResponse)
def update_webhook(webhook_id: int, webhook_update: WebhookUpdate, db: Session = Depends(get_db)):
    """
    Update an existing webhook.
    """
    try:
        init_db()
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        if webhook_update.url is not None:
            webhook.url = webhook_update.url
        if webhook_update.event_type is not None:
            webhook.event_type = webhook_update.event_type
        if webhook_update.enabled is not None:
            webhook.enabled = webhook_update.enabled
        if webhook_update.secret is not None:
            webhook.secret = webhook_update.secret
        
        webhook.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(webhook)
        
        return webhook
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/webhooks/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """
    Delete a webhook.
    """
    try:
        init_db()
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        db.delete(webhook)
        db.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webhooks/{webhook_id}/test")
def test_webhook_endpoint(webhook_id: int):
    """
    Test a webhook by sending a test payload.
    """
    try:
        result = test_webhook(webhook_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    from config import FASTAPI_HOST, FASTAPI_PORT
    uvicorn.run(app, host=FASTAPI_HOST, port=FASTAPI_PORT)

