"""
Comprehensive Africa Talking API Test Script.

This script tests the Africa's Talking SMS provider with:
1. Unit tests (mocked) - always works
2. Integration tests - requires real API credentials in .env

Usage:
    python test_africas_talking.py

Environment variables required for integration tests:
    AFRICAS_TALKING_API_KEY=your_api_key
    AFRICAS_TALKING_USERNAME=your_username
    AFRICAS_TALKING_IS_SANDBOX=true  # or false for production
"""
import os
import sys
import logging
from unittest.mock import patch, MagicMock

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_africas_talking")

# Try to import dotenv, but continue if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env")
except ImportError:
    logger.warning("python-dotenv not installed, using system environment variables")

from app.providers.africas_talking_provider import AfricasTalkingProvider
from app.providers.provider_factory import ProviderFactory, NotificationManager
from app.providers.base_provider import NotificationResult


def test_config_validation():
    """Test configuration validation."""
    print("\n" + "="*60)
    print("TEST: Configuration Validation")
    print("="*60)
    
    # Test valid config
    config = {
        "api_key": "test_key",
        "username": "test_user",
    }
    provider = AfricasTalkingProvider(config)
    assert provider.config["api_key"] == "test_key"
    assert provider.config["username"] == "test_user"
    print("✓ Valid config works correctly")
    
    # Test default sandbox mode
    assert provider.base_url == provider.SANDBOX_URL
    print("✓ Default sandbox mode works")
    
    # Test production mode
    config_prod = {
        "api_key": "test_key",
        "username": "test_user",
        "is_sandbox": False,
    }
    provider_prod = AfricasTalkingProvider(config_prod)
    assert provider_prod.base_url == provider.PRODUCTION_URL
    print("✓ Production mode works")
    
    # Test missing API key
    try:
        AfricasTalkingProvider({"username": "test"})
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "api_key" in str(e)
        print("✓ Missing API key raises ValueError")
    
    # Test missing username
    try:
        AfricasTalkingProvider({"api_key": "test"})
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "username" in str(e)
        print("✓ Missing username raises ValueError")


def test_feature_support():
    """Test feature support detection."""
    print("\n" + "="*60)
    print("TEST: Feature Support")
    print("="*60)
    
    config = {
        "api_key": "test_key",
        "username": "test_user",
    }
    provider = AfricasTalkingProvider(config)
    
    # SMS should be supported
    assert provider.supports_feature("sms") == True
    print("✓ SMS feature supported")
    
    # Email should NOT be supported
    assert provider.supports_feature("email") == False
    print("✓ Email feature not supported")
    
    # WhatsApp should NOT be supported by default
    assert provider.supports_feature("whatsapp") == False
    print("✓ WhatsApp not supported by default")
    
    # Test with WhatsApp enabled
    config_wa = {
        "api_key": "test_key",
        "username": "test_user",
        "supports_whatsapp": True,
    }
    provider_wa = AfricasTalkingProvider(config_wa)
    assert provider_wa.supports_feature("whatsapp") == True
    print("✓ WhatsApp supported when enabled")


def test_send_sms_mock():
    """Test SMS sending with mocked responses."""
    print("\n" + "="*60)
    print("TEST: Send SMS (Mocked)")
    print("="*60)
    
    config = {"api_key": "test_key", "username": "test_user"}
    provider = AfricasTalkingProvider(config)
    
    # Mock successful response
    with patch.object(provider.session, 'post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {"status": "Success", "messageId": "ATXid123456789"}
                ]
            }
        }
        mock_post.return_value = mock_response
        
        result = provider.send_sms("+254715257415", "Test message")
        
        assert result.success == True
        assert result.message_id == "ATXid123456789"
        assert result.provider == "Africa's Talking"
        print("✓ Successful SMS mock works")
    
    # Mock API error
    with patch.object(provider.session, 'post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_post.return_value = mock_response
        
        result = provider.send_sms("+254715257415", "Test message")
        assert result.success == False
        assert "API error" in result.error
        print("✓ API error handling works")
    
    # Mock recipient error
    with patch.object(provider.session, 'post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {"status": "Failed", "statusCode": 101, "error": "Invalid phone number"}
                ]
            }
        }
        mock_post.return_value = mock_response
        
        result = provider.send_sms("+254712345678", "Test message")
        
        assert result.success == False
        assert "Failed" in result.error
        print("✓ Recipient error handling works")


def test_send_whatsapp_mock():
    """Test WhatsApp sending with mocked responses."""
    print("\n" + "="*60)
    print("TEST: Send WhatsApp (Mocked)")
    print("="*60)
    
    config = {"api_key": "test_key", "username": "test_user", "supports_whatsapp": True}
    provider = AfricasTalkingProvider(config)
    
    with patch.object(provider.session, 'post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {"status": "Success", "messageId": "ATXid_whatsapp123"}
                ]
            }
        }
        mock_post.return_value = mock_response
        
        result = provider.send_whatsapp("+254712345678", "Test WhatsApp message")
        
        assert result.success == True
        assert result.message_id == "ATXid_whatsapp123"
        print("✓ WhatsApp mock works")
    
    # Test WhatsApp not enabled
    config_no_wa = {"api_key": "test_key", "username": "test_user"}
    provider_no_wa = AfricasTalkingProvider(config_no_wa)
    result = provider_no_wa.send_whatsapp("+254712345678", "Test")
    
    assert result.success == False
    assert "not enabled" in result.error
    print("✓ WhatsApp not enabled error works")


