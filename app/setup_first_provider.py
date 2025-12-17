"""
Provider Onboarding Script for Multi-Tenant Water Billing System.
Interactive script to create the first provider and admin user.
"""
import os
import sys
import logging
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import mongodb_multitenant as mt_db
from app import crud_providers
from app.models import ProviderSettings, ProviderBranding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup_provider")


def welcome_message():
    """Print welcome message."""
    print("\n" + "=" * 60)
    print("  MULTI-TENANT WATER BILLING SYSTEM")
    print("  Provider Onboarding Wizard")
    print("=" * 60)
    print()


def check_prerequisites() -> bool:
    """Check if prerequisites are met."""
    print("Checking prerequisites...")
    
    # Check MongoDB connection
    if mt_db.is_master_connected():
        print("✓ MongoDB connection successful")
    else:
        print("✗ MongoDB connection failed!")
        print("  Please ensure MongoDB is running and .env is configured")
        return False
    
    # Initialize master collections if needed
    try:
        mt_db.init_master_collections()
        print("✓ Master database collections initialized")
    except Exception as e:
        print(f"✗ Failed to initialize master collections: {e}")
        return False
    
    print()
    return True


def get_provider_info() -> dict:
    """Get provider information from user."""
    print("-" * 40)
    print("PROVIDER INFORMATION")
    print("-" * 40)
    
    # Company name
    while True:
        name = input("Company Name: ").strip()
        if name and len(name) >= 2:
            break
        print("  Please enter a valid company name (at least 2 characters)")
    
    # Slug
    while True:
        slug = input("URL Slug [e.g., kiambu-water]: ").strip().lower()
        # Normalize slug
        slug = ''.join(c if c.isalnum() or c == '-' else '-' for c in slug)
        slug = slug.strip('-')
        
        if slug and len(slug) >= 2:
            # Check if slug is available
            if not crud_providers.provider_exists(slug):
                break
            print(f"  Slug '{slug}' is already taken. Please choose another.")
        print("  Please enter a valid slug (at least 2 characters, alphanumeric and hyphens only)")
    
    # Contact info
    contact_email = input("Contact Email (optional): ").strip() or None
    contact_phone = input("Contact Phone (optional): ").strip() or None
    address = input("Address (optional): ").strip() or None
    
    print()
    
    return {
        "name": name,
        "slug": slug,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "address": address
    }


def get_admin_info() -> dict:
    """Get admin user information from user."""
    print("-" * 40)
    print("ADMIN USER INFORMATION")
    print("-" * 40)
    
    # Username
    while True:
        username = input("Admin Username: ").strip()
        if username and len(username) >= 3:
            break
        print("  Username must be at least 3 characters")
    
    # Password
    while True:
        password = input("Admin Password: ").strip()
        if len(password) >= 8:
            # Confirm password
            password2 = input("Confirm Password: ").strip()
            if password == password2:
                break
            print("  Passwords do not match")
        else:
            print("  Password must be at least 8 characters")
    
    # Email
    email = input("Admin Email (optional): ").strip() or None
    
    # Full name
    full_name = input("Full Name (optional): ").strip() or None
    
    print()
    
    return {
        "username": username,
        "password": password,
        "email": email,
        "full_name": full_name
    }


def get_rate_config() -> dict:
    """Get rate configuration from user."""
    print("-" * 40)
    print("BILLING CONFIGURATION")
    print("-" * 40)
    
    # Rate per unit
    while True:
        try:
            rate_per_unit = float(input("Rate per Water Unit (KES) [default: 1.5]: ").strip() or "1.5")
            if rate_per_unit >= 0:
                break
            print("  Rate must be a positive number")
        except ValueError:
            print("  Please enter a valid number")
    
    # Currency
    currency = input("Currency [default: KES]: ").strip().upper() or "KES"
    
    # Billing cycle
    while True:
        try:
            billing_cycle = int(input("Billing Cycle (days) [default: 30]: ").strip() or "30")
            if 1 <= billing_cycle <= 365:
                break
            print("  Billing cycle must be between 1 and 365 days")
        except ValueError:
            print("  Please enter a valid number")
    
    # Payment due days
    while True:
        try:
            due_days = int(input("Payment Due Days [default: 15]: ").strip() or "15")
            if 1 <= due_days <= 90:
                break
            print("  Payment due days must be between 1 and 90")
        except ValueError:
            print("  Please enter a valid number")
    
    print()
    
    return {
        "rate_per_unit": rate_per_unit,
        "currency": currency,
        "billing_cycle_days": billing_cycle,
        "payment_due_days": due_days
    }


def get_branding_info() -> dict:
    """Get branding configuration from user."""
    print("-" * 40)
    print("BRANDING (Optional)")
    print("-" * 40)
    
    logo_url = input("Logo URL (optional): ").strip() or None
    primary_color = input("Primary Color (hex) [default: #3B82F6]: ").strip() or "#3B82F6"
    company_display = input("Display Name (optional): ").strip() or None
    website_url = input("Website URL (optional): ").strip() or None
    
    print()
    
    return {
        "logo_url": logo_url,
        "primary_color": primary_color,
        "company_name_display": company_display,
        "website_url": website_url
    }


