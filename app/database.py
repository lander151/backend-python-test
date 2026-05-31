import asyncio
from typing import Optional
from models import NotificationRequest

notifications_db: dict[str, NotificationRequest] = {}
_lock = asyncio.Lock()


async def save_notification(notification: NotificationRequest) -> NotificationRequest:
    """Guarda una notificación en la BD en memoria"""
    async with _lock:
        notifications_db[notification.id] = notification
    return notification


async def get_notification(request_id: str) -> Optional[NotificationRequest]:
    """Obtiene una notificación por ID"""
    async with _lock:
        return notifications_db.get(request_id)


async def update_notification_status(
    request_id: str, new_status: str
) -> Optional[NotificationRequest]:
    """Actualiza el estado de una notificación"""
    async with _lock:
        if request_id in notifications_db:
            notifications_db[request_id].status = new_status
            return notifications_db[request_id]
    return None
