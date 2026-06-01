import httpx2
from settings import settings

PROVIDER_URL = settings.provider_url
API_KEY = settings.provider_api_key
PROVIDER_TIMEOUT = settings.provider_timeout


async def send_notification_to_provider(
    to: str, message: str, notification_type: str
) -> dict:
    """Envía la notificación al provider externo"""
    async with httpx2.AsyncClient() as client:
        payload = {"to": to, "message": message, "type": notification_type}
        headers = {"X-API-Key": API_KEY}
        try:
            response = await client.post(
                f"{PROVIDER_URL}/v1/notify",
                json=payload,
                headers=headers,
                timeout=PROVIDER_TIMEOUT,
            )
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.json() if response.text else {},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
