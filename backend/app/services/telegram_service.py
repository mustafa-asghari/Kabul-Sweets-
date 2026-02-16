"""
Telegram bot service for admin alerts and workflow actions.
"""

import base64
import binascii
import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("telegram_service")

DEFAULT_BOT_COMMANDS = [
    {"command": "menu", "description": "Products by category"},
    {"command": "order", "description": "Orders (pending / paid)"},
    {"command": "cake", "description": "Cake orders (pending / paid)"},
    {"command": "help", "description": "Show bot menu"},
]


class TelegramService:
    """Lightweight Telegram Bot API client."""
    _commands_configured: bool = False

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN.strip()
        self.admin_chat_ids = settings.TELEGRAM_ADMIN_CHAT_IDS
        self.api_base = (
            f"https://api.telegram.org/bot{self.bot_token}"
            if self.bot_token
            else ""
        )

    def is_configured(self) -> bool:
        """Return True when bot token and admin chats are configured."""
        return bool(self.api_base and self.admin_chat_ids)

    def send_text(
        self,
        chat_id: int,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
        disable_web_page_preview: bool = True,
    ) -> bool:
        """Send a text message to a Telegram chat."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._post_json("sendMessage", payload)

    def send_photo_url(
        self,
        chat_id: int,
        photo_url: str,
        *,
        caption: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Send an image to Telegram by remote URL."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo_url,
            "parse_mode": "HTML",
        }
        if caption:
            payload["caption"] = caption
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._post_json("sendPhoto", payload)

    def send_photo_data_url(
        self,
        chat_id: int,
        data_url: str,
        *,
        caption: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Send an image to Telegram from a base64 data URL."""
        parsed = self._parse_data_url(data_url)
        if parsed is None:
            return False

        content_type, file_bytes = parsed
        extension = self._extension_for_content_type(content_type)

        data: dict[str, Any] = {
            "chat_id": str(chat_id),
            "parse_mode": "HTML",
        }
        if caption:
            data["caption"] = caption
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)

        files = {
            "photo": (f"cake-reference.{extension}", file_bytes, content_type),
        }
        return self._post_multipart("sendPhoto", data, files)

    def answer_callback_query(self, callback_query_id: str, text: str) -> bool:
        """Acknowledge callback button presses in Telegram."""
        payload = {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": False,
        }
        return self._post_json("answerCallbackQuery", payload)

    def edit_message_reply_markup(
        self,
        chat_id: int,
        message_id: int,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Update or clear inline buttons on an existing message."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        else:
            payload["reply_markup"] = {"inline_keyboard": []}
        return self._post_json("editMessageReplyMarkup", payload)

    def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
        disable_web_page_preview: bool = True,
    ) -> bool:
        """Edit message text and optional buttons to keep chat clean."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._post_json("editMessageText", payload)

    def ensure_default_commands(self) -> bool:
        """Ensure slash command menu is configured for persistent access."""
        if not self.api_base:
            return False
        if self.__class__._commands_configured:
            return True

        ok = self._post_json("setMyCommands", {"commands": DEFAULT_BOT_COMMANDS})
        if ok:
            self.__class__._commands_configured = True
        return ok

    def _post_json(self, method: str, payload: dict[str, Any]) -> bool:
        if not self.api_base:
            logger.warning("Telegram bot token is not configured")
            return False

        url = f"{self.api_base}/{method}"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
            if not body.get("ok"):
                logger.warning("Telegram API %s failed: %s", method, body)
                return False
            return True
        except Exception as exc:
            logger.warning("Telegram API %s request failed: %s", method, str(exc))
            return False

    def _post_multipart(
        self,
        method: str,
        data: dict[str, Any],
        files: dict[str, tuple[str, bytes, str]],
    ) -> bool:
        if not self.api_base:
            logger.warning("Telegram bot token is not configured")
            return False

        url = f"{self.api_base}/{method}"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, data=data, files=files)
            response.raise_for_status()
            body = response.json()
            if not body.get("ok"):
                logger.warning("Telegram API %s failed: %s", method, body)
                return False
            return True
        except Exception as exc:
            logger.warning("Telegram API %s multipart request failed: %s", method, str(exc))
            return False

    @staticmethod
    def _extension_for_content_type(content_type: str) -> str:
        if content_type == "image/png":
            return "png"
        if content_type == "image/webp":
            return "webp"
        if content_type == "image/gif":
            return "gif"
        return "jpg"

    @staticmethod
    def _parse_data_url(data_url: str) -> tuple[str, bytes] | None:
        if not data_url.startswith("data:") or "," not in data_url:
            return None

        header, encoded = data_url.split(",", 1)
        if ";base64" not in header:
            return None

        content_type = header.split(";")[0].removeprefix("data:")
        try:
            file_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            return None

        if not content_type.startswith("image/"):
            return None
        return content_type, file_bytes
