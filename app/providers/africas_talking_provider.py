"""
Africa's Talking Notification Provider.

This module implements the Africa's Talking SMS provider for the
pluggable notification architecture. Africa's Talking is a leading
SMS provider in Africa with coverage across multiple countries.

API Documentation: https://www.africastalking.com/docs/sms/send
"""
import requests
from typing import Dict, Any
import logging
from .base_provider import BaseNotificationProvider, NotificationResult

logger = logging.getLogger("notify")


class AfricasTalkingProvider(BaseNotificationProvider):
    """Africa's Talking SMS provider."""

    # Base URLs for different environments
    SANDBOX_URL = "https://api.sandbox.africastalking.com"
    PRODUCTION_URL = "https://api.africastalking.com"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Africa's Talking provider.
        
        Args:
            config: Configuration dictionary with:
                - api_key: Africa's Talking API key
                - username: Africa's Talking account username
                - is_sandbox: Use sandbox environment (default: True for testing)
                - supports_whatsapp: Enable WhatsApp support if API supports it
        """
        # Set default for sandbox mode
        if "is_sandbox" not in config:
            config["is_sandbox"] = True
        super().__init__(config)

    @property
    def base_url(self) -> str:
        """Get the appropriate base URL based on environment."""
        return self.SANDBOX_URL if self.config.get("is_sandbox", True) else self.PRODUCTION_URL

    def validate_config(self) -> None:
        """Validate Africa's Talking configuration."""
        required_keys = ["api_key", "username"]
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                raise ValueError(f"Missing Africa's Talking configuration: {key}")

    def send_sms(self, phone_number: str, message: str) -> NotificationResult:
        """Send SMS via Africa's Talking."""
        try:
            # Africa's Talking expects phone numbers in international format
            url = f"{self.base_url}/version1/messaging"
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {self.config['api_key']}"
            }

            data = {
                "username": self.config["username"],
                "to": phone_number,
                "message": message,
            }

            resp = requests.post(url, data=data, headers=headers, timeout=10)

            if resp.status_code == 201:
                resp_json = resp.json()
                # Parse Africa's Talking response
                recipients = resp_json.get("SMSMessageData", {}).get("Recipients", [])
                if recipients:
                    recipient = recipients[0]
                    if recipient.get("status") == "Success":
                        message_id = recipient.get("messageId")
                        logger.info(f"Sent Africa's Talking SMS to {phone_number} (ID: {message_id})")
                        return NotificationResult(
                            success=True,
                            message_id=message_id,
                            provider="Africa's Talking"
                        )
                    else:
                        error = f"Africa's Talking API error: {recipient.get('status', 'Unknown error')} - {recipient.get('statusCode')}"
                        logger.error(error)
                        return NotificationResult(
                            success=False,
                            error=error,
                            provider="Africa's Talking"
                        )
                else:
                    error = f"Africa's Talking API error: No recipients in response"
                    logger.error(error)
                    return NotificationResult(
                        success=False,
                        error=error,
                        provider="Africa's Talking"
                    )
            else:
                error = f"Africa's Talking API error ({resp.status_code}): {resp.text}"
                logger.error(error)
                return NotificationResult(
                    success=False,
                    error=error,
                    provider="Africa's Talking"
                )
        except requests.exceptions.Timeout:
            error = "Africa's Talking API timeout"
            logger.error(error)
            return NotificationResult(
                success=False,
                error=error,
                provider="Africa's Talking"
            )
        except Exception as e:
            error = f"Africa's Talking send error: {str(e)}"
            logger.exception(error)
            return NotificationResult(
                success=False,
                error=error,
                provider="Africa's Talking"
            )

    def send_whatsapp(self, phone_number: str, message: str) -> NotificationResult:
        """
        Send WhatsApp via Africa's Talking.
        
        Note: Africa's Talking WhatsApp support is limited and may require
        additional configuration. Returns not supported if not enabled.
        """
        # Check if WhatsApp is supported in configuration
        if not self.config.get("supports_whatsapp", False):
            return NotificationResult(
                success=False,
                error="WhatsApp not enabled for Africa's Talking provider. Set 'supports_whatsapp' to true if your account supports it.",
                provider="Africa's Talking"
            )

        try:
            url = f"{self.base_url}/version1/messaging"
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {self.config['api_key']}"
            }

            data = {
                "username": self.config["username"],
                "to": phone_number,
                "message": message,
                "channel": "whatsapp",  # Specify WhatsApp channel
            }

            resp = requests.post(url, data=data, headers=headers, timeout=10)

            if resp.status_code == 201:
                resp_json = resp.json()
                recipients = resp_json.get("SMSMessageData", {}).get("Recipients", [])
                if recipients:
                    recipient = recipients[0]
                    if recipient.get("status") == "Success":
                        message_id = recipient.get("messageId")
                        logger.info(f"Sent Africa's Talking WhatsApp to {phone_number} (ID: {message_id})")
                        return NotificationResult(
                            success=True,
                            message_id=message_id,
                            provider="Africa's Talking WhatsApp"
                        )
                
                error = f"Africa's Talking WhatsApp error: {resp_json}"
                logger.error(error)
                return NotificationResult(
                    success=False,
                    error=error,
                    provider="Africa's Talking WhatsApp"
                )
            else:
                error = f"Africa's Talking API error ({resp.status_code}): {resp.text}"
                logger.error(error)
                return NotificationResult(
                    success=False,
                    error=error,
                    provider="Africa's Talking WhatsApp"
                )
        except Exception as e:
            error = f"Africa's Talking WhatsApp send error: {str(e)}"
            logger.exception(error)
            return NotificationResult(
                success=False,
                error=error,
                provider="Africa's Talking WhatsApp"
            )

    def send_email(self, email: str, subject: str, body: str) -> NotificationResult:
        """Africa's Talking doesn't provide email service; return not supported."""
        return NotificationResult(
            success=False,
            error="Email sending not supported by Africa's Talking provider. Use Twilio or SMTP instead.",
            provider="Africa's Talking"
        )

    def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance.
        
        Returns:
            Dictionary with balance information
        """
        try:
            url = f"{self.base_url}/version1/user"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config['api_key']}"
            }
            
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                resp_json = resp.json()
                user_data = resp_json.get("UserData", {})
                return {
                    "success": True,
                    "balance": user_data.get("balance"),
                    "currency": user_data.get("currency"),
                    "phone_number": user_data.get("phoneNumber"),
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get balance: {resp.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def supports_feature(self, feature: str) -> bool:
        """Check if provider supports a specific feature."""
        if feature == "sms":
            return all([
                self.config.get("api_key"),
                self.config.get("username")
            ])
        elif feature == "whatsapp":
            return all([
                self.config.get("api_key"),
                self.config.get("username"),
                self.config.get("supports_whatsapp", False)
            ])
        elif feature == "email":
            return False
        return False

