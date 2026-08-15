"""
CleanTrack AI — Notification Service
Sends FCM push and SMS (Twilio) notifications.
Gracefully degrades if credentials are missing.
"""
import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.core.config import get_settings
from app.models.notification import Notification, NotificationChannel, NotificationType
from app.models.user import User

logger = structlog.get_logger()
settings = get_settings()


class NotificationService:
    def __init__(self, db=None):
        self.db = db
        self._firebase_app = None

    def _get_firebase(self):
        if self._firebase_app:
            return self._firebase_app

        try:
            import firebase_admin
            from firebase_admin import credentials

            if settings.firebase_credentials_base64:
                cred_dict = json.loads(
                    base64.b64decode(settings.firebase_credentials_base64)
                )
                cred = credentials.Certificate(cred_dict)
            else:
                cred = credentials.Certificate(settings.firebase_credentials_path)

            if not firebase_admin._apps:
                self._firebase_app = firebase_admin.initialize_app(cred)
            else:
                self._firebase_app = firebase_admin.get_app()
            return self._firebase_app
        except Exception as e:
            logger.warning("firebase_init_failed", error=str(e))
            return None

    async def send_push(
        self,
        user: User,
        notif_type: NotificationType,
        title: str,
        body: str,
        payload: Optional[dict] = None,
        report_id: Optional[uuid.UUID] = None,
        dispatch_id: Optional[uuid.UUID] = None,
    ) -> Optional[Notification]:
        """Send FCM push notification. Falls back to SMS if FCM token missing."""
        notification = None

        if user.fcm_token:
            try:
                from firebase_admin import messaging
                app = self._get_firebase()
                if app:
                    msg = messaging.Message(
                        notification=messaging.Notification(title=title, body=body),
                        data={k: str(v) for k, v in (payload or {}).items()},
                        token=user.fcm_token,
                        android=messaging.AndroidConfig(priority="high"),
                    )
                    message_id = messaging.send(msg)
                    notification = Notification(
                        user_id=user.id,
                        type=notif_type,
                        channel=NotificationChannel.FCM,
                        title=title,
                        body=body,
                        payload=payload,
                        report_id=report_id,
                        dispatch_id=dispatch_id,
                        is_sent=True,
                        fcm_message_id=message_id,
                        sent_at=datetime.now(timezone.utc),
                    )
            except Exception as e:
                logger.error("fcm_send_failed", error=str(e), user_id=str(user.id))

        # SMS fallback: send if no FCM or FCM failed
        if not notification and user.phone:
            notification = await self._send_sms(user, title, body, notif_type, payload)

        if notification and self.db:
            self.db.add(notification)

        return notification

    async def _send_sms(
        self,
        user: User,
        title: str,
        body: str,
        notif_type: NotificationType,
        payload: Optional[dict] = None,
    ) -> Optional[Notification]:
        if not settings.twilio_account_sid:
            logger.warning("sms_skipped_no_credentials")
            return None

        try:
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            message = client.messages.create(
                body=f"[CleanTrack] {title}: {body}",
                from_=settings.twilio_phone_number,
                to=user.phone,
            )
            return Notification(
                user_id=user.id,
                type=notif_type,
                channel=NotificationChannel.SMS,
                title=title,
                body=body,
                payload=payload,
                is_sent=True,
                twilio_sid=message.sid,
                sent_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error("sms_send_failed", error=str(e), phone=user.phone)
            return None
