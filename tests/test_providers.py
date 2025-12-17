"""
Unit Tests for Notification Providers.

This module contains comprehensive tests for the Africa's Talking notification provider.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.providers.base_provider import BaseNotificationProvider, NotificationResult, ProviderFeatures
from app.providers.africas_talking_provider import AfricasTalkingProvider
from app.providers.provider_factory import ProviderFactory, NotificationManager


class TestNotificationResult:
    """Tests for NotificationResult dataclass."""

    def test_success_result(self):
        """Test successful result creation."""
        result = NotificationResult(
            success=True,
            message_id="msg123",
            provider="Africa's Talking"
        )
        assert result.success is True
        assert result.message_id == "msg123"
        assert result.error is None
        assert result.provider == "Africa's Talking"

    def test_failure_result(self):
        """Test failure result creation."""
        result = NotificationResult(
            success=False,
            error="Failed to send"
        )
        assert result.success is False
        assert result.error == "Failed to send"
        assert result.message_id is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = NotificationResult(
            success=True,
            message_id="msg123",
            provider="Africa's Talking"
        )
        result_dict = result.to_dict()
        assert result_dict == {
            "success": True,
            "message_id": "msg123",
            "error": None,
            "provider": "Africa's Talking",
        }


class TestProviderFeatures:
    """Tests for ProviderFeatures class."""

    def test_all_features(self):
        """Test that all features are returned."""
        features = ProviderFeatures.all_features()
        assert "sms" in features
        assert "email" in features
        assert "whatsapp" in features


class TestBaseNotificationProvider:
    """Tests for BaseNotificationProvider abstract class."""

    def test_get_provider_name(self):
        """Test provider name extraction."""
        class TestProvider(BaseNotificationProvider):
            def validate_config(self): 
                pass
            def send_sms(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_email(self, email: str, subject: str, body: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_whatsapp(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
        
        config = {"test_key": "test_value"}
        provider = TestProvider(config)
        assert provider.get_provider_name() == "TestProvider"

    def test_default_supports_feature(self):
        """Test default supports_feature returns False."""
        class TestProvider(BaseNotificationProvider):
            def validate_config(self): 
                pass
            def send_sms(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_email(self, email: str, subject: str, body: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_whatsapp(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
        
        config = {"test_key": "test_value"}
        provider = TestProvider(config)
        assert provider.supports_feature("sms") is False
        assert provider.supports_feature("email") is False

    def test_default_get_balance(self):
        """Test default get_balance returns not supported."""
        class TestProvider(BaseNotificationProvider):
            def validate_config(self): 
                pass
            def send_sms(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_email(self, email: str, subject: str, body: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_whatsapp(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
        
        config = {"test_key": "test_value"}
        provider = TestProvider(config)
        result = provider.get_balance()
        assert result["success"] is False
        assert "not supported" in result.get("error", "")


class TestAfricasTalkingProvider:
    """Tests for AfricasTalkingProvider."""

    def test_init_valid_config(self):
        """Test initialization with valid config."""
        config = {
            "api_key": "test_key",
            "username": "test_user",
        }
        provider = AfricasTalkingProvider(config)
        assert provider.get_provider_name() == "AfricasTalkingProvider"
        assert provider.base_url == provider.SANDBOX_URL  # Default is sandbox

    def test_init_production_config(self):
        """Test initialization with production config."""
        config = {
            "api_key": "test_key",
            "username": "test_user",
            "is_sandbox": False,
        }
        provider = AfricasTalkingProvider(config)
        assert provider.base_url == provider.PRODUCTION_URL

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        config = {"username": "test_user"}
        with pytest.raises(ValueError, match="Missing Africa's Talking configuration"):
            AfricasTalkingProvider(config)

    def test_supports_feature_sms(self):
        """Test SMS feature support."""
        config = {
            "api_key": "test_key",
            "username": "test_user",
        }
        provider = AfricasTalkingProvider(config)
        assert provider.supports_feature("sms") is True
        assert provider.supports_feature("email") is False
        assert provider.supports_feature("whatsapp") is False

    def test_supports_feature_whatsapp(self):
        """Test WhatsApp feature support when enabled."""
        config = {
            "api_key": "test_key",
            "username": "test_user",
            "supports_whatsapp": True,
        }
        provider = AfricasTalkingProvider(config)
        assert provider.supports_feature("whatsapp") is True

    @patch("requests.post")
    def test_send_sms_success(self, mock_post):
        """Test successful SMS sending."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {"status": "Success", "messageId": "msg123"}
                ]
            }
        }
        mock_post.return_value = mock_response

        config = {"api_key": "test_key", "username": "test_user"}
        provider = AfricasTalkingProvider(config)
        result = provider.send_sms("+254712345678", "Test message")

        assert result.success is True
        assert result.message_id == "msg123"
        assert result.provider == "Africa's Talking"

    @patch("requests.post")
    def test_send_sms_api_error(self, mock_post):
        """Test SMS sending with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_post.return_value = mock_response

        config = {"api_key": "test_key", "username": "test_user"}
        provider = AfricasTalkingProvider(config)
        result = provider.send_sms("+254712345678", "Test message")

        assert result.success is False
        assert "API error" in result.error

    @patch("requests.post")
    def test_send_sms_recipient_error(self, mock_post):
        """Test SMS sending with recipient error."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {"status": "Failed", "statusCode": 101}
                ]
            }
        }
        mock_post.return_value = mock_response

        config = {"api_key": "test_key", "username": "test_user"}
        provider = AfricasTalkingProvider(config)
        result = provider.send_sms("+254712345678", "Test message")

        assert result.success is False

    def test_send_whatsapp_not_enabled(self):
        """Test WhatsApp sending when not enabled."""
        config = {"api_key": "test_key", "username": "test_user"}
        provider = AfricasTalkingProvider(config)
        result = provider.send_whatsapp("+254712345678", "Test message")

        assert result.success is False
        assert "WhatsApp not enabled" in result.error

    def test_send_email_not_supported(self):
        """Test email sending returns not supported."""
        config = {"api_key": "test_key", "username": "test_user"}
        provider = AfricasTalkingProvider(config)
        result = provider.send_email("test@test.com", "Subject", "Body")

        assert result.success is False
        assert "not supported" in result.error

    @patch("requests.get")
    def test_get_balance_success(self, mock_get):
        """Test getting account balance."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "UserData": {
                "balance": "NGN 500.00",
                "currency": "NGN",
                "phoneNumber": "+2347088888888"
            }
        }
        mock_get.return_value = mock_response

        config = {"api_key": "test_key", "username": "test_user"}
        provider = AfricasTalkingProvider(config)
        result = provider.get_balance()

        assert result["success"] is True
        assert result["balance"] == "NGN 500.00"


class TestProviderFactory:
    """Tests for ProviderFactory."""

    def test_get_africas_talking_provider(self):
        """Test getting Africa's Talking provider."""
        config = {
            "api_key": "test",
            "username": "test"
        }
        provider = ProviderFactory.get_provider("africas_talking", config)
        assert isinstance(provider, AfricasTalkingProvider)

    def test_get_africa_talking_alias(self):
        """Test Africa's Talking alias."""
        config = {
            "api_key": "test",
            "username": "test"
        }
        provider = ProviderFactory.get_provider("africa_talking", config)
        assert isinstance(provider, AfricasTalkingProvider)

    def test_invalid_provider(self):
        """Test error on invalid provider name."""
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.get_provider("invalid_provider", {})

    def test_list_providers(self):
        """Test listing available providers."""
        providers = ProviderFactory.list_providers()
        assert "africas_talking" in providers

    def test_register_provider(self):
        """Test registering a new provider."""
        class DummyProvider(BaseNotificationProvider):
            def validate_config(self): 
                pass
            def send_sms(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_email(self, email: str, subject: str, body: str) -> NotificationResult:
                return NotificationResult(success=True)
            def send_whatsapp(self, phone_number: str, message: str) -> NotificationResult:
                return NotificationResult(success=True)
        
        ProviderFactory.register_provider("dummy", DummyProvider)
        assert "dummy" in ProviderFactory.list_providers()


class TestNotificationManager:
    """Tests for NotificationManager."""

    def test_init_primary_only(self):
        """Test initialization with only primary provider."""
        config = {
            "api_key": "test_key",
            "username": "test_user",
        }
        manager = NotificationManager("africas_talking", primary_config=config)
        assert manager.get_active_provider() == "AfricasTalkingProvider"
        assert manager.is_fallback_available() is False

    @patch.object(AfricasTalkingProvider, "send_sms")
    def test_init_with_fallback(self, mock_at_sms):
        """Test initialization with fallback provider."""
        at_config = {"api_key": "test_key", "username": "test_user"}
        
        manager = NotificationManager(
            "africas_talking", 
            "africas_talking",  # Same provider for fallback test
            primary_config=at_config,
            fallback_config=at_config
        )
        assert manager.get_active_provider() == "AfricasTalkingProvider"
        assert manager.is_fallback_available() is True

    @patch.object(AfricasTalkingProvider, "send_sms")
    def test_send_sms_success(self, mock_at_sms):
        """Test SMS sending success."""
        mock_at_sms.return_value = NotificationResult(
            success=True,
            message_id="msg123",
            provider="Africa's Talking"
        )

        config = {"api_key": "test_key", "username": "test_user"}
        manager = NotificationManager("africas_talking", primary_config=config)
        result = manager.send_sms("+254712345678", "Test message")

        assert result["success"] is True
        assert result["message_id"] == "msg123"

    @patch.object(AfricasTalkingProvider, "send_sms")
    def test_send_sms_failure(self, mock_at_sms):
        """Test SMS sending failure."""
        mock_at_sms.return_value = NotificationResult(
            success=False,
            error="Network error",
            provider="Africa's Talking"
        )

        config = {"api_key": "test_key", "username": "test_user"}
        manager = NotificationManager("africas_talking", primary_config=config)
        result = manager.send_sms("+254712345678", "Test message")

        assert result["success"] is False
        assert "Network error" in result["error"]

    @patch.object(AfricasTalkingProvider, "send_sms")
    def test_fallback_on_primary_failure(self, mock_at_sms):
        """Test fallback when primary provider fails."""
        mock_at_sms.return_value = NotificationResult(
            success=False,
            error="Primary error",
            provider="Africa's Talking"
        )

        config = {"api_key": "test_key", "username": "test_user"}

        manager = NotificationManager(
            "africas_talking", 
            "africas_talking",
            primary_config=config,
            fallback_config=config
        )

        result = manager.send_sms("+254712345678", "Test message")

        assert result["success"] is False  # Fallback also fails
        assert mock_at_sms.call_count == 2  # Both primary and fallback called

    @patch.object(AfricasTalkingProvider, "get_balance")
    def test_check_balance(self, mock_get_balance):
        """Test balance check."""
        mock_get_balance.return_value = {
            "success": False, 
            "error": "Balance check not supported by this provider"
        }
        
        config = {"api_key": "test_key", "username": "test_user"}
        manager = NotificationManager("africas_talking", primary_config=config)
        result = manager.check_balance()
        
        assert result["success"] is False
        assert "not supported" in result["error"]


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

