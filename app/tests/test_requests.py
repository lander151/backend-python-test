import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from models import NotificationRequest
from constants import STATUS_QUEUED, STATUS_PROCESSING, STATUS_SENT, STATUS_FAILED
from routers.requests import call_provider


@pytest.fixture
def client():
    """Fixture que proporciona un cliente de prueba para FastAPI"""
    return TestClient(app)


class TestCreateRequest:
    """Tests para el endpoint POST /requests"""

    @pytest.mark.asyncio
    async def test_create_request_success(self, notification_data):
        """Test que verifica la creación exitosa de una solicitud"""
        with patch("routers.requests.save_notification", new_callable=AsyncMock):
            client = TestClient(app)
            response = client.post(
                "v1/requests",
                json={
                    "to": notification_data["to"],
                    "message": notification_data["message"],
                    "type": notification_data["type"],
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert isinstance(data["id"], str)

    @pytest.mark.asyncio
    async def test_create_request_with_all_fields(self):
        """Test que crea una solicitud con todos los campos"""
        with patch("routers.requests.save_notification", new_callable=AsyncMock):
            client = TestClient(app)
            payload = {
                "to": "test@example.com",
                "message": "Hello World",
                "type": "sms",
            }
            response = client.post("v1/requests", json=payload)

            assert response.status_code == 201
            data = response.json()
            assert "id" in data

    @pytest.mark.asyncio
    async def test_create_request_saves_notification(self):
        """Test que verifica que save_notification es llamado"""
        with patch(
            "routers.requests.save_notification", new_callable=AsyncMock
        ) as mock_save:
            client = TestClient(app)
            payload = {
                "to": "test@example.com",
                "message": "Test",
                "type": "email",
            }
            response = client.post("v1/requests", json=payload)

            assert response.status_code == 201
            mock_save.assert_called_once()
            # Verificar que se pasó un NotificationRequest
            call_args = mock_save.call_args[0][0]
            assert isinstance(call_args, NotificationRequest)
            assert call_args.status == STATUS_QUEUED


class TestProcessRequest:
    """Tests para el endpoint POST /requests/{request_id}/process"""

    @pytest.mark.asyncio
    async def test_process_request_success(self, notification_with_id):
        """Test que procesa exitosamente una solicitud"""
        with (
            patch(
                "routers.requests.get_notification", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "routers.requests.update_notification_status", new_callable=AsyncMock
            ) as mock_update,
            patch("routers.requests.call_provider", new_callable=AsyncMock),
        ):
            mock_get.return_value = notification_with_id

            client = TestClient(app)
            response = client.post(f"v1/requests/{notification_with_id.id}/process")

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == STATUS_PROCESSING
            assert data["id"] == notification_with_id.id
            mock_get.assert_called_once_with(notification_with_id.id)
            mock_update.assert_called_once_with(
                notification_with_id.id, STATUS_PROCESSING
            )

    @pytest.mark.asyncio
    async def test_process_request_not_found(self):
        """Test que retorna 404 cuando la notificación no existe"""
        with patch(
            "routers.requests.get_notification", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            client = TestClient(app)
            response = client.post("v1/requests/nonexistent-id/process")

            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Not found"

    @pytest.mark.asyncio
    async def test_process_request_adds_background_task(self, notification_with_id):
        """Test que verifica que se agregue una tarea en background"""
        with (
            patch(
                "routers.requests.get_notification", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "routers.requests.update_notification_status", new_callable=AsyncMock
            ) as mock_update,
            patch("routers.requests.call_provider", new_callable=AsyncMock),
        ):
            mock_get.return_value = notification_with_id

            client = TestClient(app)
            response = client.post(f"v1/requests/{notification_with_id.id}/process")

            assert response.status_code == 202


class TestGetRequestStatus:
    """Tests para el endpoint GET /requests/{request_id}"""

    @pytest.mark.asyncio
    async def test_get_request_status_success(self, notification_with_id):
        """Test que obtiene exitosamente el estado de una solicitud"""
        with patch(
            "routers.requests.get_notification", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = notification_with_id

            client = TestClient(app)
            response = client.get(f"v1/requests/{notification_with_id.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == notification_with_id.id
            assert data["status"] == STATUS_QUEUED

    @pytest.mark.asyncio
    async def test_get_request_status_not_found(self):
        """Test que retorna 404 cuando la notificación no existe"""
        with patch(
            "routers.requests.get_notification", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            client = TestClient(app)
            response = client.get("v1/requests/nonexistent-id")

            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Not found"

    @pytest.mark.asyncio
    async def test_get_request_status_with_different_status(self):
        """Test que obtiene el estado con diferentes estados"""
        notification_id = str(uuid4())
        for status in [STATUS_QUEUED, STATUS_PROCESSING, STATUS_SENT, STATUS_FAILED]:
            notification = NotificationRequest(
                id=notification_id,
                to="user@example.com",
                message="Test",
                type="email",
                status=status,
            )

            with patch(
                "routers.requests.get_notification", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = notification

                client = TestClient(app)
                response = client.get(f"v1/requests/{notification_id}")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == status


class TestCallProvider:
    """Tests para la función call_provider"""

    @pytest.mark.asyncio
    async def test_call_provider_success(self, notification_with_id):
        """Test que envía la notificación exitosamente"""
        with (
            patch(
                "routers.requests.send_notification_to_provider",
                new_callable=AsyncMock,
            ) as mock_send,
            patch(
                "routers.requests.update_notification_status",
                new_callable=AsyncMock,
            ) as mock_update,
        ):
            mock_send.return_value = {"success": True}

            result = await call_provider(notification_with_id.id, notification_with_id)

            mock_send.assert_called_once_with(
                to=notification_with_id.to,
                message=notification_with_id.message,
                notification_type=notification_with_id.type,
            )
            mock_update.assert_called_once_with(notification_with_id.id, STATUS_SENT)

    @pytest.mark.asyncio
    async def test_call_provider_failure(self, notification_with_id):
        """Test que marca como failed cuando el provider falla"""
        with (
            patch(
                "routers.requests.send_notification_to_provider",
                new_callable=AsyncMock,
            ) as mock_send,
            patch(
                "routers.requests.update_notification_status",
                new_callable=AsyncMock,
            ) as mock_update,
        ):
            mock_send.return_value = {"success": False}

            result = await call_provider(notification_with_id.id, notification_with_id)

            mock_update.assert_called_once_with(notification_with_id.id, STATUS_FAILED)

    @pytest.mark.asyncio
    async def test_call_provider_with_exception_retries(self, notification_with_id):
        """Test que reintenta cuando ocurre una excepción"""
        with (
            patch(
                "routers.requests.send_notification_to_provider",
                new_callable=AsyncMock,
            ) as mock_send,
            patch(
                "routers.requests.update_notification_status",
                new_callable=AsyncMock,
            ) as mock_update,
            patch("routers.requests.asyncio.sleep", new_callable=AsyncMock),
        ):
            # Primera llamada falla, segunda exitosa
            mock_send.side_effect = [
                Exception("Connection error"),
                {"success": True},
            ]

            result = await call_provider(notification_with_id.id, notification_with_id)

            # Debe reintentar y finalmente ser exitoso
            assert mock_send.call_count == 2
            mock_update.assert_called_once_with(notification_with_id.id, STATUS_SENT)

    @pytest.mark.asyncio
    async def test_call_provider_max_retries_exceeded(self, notification_with_id):
        """Test que retorna error después de exceder max_retries"""
        with (
            patch(
                "routers.requests.send_notification_to_provider",
                new_callable=AsyncMock,
            ) as mock_send,
            patch(
                "routers.requests.update_notification_status",
                new_callable=AsyncMock,
            ) as mock_update,
            patch("routers.requests.asyncio.sleep", new_callable=AsyncMock),
            patch("routers.requests.MAX_RETRIES", 3),
        ):
            # Todas las llamadas fallan
            mock_send.side_effect = Exception("Connection error")

            result = await call_provider(notification_with_id.id, notification_with_id)

            assert not result["success"]
            assert "Max retries exceeded" in result["error"]

    @pytest.mark.asyncio
    async def test_call_provider_success_on_retry(self, notification_with_id):
        """Test que logra enviar exitosamente en un reintento"""
        with (
            patch(
                "routers.requests.send_notification_to_provider",
                new_callable=AsyncMock,
            ) as mock_send,
            patch(
                "routers.requests.update_notification_status",
                new_callable=AsyncMock,
            ) as mock_update,
            patch("routers.requests.asyncio.sleep", new_callable=AsyncMock),
        ):
            # Primero falla, luego éxito
            mock_send.side_effect = [
                Exception("Temporary error"),
                {"success": True},
            ]

            result = await call_provider(notification_with_id.id, notification_with_id)

            # Debe haber reintentado y logrado
            assert mock_send.call_count == 2
            mock_update.assert_called_once_with(notification_with_id.id, STATUS_SENT)
            assert result["success"]
