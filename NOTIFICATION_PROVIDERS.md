# Africa's Talking Notification Provider

This document describes the notification provider architecture for the Water Billing System using Africa's Talking SMS service.

## Overview

The notification module uses Africa's Talking as the SMS provider for sending notifications to customers. The architecture is designed to be extensible for adding additional providers in the future.

## Provider

### AfricasTalkingProvider
- **Features**: SMS, WhatsApp (if supported)
- **Configuration**:
  - `AFRICAS_TALKING_API_KEY`
  - `AFRICAS_TALKING_USERNAME`
  - `AFRICAS_TALKING_IS_SANDBOX` (default: true)
  - `AFRICAS_TALKING_SUPPORTS_WHATSAPP`

## Usage

### Basic Usage

```python
from app.notify import send_sms, send_email, send_invoice_message

# Send SMS
send_sms("+254712345678", "Your water bill is ready")

# Send email
send_email("customer@email.com", "Invoice #123", "Please find attached...")

# Send invoice via all channels
send_invoice_message(customer, invoice, method="all")
```

### Advanced Usage

```python
from app.providers import ProviderFactory, NotificationManager

# Get a specific provider
provider = ProviderFactory.get_provider("africas_talking")

# Create manager with fallback
manager = NotificationManager(
    primary_provider="africas_talking",
    fallback_provider=None  # Configure if needed
)

# Send SMS
result = manager.send_sms("+254712345678", "Message")
if not result["success"]:
    print(f"Failed: {result['error']}")

# Check provider status
status = manager.get_active_provider()  # "AfricasTalkingProvider"

# Check balance
balance = manager.check_balance()
```

### Adding a New Provider

```python
from app.providers import BaseNotificationProvider, NotificationResult

class MyCustomProvider(BaseNotificationProvider):
    """Custom SMS provider implementation."""
    
    def validate_config(self):
        """Validate required config."""
        if not self.config.get("api_key"):
            raise ValueError("Missing api_key")
    
    def send_sms(self, phone_number, message):
        """Send SMS via custom API."""
        return NotificationResult(success=True, message_id="xxx")
    
    def send_email(self, email, subject, body):
        return NotificationResult(success=False, error="Not implemented")
    
    def send_whatsapp(self, phone_number, message):
        return NotificationResult(success=False, error="Not implemented")

# Register the provider
ProviderFactory.register_provider("custom", MyCustomProvider)

# Use it
provider = ProviderFactory.get_provider("custom")
```

## Configuration

### Environment Variables

```bash
# Africa's Talking Configuration
# Get credentials from: https://account.africastalking.com
AFRICAS_TALKING_API_KEY=your_api_key
AFRICAS_TALKING_USERNAME=your_username
AFRICAS_TALKING_IS_SANDBOX=true  # Set to false for production
AFRICAS_TALKING_SUPPORTS_WHATSAPP=false

# Optional: Provider Selection (defaults to africas_talking)
# SMS_PROVIDER=africas_talking

# Optional: Fallback Provider
# SMS_FALLBACK_PROVIDER=
```

## API Reference

### BaseNotificationProvider

```python
class BaseNotificationProvider:
    def __init__(self, config: Dict[str, Any])
    def validate_config(self) -> None
    def send_sms(self, phone: str, message: str) -> NotificationResult
    def send_email(self, email: str, subject: str, body: str) -> NotificationResult
    def send_whatsapp(self, phone: str, message: str) -> NotificationResult
    def get_provider_name(self) -> str
    def get_balance(self) -> Dict[str, Any]
    def supports_feature(self, feature: str) -> bool
```

### NotificationManager

```python
class NotificationManager:
    def __init__(self, primary_provider, fallback_provider=None)
    def send_sms(phone: str, message: str) -> Dict[str, Any]
    def send_email(email: str, subject: str, body: str) -> Dict[str, Any]
    def send_whatsapp(phone: str, message: str) -> Dict[str, Any]
    def get_active_provider() -> str
    def is_fallback_available() -> bool
    def check_balance() -> Dict[str, Any]
```

### NotificationResult

```python
@dataclass
class NotificationResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]
```

## Running Tests

```bash
# Run provider tests
pytest tests/test_providers.py -v

# Run with coverage
pytest tests/test_providers.py --cov=app/providers
```

## Africa's Talking Features

| Feature | Supported |
|---------|-----------|
| SMS | ✓ |
| WhatsApp | Limited (requires account support) |
| Email | ✗ |
| Balance Check | ✓ |
| Sandbox Mode | ✓ |

## Error Handling

All providers return `NotificationResult` with consistent error handling:

```python
result = provider.send_sms("+254712345678", "Test")

if result.success:
    print(f"Sent: {result.message_id}")
else:
    print(f"Failed: {result.error}")
    print(f"Provider: {result.provider}")
```

## Best Practices

1. **Validate Config**: Use `validate_config()` in custom providers
2. **Log Errors**: All providers log errors with the `logger`
3. **Feature Flags**: Use `supports_feature()` to check capabilities
4. **Graceful Degradation**: Return meaningful errors when features are unavailable

## License

This module is part of the Water Billing System.

