import asyncio

from fastapi import status, APIRouter, HTTPException, BackgroundTasks

from constants import STATUS_FAILED, STATUS_SENT, STATUS_PROCESSING, STATUS_QUEUED
from database import save_notification, get_notification, update_notification_status
from models import NotificationRequest, NotificationResponse, NotificationStatus
from provider import send_notification_to_provider

from settings import settings

MAX_RETRIES = settings.max_retries
RETRY_BACKOFF = settings.retry_backoff

requests_router = APIRouter()


@requests_router.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_request(data: NotificationRequest):
    """
    Registro de Solicitud: POST /v1/requests
    Crea una nueva solicitud de notificación
    """

    notification = NotificationRequest(
        to=data.to,
        message=data.message,
        type=data.type,
        status=STATUS_QUEUED,
    )

    await save_notification(notification)

    return NotificationResponse(id=notification.id)


@requests_router.post(
    "/requests/{request_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Notificación en proceso"},
        404: {
            "description": "Not found",
        },
    },
)
async def process_request(request_id: str, background_tasks: BackgroundTasks):
    """Procesamiento de Envío: POST /v1/requests/{id}/process"""

    notification = await get_notification(request_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Not found")

    await update_notification_status(request_id, STATUS_PROCESSING)
    background_tasks.add_task(call_provider, request_id, notification)

    return {"status": STATUS_PROCESSING, "id": request_id}


async def call_provider(request_id: str, notification: NotificationRequest) -> dict:

    for attempt in range(MAX_RETRIES):
        try:
            result = await send_notification_to_provider(
                to=notification.to,
                message=notification.message,
                notification_type=notification.type,
            )
            new_status = STATUS_SENT if result["success"] else STATUS_FAILED

            await update_notification_status(request_id, new_status)

        except Exception:
            await asyncio.sleep(RETRY_BACKOFF**attempt)

    return {"success": False, "error": "Max retries exceeded"}


@requests_router.get(
    "/requests/{request_id}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": NotificationStatus},
        404: {
            "description": "Not found",
        },
    },
)
async def get_request_status(request_id: str):
    """
    Consulta de Estado: GET /v1/requests/{id}
    """

    notification = await get_notification(request_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Not found")

    return NotificationStatus(id=notification.id, status=notification.status)
