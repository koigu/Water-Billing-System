"""
Notification Module for Water Billing System.

This module provides notification functionality using Africa's Talking SMS provider.
Supports SMS and WhatsApp notifications.

Usage:
    from app.notify import send_sms, send_email, send_invoice_message
    
    # Simple SMS
    send_sms("+254712345678", "Your bill is ready")
    
    # Send invoice
    send_invoice_message(customer, invoice, method="all")
"""

import os
import logging
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

from app.providers import NotificationManager, ProviderFactory

logger = logging.getLogger("notify")

# Default provider is Africa's Talking
DEFAULT_PROVIDER = "africas_talking"

def _init_notification_manager():
    """Initialize the notification manager from environment variables."""
    primary = os.getenv("SMS_PROVIDER", DEFAULT_PROVIDER).lower()
    fallback = os.getenv("SMS_FALLBACK_PROVIDER", None)
    
    if fallback:
        fallback = fallback.lower() if fallback else None
    
    try:
        return NotificationManager(primary, fallback)
    except Exception as e:
        logger.error(f"Failed to initialize notification manager: {e}")
        return None

notification_manager = _init_notification_manager()


# ==================== Backward Compatibility Functions ====================

def send_sms(to_number: str, body: str) -> bool:
    """
    Send SMS message using the configured provider.
    
    Args:
        to_number: Recipient phone number
        body: Message body
        
    Returns:
        True if sent successfully, False otherwise
    """
    if notification_manager is None:
        logger.error("Notification manager not initialized")
        return False
    
    result = notification_manager.send_sms(to_number, body)
    return result.get("success", False)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send email message using the configured provider.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body
        
    Returns:
        True if sent successfully, False otherwise
    """
    if notification_manager is None:
        logger.error("Notification manager not initialized")
        return False
    
    result = notification_manager.send_email(to_email, subject, body)
    return result.get("success", False)


def send_whatsapp(to_number: str, body: str) -> bool:
    """
    Send WhatsApp message using the configured provider.
    
    Args:
        to_number: Recipient WhatsApp number
        body: Message body
        
    Returns:
        True if sent successfully, False otherwise
    """
    if notification_manager is None:
        logger.error("Notification manager not initialized")
        return False
    
    result = notification_manager.send_whatsapp(to_number, body)
    return result.get("success", False)


def send_invoice_message(
    customer,
    invoice,
    method: Literal["email", "sms", "whatsapp", "all"] = "all"
) -> bool:
    """
    Send invoice to customer via specified method.
    
    Args:
        customer: Customer object with email, phone attributes
        invoice: Invoice object with id, amount, due_date, status, location
        method: Delivery method ("email", "sms", "whatsapp", or "all")
        
    Returns:
        bool: True if at least one delivery method succeeded
    """
    if notification_manager is None:
        logger.error("Notification manager not initialized")
        return False
    
    due = invoice.due_date
    body = (
        f"Invoice #{invoice.id}\n"
        f"Amount: {invoice.amount}\n"
        f"Location: {invoice.location or getattr(customer, 'location', '')}\n"
        f"Due: {due}\n"
        f"Status: {invoice.status}\n"
    )
    subject = f"Invoice #{invoice.id} - Amount {invoice.amount}"

    sent_any = False

    if method in ("email", "all") and getattr(customer, "email", None):
        if send_email(customer.email, subject, body):
            sent_any = True

    # For SMS/WhatsApp: customer.phone should include country code
    if method in ("sms", "all") and getattr(customer, "phone", None):
        if send_sms(customer.phone, body):
            sent_any = True

    if method == "whatsapp" and getattr(customer, "phone", None):
        if send_whatsapp(customer.phone, body):
            sent_any = True

    if not sent_any:
        logger.info(
            f"No delivery performed for customer {getattr(customer, 'id', '<no-id>')}; "
            f"would have sent via {method}"
        )

    return sent_any


# ==================== Advanced Functions ====================

def get_notification_status() -> dict:
    """
    Get the current notification provider status.
    
    Returns:
        Dictionary with provider information
    """
    if notification_manager is None:
        return {
            "initialized": False,
            "primary_provider": None,
            "fallback_provider": None,
            "status": "Not initialized"
        }
    
    return {
        "initialized": True,
        "primary_provider": notification_manager.get_active_provider(),
        "fallback_available": notification_manager.is_fallback_available(),
        "status": "Active"
    }


def check_provider_balance() -> dict:
    """
    Check the balance of the current provider.
    
    Returns:
        Dictionary with balance information
    """
    if notification_manager is None:
        return {"success": False, "error": "Notification manager not initialized"}
    
    return notification_manager.check_balance()


def switch_provider(provider_name: str) -> bool:
    """
    Switch to a different notification provider at runtime.
    
    Args:
        provider_name: Name of the provider to switch to
        
    Returns:
        True if switch successful, False otherwise
    """
    global notification_manager
    
    try:
        new_manager = NotificationManager(provider_name)
        notification_manager = new_manager
        logger.info(f"Switched to provider: {provider_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to switch provider: {e}")
        return False


__all__ = [
    # Core functions
    "send_sms",
    "send_email",
    "send_whatsapp",
    "send_invoice_message",
    
    # Advanced functions
    "get_notification_status",
    "check_provider_balance",
    "switch_provider",
]

