"""External integration adapters."""

from app.clients.notifications import EventDispatcher, NotificationDispatcher

__all__ = ["EventDispatcher", "NotificationDispatcher"]
