"""
Telegram Bot Router - Handles webhook and API endpoints for Telegram integration
"""

from fastapi import APIRouter, Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Database reference (set by main server)
db: AsyncIOMotorDatabase = None

def set_db(database: AsyncIOMotorDatabase):
    global db
    db = database


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Webhook endpoint for receiving Telegram updates
    URL: https://your-domain.com/api/telegram/webhook
    """
    try:
        from services.telegram_bot import handle_telegram_message, handle_callback_query
        
        update = await request.json()
        logger.info(f"Telegram update received: {update.get('update_id', 'N/A')}")
        
        # Handle different update types
        if "message" in update:
            result = await handle_telegram_message(db, update["message"])
            logger.info(f"Message handled: {result}")
        elif "callback_query" in update:
            result = await handle_callback_query(db, update["callback_query"])
            logger.info(f"Callback handled: {result}")
        else:
            logger.warning(f"Unknown update type: {list(update.keys())}")
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        # Return 200 to prevent Telegram from retrying
        return {"ok": False, "error": str(e)}


@router.get("/set-webhook")
async def set_telegram_webhook():
    """
    Set the Telegram webhook URL
    Call this once after deployment to register the webhook
    """
    import httpx
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise HTTPException(status_code=500, detail="Telegram bot token not configured")
    
    # Get the backend URL from environment
    backend_url = os.environ.get("REACT_APP_BACKEND_URL", "")
    if not backend_url:
        raise HTTPException(status_code=500, detail="Backend URL not configured")
    
    webhook_url = f"{backend_url}/api/telegram/webhook"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": webhook_url},
                timeout=10
            )
            result = response.json()
            
            if result.get("ok"):
                return {
                    "status": "success",
                    "message": "Webhook set successfully",
                    "webhook_url": webhook_url
                }
            else:
                raise HTTPException(status_code=500, detail=f"Telegram API error: {result.get('description', 'Unknown error')}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to set webhook: {str(e)}")


@router.get("/webhook-info")
async def get_webhook_info():
    """Get current webhook configuration"""
    import httpx
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise HTTPException(status_code=500, detail="Telegram bot token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getWebhookInfo",
                timeout=10
            )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to get webhook info: {str(e)}")


@router.get("/bot-info")
async def get_bot_info():
    """Get bot information"""
    import httpx
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise HTTPException(status_code=500, detail="Telegram bot token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10
            )
            result = response.json()
            
            if result.get("ok"):
                bot = result.get("result", {})
                return {
                    "bot_name": bot.get("first_name"),
                    "bot_username": bot.get("username"),
                    "bot_id": bot.get("id"),
                    "can_join_groups": bot.get("can_join_groups"),
                    "supports_inline_queries": bot.get("supports_inline_queries")
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to get bot info")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@router.post("/send-message")
async def send_message_api(chat_id: int, message: str):
    """
    Send a message to a specific chat
    Useful for sending notifications from the ERP
    """
    from services.telegram_bot import send_telegram_message
    
    success = await send_telegram_message(chat_id, message)
    if success:
        return {"status": "sent", "chat_id": chat_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.get("/linked-employees")
async def get_linked_employees():
    """Get list of employees who have linked their Telegram accounts"""
    employees = await db.employees.find(
        {"telegram_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1, "telegram_username": 1, "telegram_linked_at": 1}
    ).to_list(100)
    
    return {
        "count": len(employees),
        "employees": employees
    }


@router.get("/meeting-logs")
async def get_telegram_meeting_logs(limit: int = 50):
    """Get meeting logs submitted via Telegram"""
    logs = await db.meeting_logs.find(
        {"source": "telegram"}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Convert ObjectId to string
    for log in logs:
        if "_id" in log:
            log["_id"] = str(log["_id"])
    
    return {
        "count": len(logs),
        "logs": logs
    }
