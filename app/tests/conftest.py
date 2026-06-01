from uuid import uuid4

import pytest
import sys
from pathlib import Path

from constants import STATUS_QUEUED
from models import NotificationRequest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def notification_data():
    """Fixture con datos de una notificación de prueba"""
    return {
        "to": "test@example.com",
        "message": "Test message",
        "type": "email",
    }


@pytest.fixture
def notification_with_id(notification_data):
    """Fixture con datos de notificación incluyendo un ID"""
    notification_id = str(uuid4())
    return NotificationRequest(
        id=notification_id,
        **notification_data,
        status=STATUS_QUEUED,
    )
