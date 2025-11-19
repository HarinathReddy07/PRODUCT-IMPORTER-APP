"""
Utility functions for webhook management and triggering.
"""
import requests
import logging
from typing import Dict, Any, List
from models import Webhook, SessionLocal, init_db
from config import WEBHOOK_TIMEOUT

logger = logging.getLogger(__name__)


def trigger_webhooks(event_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Trigger all enabled webhooks for a given event type.
    
    Args:
        event_type: Type of event (e.g., 'product.created', 'product.updated')
        payload: Data to send to webhooks
        
    Returns:
        List of webhook trigger results
    """
    try:
        init_db()
        db = SessionLocal()
        
        # Find all enabled webhooks for this event type
        webhooks = db.query(Webhook).filter(
            Webhook.event_type == event_type,
            Webhook.enabled == True
        ).all()
        
        results = []
        
        for webhook in webhooks:
            try:
                response = requests.post(
                    webhook.url,
                    json={
                        "event_type": event_type,
                        "payload": payload,
                        "timestamp": payload.get("timestamp")
                    },
                    timeout=WEBHOOK_TIMEOUT,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "ProductImporter/1.0"
                    }
                )
                
                results.append({
                    "webhook_id": webhook.id,
                    "url": webhook.url,
                    "status_code": response.status_code,
                    "success": 200 <= response.status_code < 300,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else None
                })
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error triggering webhook {webhook.id}: {str(e)}")
                results.append({
                    "webhook_id": webhook.id,
                    "url": webhook.url,
                    "success": False,
                    "error": str(e)
                })
        
        db.close()
        return results
        
    except Exception as e:
        logger.error(f"Error in trigger_webhooks: {str(e)}", exc_info=True)
        return []


def test_webhook(webhook_id: int) -> Dict[str, Any]:
    """
    Test a specific webhook by sending a test payload.
    
    Args:
        webhook_id: ID of webhook to test
        
    Returns:
        Test result dictionary
    """
    try:
        init_db()
        db = SessionLocal()
        
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            db.close()
            return {
                "success": False,
                "error": "Webhook not found"
            }
        
        test_payload = {
            "event_type": webhook.event_type,
            "payload": {
                "test": True,
                "message": "This is a test webhook trigger"
            }
        }
        
        try:
            response = requests.post(
                webhook.url,
                json=test_payload,
                timeout=WEBHOOK_TIMEOUT,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ProductImporter/1.0"
                }
            )
            
            result = {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else None,
                "response_body": response.text[:500]  # Limit response body
            }
            
        except requests.exceptions.RequestException as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        db.close()
        return result
        
    except Exception as e:
        logger.error(f"Error testing webhook: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

