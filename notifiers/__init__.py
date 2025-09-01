"""
Notifiers Package

Contains various notification services for sending AI intelligence events to different platforms.
"""

from .console_notifier import ConsoleNotifier
# Import other notifiers only if their dependencies are available
try:
    from .telegram_notifier import TelegramNotifier
except ImportError:
    pass

try:
    from .discord_notifier import DiscordNotifier
except ImportError:
    pass

try:
    from .webhook_notifier import WebhookNotifier
except ImportError:
    pass

from .component_notifier import ComponentNotifier

__all__ = [
    'ConsoleNotifier',
    'TelegramNotifier',
    'DiscordNotifier',
    'WebhookNotifier',
    'ComponentNotifier'
] 