def test_email_not_supported():
    """Test that email is not supported."""
    print("\n" + "="*60)
    print("TEST: Email Not Supported")
    print("="*60)
    
    config = {"api_key": "test_key", "username": "test_user"}
    provider = AfricasTalkingProvider(config)
    
    result = provider.send_email("test@example.com", "Subject", "Body")
    
    assert result.success == False
    assert "not supported" in result.error
    print("✓ Email not supported works")


def test_get_balance_mock():
    """Test balance check with mocked responses."""
    print("\n" + "="*60)
    print("TEST: Get Balance (Mocked)")
    print("="*60)
    
    config = {"api_key": "test_key", "username": "test_user"}
    provider = AfricasTalkingProvider(config)
    
    with patch.object(provider.session, 'get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "UserData": {
                "balance": "KES 500.00",
                "currency": "KES",
                "phoneNumber": "+254700000000"
            }
        }
        mock_get.return_value = mock_response
        
        result = provider.get_balance()
        
        assert result["success"] == True
        assert result["balance"] == "KES 500.00"
        assert result["currency"] == "KES"
        print("✓ Balance check mock works")


def test_provider_factory():
    """Test the provider factory."""
    print("\n" + "="*60)
    print("TEST: Provider Factory")
    print("="*60)
    
    # Test getting Africa Talking provider
    config = {"api_key": "test", "username": "test"}
    provider = ProviderFactory.get_provider("africas_talking", config)
    assert isinstance(provider, AfricasTalkingProvider)
    print("✓ Factory returns AfricasTalkingProvider")
    
    # Test alias
    provider2 = ProviderFactory.get_provider("africa_talking", config)
    assert isinstance(provider2, AfricasTalkingProvider)
    print("✓ Factory alias works")
    
    # Test list providers
    providers = ProviderFactory.list_providers()
    assert "africas_talking" in providers
    print("✓ List providers works")


def test_notification_manager():
    """Test the notification manager."""
    print("\n" + "="*60)
    print("TEST: Notification Manager")
    print("="*60)
    
    config = {"api_key": "test", "username": "test"}
    
    # Test with primary only
    manager = NotificationManager("africas_talking", primary_config=config)
    assert manager.get_active_provider() == "AfricasTalkingProvider"
    assert manager.is_fallback_available() == False
    print("✓ NotificationManager primary only works")
    
    # Test with fallback
    manager_with_fb = NotificationManager(
        "africas_talking", 
        "africas_talking",
        primary_config=config,
        fallback_config=config
    )
    assert manager_with_fb.is_fallback_available() == True
    print("✓ NotificationManager with fallback works")


def test_integration_with_credentials():
    """Test with real Africa Talking API credentials."""
    print("\n" + "="*60)
    print("TEST: Integration with Real Credentials")
    print("="*60)
    
    api_key = os.getenv("AFRICAS_TALKING_API_KEY")
    username = os.getenv("AFRICAS_TALKING_USERNAME")
    
    if not api_key or not username:
        print("⚠ Skipping integration test - no credentials found")
        print("  Set AFRICAS_TALKING_API_KEY and AFRICAS_TALKING_USERNAME in .env")
        return
    
    print(f"Testing with username: {username}")
    print(f"Sandbox mode: {os.getenv('AFRICAS_TALKING_IS_SANDBOX', 'true')}")
    
    # Check if we should skip SSL verification (for Windows/testing)
    verify_ssl = os.getenv("AFRICAS_TALKING_VERIFY_SSL", "true").lower() == "true"
    
    config = {
        "api_key": api_key,
        "username": username,
        "is_sandbox": os.getenv("AFRICAS_TALKING_IS_SANDBOX", "true").lower() == "true",
        "verify_ssl": verify_ssl,
    }
    
    provider = AfricasTalkingProvider(config)
    
    # Suppress urllib3 warnings if SSL verification is disabled
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Test 1: Check balance
    print("\n1. Checking account balance...")
    balance = provider.get_balance()
    if balance.get("success"):
        print(f"   ✓ Balance: {balance.get('balance')} {balance.get('currency')}")
    else:
        print(f"   ✗ Balance check failed: {balance.get('error')}")
    
    # Test 2: Send SMS (to your own verified number)
    # NOTE: In sandbox, you can only send to registered phone numbers
    test_phone = os.getenv("TEST_PHONE_NUMBER", "+254715257415")  # Default test number
    test_message = "Test message from Water Billing System - Africa Talking API Test"
    
    print(f"\n2. Sending SMS to {test_phone}...")
    result = provider.send_sms(test_phone, test_message)
    
    if result.success:
        print(f"   ✓ SMS sent successfully!")
        print(f"   Message ID: {result.message_id}")
    else:
        print(f"   ✗ SMS failed: {result.error}")
        print("   Note: In sandbox mode, phone number must be verified")
    
    # Test 3: Test feature support
    print("\n3. Feature support:")
    print(f"   SMS: {provider.supports_feature('sms')}")
    print(f"   WhatsApp: {provider.supports_feature('whatsapp')}")
    print(f"   Email: {provider.supports_feature('email')}")


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# AFRICA'S TALKING API TEST SUITE")
    print("#"*60)
    
    # Run unit tests (always work)
    test_config_validation()
    test_feature_support()
    test_send_sms_mock()
    test_send_whatsapp_mock()
    test_email_not_supported()
    test_get_balance_mock()
    test_provider_factory()
    test_notification_manager()
    
    # Run integration tests (requires credentials)
    test_integration_with_credentials()
    
    print("\n" + "#"*60)
    print("# ALL TESTS COMPLETED")
    print("#"*60 + "\n")


if __name__ == "__main__":
    main()

