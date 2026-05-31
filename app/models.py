from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from constants import STATUS_QUEUED, NOTIFICATION_TYPES, STATUSES


class NotificationRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    to: str
    message: str
    type: str = Literal[NOTIFICATION_TYPES]
    status: str = STATUS_QUEUED  # default


class NotificationResponse(BaseModel):
    id: str


class NotificationStatus(BaseModel):
    id: str
    status: str = Literal[STATUSES]
