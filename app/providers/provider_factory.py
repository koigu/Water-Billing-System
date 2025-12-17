"""
Provider Factory and Notification Manager.

This module provides a factory for creating notification provider instances
and a notification manager with fallback support for Africa's Talking.
"""
import os
from typing import Dict, Any, Optional, Type
import logging
from .base_provider import BaseNotificationProvider
from .africas_talking_provider import AfricasTalkingProvider

logger = logging.getLogger("notify")


class ProviderFactory:
    """Factory for creating notification provider instances."""

    # Registry of available providers
    PROVIDERS: Dict[str, Type[BaseNotificationProvider]] = {
        "africas_talking": AfricasTalkingProvider,
        "africa_talking": AfricasTalkingProvider,  # Alias
    }

    @staticmethod
    def get_provider(provider_name: str, config: Optional[Dict[str, Any]] = None) -> BaseNotificationProvider:
        """
        Get a provider instance by name.
        
        Args:
            provider_name: Name of the provider (e.g., "africas_talking")
            config: Configuration dictionary. If None, will be loaded from environment variables.
            
        Returns:
            Initialized provider instance
            
        Raises:
            ValueError: If provider name is not found
        """
        provider_name = provider_name.lower().strip()
        
        if provider_name not in ProviderFactory.PROVIDERS:
            available = ", ".join(ProviderFactory.PROVIDERS.keys())
            raise ValueError(
                f"Unknown provider: {provider_name}. Available providers: {available}"
            )

        Provider = ProviderFactory.PROVIDERS[provider_name]
        
        if config is None:
            config = ProviderFactory.load_config_from_env(provider_name)
        
        logger.info(f"Initializing {provider_name} provider")
        return Provider(config)

    @staticmethod
    def load_config_from_env(provider_name: str) -> Dict[str, Any]:
        """Load provider configuration from environment variables."""
        provider_name = provider_name.lower().strip()

        if provider_name in ("africas_talking", "africa_talking"):
            return {
                "api_key": os.getenv("AFRICAS_TALKING_API_KEY"),
                "username": os.getenv("AFRICAS_TALKING_USERNAME"),
                "is_sandbox": os.getenv("AFRICAS_TALKING_IS_SANDBOX", "true").lower() == "true",
                "supports_whatsapp": os.getenv("AFRICAS_TALKING_SUPPORTS_WHATSAPP", "false").lower() == "true",
            }
        
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    @staticmethod
    def register_provider(name: str, provider_class: Type[BaseNotificationProvider]) -> None:
        """
        Register a new provider with the factory.
        
        Args:
            name: Provider name (lowercase)
            provider_class: Provider class that inherits from BaseNotificationProvider
        """
        ProviderFactory.PROVIDERS[name.lower()] = provider_class
        logger.info(f"Registered new provider: {name}")

    @staticmethod
    def list_providers() -> list:
        """List all registered provider names."""
        return list(ProviderFactory.PROVIDERS.keys())


class NotificationManager:
    """Manager for sending notifications with pluggable providers and fallback support."""

    def __init__(
        self, 
        primary_provider: str, 
        fallback_provider: Optional[str] = None,
        primary_config: Optional[Dict[str, Any]] = None,
        fallback_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize notification manager.
        
        Args:
            primary_provider: Primary provider name (required)
            fallback_provider: Fallback provider if primary fails (optional)
            primary_config: Custom config for primary provider (optional)
            fallback_config: Custom config for fallback provider (optional)
        """
        self.primary = None
        self.fallback = None
        
        try:
            if primary_config:
                self.primary = ProviderFactory.get_provider(primary_provider, primary_config)
            else:
                self.primary = ProviderFactory.get_provider(primary_provider)
            logger.info(f"Primary notification provider: {primary_provider}")
        except Exception as e:
            logger.error(f"Failed to initialize primary provider '{primary_provider}': {e}")
            raise

        if fallback_provider:
            try:
                if fallback_config:
                    self.fallback = ProviderFactory.get_provider(fallback_provider, fallback_config)
                else:
                    self.fallback = ProviderFactory.get_provider(fallback_provider)
                logger.info(f"Fallback notification provider: {fallback_provider}")
            except Exception as e:
                logger.warning(f"Failed to initialize fallback provider '{fallback_provider}': {e}")

    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS with fallback support."""
        if not self.primary:
            return {"success": False, "error": "No primary provider configured"}
        
        result = self.primary.send_sms(phone_number, message)
        
        if not result.success and self.fallback:
            logger.warning(
                f"Primary SMS provider failed ({result.error}), trying fallback..."
            )
            result = self.fallback.send_sms(phone_number, message)
        
        return result.to_dict()

    def send_email(self, email: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email with fallback support."""
        if not self.primary:
            return {"success": False, "error": "No primary provider configured"}
        
        result = self.primary.send_email(email, subject, body)
        
        if not result.success and self.fallback:
            logger.warning(
                f"Primary email provider failed ({result.error}), trying fallback..."
            )
            result = self.fallback.send_email(email, subject, body)
        
        return result.to_dict()

    def send_whatsapp(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp with fallback support."""
        if not self.primary:
            return {"success": False, "error": "No primary provider configured"}
        
        result = self.primary.send_whatsapp(phone_number, message)
        
        if not result.success and self.fallback:
            logger.warning(
                f"Primary WhatsApp provider failed ({result.error}), trying fallback..."
            )
            result = self.fallback.send_whatsapp(phone_number, message)
        
        return result.to_dict()

    def get_active_provider(self) -> str:
        """Get the name of the currently active provider."""
        if self.primary:
            return self.primary.get_provider_name()
        return "None"

    def is_fallback_available(self) -> bool:
        """Check if fallback provider is available."""
        return self.fallback is not None

    def check_balance(self) -> Dict[str, Any]:
        """
        Check the balance/status of the primary provider.
        
        Returns:
            Dictionary with balance information if supported
        """
        if self.primary:
            return self.primary.get_balance()
        return {"success": False, "error": "No provider configured"}