def create_provider(provider_info: dict, admin_info: dict, rate_config: dict, branding_info: dict) -> bool:
    """Create provider and admin user."""
    try:
        # Build settings
        settings = ProviderSettings(
            rate_per_unit=rate_config["rate_per_unit"],
            currency=rate_config["currency"],
            billing_cycle_days=rate_config["billing_cycle_days"],
            payment_due_days=rate_config["payment_due_days"]
        )
        
        # Build branding
        branding = ProviderBranding(
            logo_url=branding_info.get("logo_url"),
            primary_color=branding_info.get("primary_color", "#3B82F6"),
            company_name_display=branding_info.get("company_name_display"),
            website_url=branding_info.get("website_url")
        )
        
        print("Creating provider...")
        
        # Create provider
        provider = crud_providers.create_provider({
            "name": provider_info["name"],
            "slug": provider_info["slug"],
            "contact_email": provider_info["contact_email"],
            "contact_phone": provider_info["contact_phone"],
            "address": provider_info["address"],
            "settings": settings.model_dump(),
            "branding": branding.model_dump(),
            "created_by": "setup_script"
        })
        
        print(f"✓ Provider created: {provider['name']}")
        print(f"  Database: {provider['database_name']}")
        print(f"  Slug: {provider['slug']}")
        
        # Create admin user
        admin = crud_providers.create_admin_user({
            "provider_slug": provider_info["slug"],
            "username": admin_info["username"],
            "password": admin_info["password"],
            "email": admin_info["email"],
            "full_name": admin_info["full_name"],
            "is_super_admin": True
        })
        
        print(f"✓ Admin user created: {admin['username']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create provider: {e}")
        print(f"✗ Error creating provider: {e}")
        return False


def print_summary(provider_info: dict, admin_info: dict):
    """Print setup summary."""
    print()
    print("=" * 60)
    print("  SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Provider Details:")
    print(f"  Name: {provider_info['name']}")
    print(f"  Slug: {provider_info['slug']}")
    print(f"  Database: wb_{provider_info['slug']}_xxxxxx")
    print()
    print("Admin User:")
    print(f"  Username: {admin_info['username']}")
    print()
    print("Access Methods:")
    print(f"  - Subdomain: {provider_info['slug']}.yourdomain.com")
    print(f"  - Header: X-Provider-Slug: {provider_info['slug']}")
    print(f"  - Query: ?provider={provider_info['slug']}")
    print()
    print("Next Steps:")
    print("  1. Start the application: python -m uvicorn app.main_multitenant:app --reload")
    print("  2. Login at: http://localhost:8000/api/admin/login")
    print("  3. Configure DNS for your subdomain")
    print()
    print("=" * 60)


def list_providers_cmd():
    """List all providers."""
    print("\nRegistered Providers:")
    print("-" * 60)
    
    providers = crud_providers.list_providers(active_only=False)
    
    if not providers:
        print("No providers found.")
        return
    
    for p in providers:
        status = "Active" if p.get("is_active", True) else "Inactive"
        print(f"  {p['name']} ({p['slug']}) - {status}")
        print(f"    Database: {p['database_name']}")
        print(f"    Created: {p.get('created_at', 'N/A')}")
        print()
    
    print(f"Total: {len(providers)} provider(s)")


def delete_provider_cmd(slug: str):
    """Delete a provider."""
    confirm = input(f"Delete provider '{slug}' and all its data? [y/N]: ").strip().lower()
    
    if confirm != 'y':
        print("Cancelled.")
        return
    
    try:
        # First get provider to show info
        provider = crud_providers.get_provider(slug)
        if not provider:
            print(f"Provider '{slug}' not found.")
            return
        
        print(f"Deleting provider: {provider['name']}")
        
        # Delete provider (with database)
        result = crud_providers.delete_provider(slug, delete_database=True)
        
        if result:
            print(f"✓ Provider '{slug}' deleted successfully.")
        else:
            print(f"✗ Failed to delete provider '{slug}'.")
            
    except Exception as e:
        print(f"Error: {e}")


def migrate_existing_data_cmd(slug: str):
    """Migrate existing data from single-tenant to provider database."""
    print(f"\nMigrating data for provider '{slug}'...")
    print("This feature requires custom migration logic.")
    print("Please contact support for assistance.")


def main():
    """Main entry point."""
    welcome_message()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\nPrerequisites check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "list":
            list_providers_cmd()
            return
        
        if command == "delete":
            if len(sys.argv) > 2:
                delete_provider_cmd(sys.argv[2])
            else:
                print("Usage: python setup_first_provider.py delete <slug>")
            return
        
        if command == "migrate":
            if len(sys.argv) > 2:
                migrate_existing_data_cmd(sys.argv[2])
            else:
                print("Usage: python setup_first_provider.py migrate <slug>")
            return
    
    # Interactive mode
    print("This wizard will help you create your first water provider.\n")
    
    # Get provider info
    provider_info = get_provider_info()
    
    # Check if provider already exists
    if crud_providers.provider_exists(provider_info["slug"]):
        print(f"\n⚠ Provider '{provider_info['slug']}' already exists!")
        override = input("Overwrite? [y/N]: ").strip().lower()
        if override != 'y':
            print("Setup cancelled.")
            sys.exit(0)
        
        # Delete existing provider
        crud_providers.delete_provider(provider_info["slug"], delete_database=True)
    
    # Get admin info
    admin_info = get_admin_info()
    
    # Get rate config
    rate_config = get_rate_config()
    
    # Get branding info
    branding_info = get_branding_info()
    
    # Create provider and admin
    success = create_provider(provider_info, admin_info, rate_config, branding_info)
    
    if success:
        print_summary(provider_info, admin_info)
    else:
        print("\nSetup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

