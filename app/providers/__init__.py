"""
Notification Providers Package.

This package provides a notification provider architecture using
Africa's Talking SMS service for sending notifications.

Available Providers:
- AfricasTalkingProvider: SMS via Africa's Talking

Usage:
    from app.providers import NotificationManager, ProviderFactory
    
    # Get a provider instance
    provider = ProviderFactory.get_provider("africas_talking")
    
    # Or use the notification manager
    manager = NotificationManager("africas_talking")
    result = manager.send_sms("+254712345678", "Hello!")
"""

from .base_provider import BaseNotificationProvider, NotificationResult, ProviderFeatures
from .africas_talking_provider import AfricasTalkingProvider
from .provider_factory import ProviderFactory, NotificationManager

__all__ = [
    # Base classes
    "BaseNotificationProvider",
    "NotificationResult",
    "ProviderFeatures",
    
    # Providers
    "AfricasTalkingProvider",
    
    # Factory and Manager
    "ProviderFactory",
    "NotificationManager",
]

