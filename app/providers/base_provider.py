"""
Base Notification Provider Abstract Class.

This module defines the abstract base class for all notification providers
(SMS, Email, WhatsApp). New providers should inherit from BaseNotificationProvider
and implement all abstract methods.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("notify")


@dataclass
class NotificationResult:
    """Result of a notification sending attempt."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "message_id": self.message_id,
            "error": self.error,
            "provider": self.provider,
        }


class BaseNotificationProvider(ABC):
    """Abstract base class for notification providers (SMS, Email, WhatsApp)."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
            
        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> None:
        """Validate that required configuration is present. Raise ValueError if invalid."""
        pass

    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> NotificationResult:
        """
        Send an SMS message.
        
        Args:
            phone_number: Recipient phone number (international format, e.g., +254712345678)
            message: Message body
            
        Returns:
            NotificationResult with success status and optional message ID
        """
        pass

    @abstractmethod
    def send_email(self, email: str, subject: str, body: str) -> NotificationResult:
        """
        Send an email message.
        
        Args:
            email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            
        Returns:
            NotificationResult with success status
        """
        pass

    @abstractmethod
    def send_whatsapp(self, phone_number: str, message: str) -> NotificationResult:
        """
        Send a WhatsApp message.
        
        Args:
            phone_number: Recipient WhatsApp phone number
            message: Message body
            
        Returns:
            NotificationResult with success status and optional message ID
        """
        pass

    def get_provider_name(self) -> str:
        """Return the name of this provider."""
        return self.__class__.__name__

    def get_balance(self) -> Dict[str, Any]:
        """
        Get the account balance/status for this provider.
        
        Override this method in providers that support balance queries.
        
        Returns:
            Dictionary with balance information
        """
        return {"success": False, "error": "Balance check not supported by this provider"}

    def supports_feature(self, feature: str) -> bool:
        """
        Check if provider supports a specific feature.
        
        Override this method to specify feature support.
        
        Args:
            feature: Feature name (e.g., "sms", "email", "whatsapp")
            
        Returns:
            True if feature is supported, False otherwise
        """
        return False

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"<{self.get_provider_name()}>"


# Feature flags for providers
class ProviderFeatures:
    """Feature flags for notification providers."""
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    
    @classmethod
    def all_features(cls) -> list:
        """Return all available features."""
        return [cls.SMS, cls.EMAIL, cls.WHATSAPP]

