"""
Grant Super Admin Access Script for Celebration Waters
Run this to give yourself creator/super admin access.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import mongodb_multitenant as mt_db
from app import crud_providers

def create_super_admin():
    """Create a super admin user with full system access."""
    
    print("=" * 50)
    print("  SUPER ADMIN SETUP FOR CELEBRATION WATERS")
    print("=" * 50)
    print()
    
    # Provider details
    provider_slug = "celebration-water"
    provider_name = "Celebration Waters"
    
    print(f"Provider: {provider_name} (slug: {provider_slug})")
    print()
    
    # Step 1: Ensure provider exists
    print("Step 1: Checking provider...")
    provider = crud_providers.get_provider(provider_slug)
    
    if not provider:
        print(f"  Creating provider: {provider_name}...")
        provider = crud_providers.create_provider({
            "name": provider_name,
            "slug": provider_slug,
            "contact_email": "franciskoigu@gmail.com",
            "contact_phone": "0722532930",
            "address": "Naivasha, Kenya",
            "settings": {
                "rate_per_unit": 50.0,
                "currency": "KES",
                "billing_cycle_days": 30,
                "payment_due_days": 15
            }
        })
        print(f"  ✓ Provider created: {provider['database_name']}")
    else:
        print(f"  ✓ Provider already exists")
    
    # Step 2: Create super admin user (Admin)
    print()
    print("Step 2: Creating super admin user (Admin)...")
    
    # First, create a super admin in the super_admins collection
    from app.crud_providers import get_super_admin_by_username
    
    existing_super_admin = get_super_admin_by_username("Admin")
    
    if existing_super_admin:
        print("  ✓ Super admin 'Admin' already exists")
        print(f"  User ID: {existing_super_admin['id']}")
    else:
        # Create the super admin in the super_admins collection
        super_admin = crud_providers.create_super_admin({
            "username": "Admin",
            "password": "Changeme",
            "email": "admin@waterbilling.com",
            "full_name": "System Administrator"
        })
        print(f"  ✓ Super admin created!")
        print(f"  Username: Admin")
        print(f"  Password: Changeme")
    
    # Step 3: Create provider admin user (Francis for celebration-water)
    print()
    print("Step 3: Creating provider admin user (Francis)...")
    
    admin = crud_providers.get_admin_user_by_username(provider["id"], "Francis")
    
    if admin:
        print("  ✓ Provider admin 'Francis' already exists")
        print(f"  User ID: {admin['id']}")
    else:
        # Create the provider admin
        admin = crud_providers.create_admin_user({
            "provider_slug": provider_slug,
            "provider_id": provider["id"],
            "username": "Francis",
            "password": "12345678",
            "email": "franciskoigu@gmail.com",
            "full_name": "Francis Koigu",
            "is_super_admin": False  # Provider admin (not super admin)
        })
        print(f"  ✓ Provider admin created!")
        print(f"  Username: Francis")
        print(f"  Password: 12345678")
    
    # Step 4: Verify access
    print()
    print("Step 4: Verifying access...")
    
    # Test super admin authentication
    from app.crud_providers import authenticate_super_admin
    auth = authenticate_super_admin("Admin", "Changeme")
    
    if auth:
        print("  ✓ Super admin authentication successful!")
        print(f"  Admin ID: {auth['id']}")
        print(f"  Username: {auth['username']}")
    else:
        print("  ✗ Super admin authentication failed!")
    
    # Test provider admin authentication
    auth_provider = crud_providers.authenticate_admin("Francis", "12345678", provider_slug)
    
    if auth_provider:
        print("  ✓ Provider admin authentication successful!")
        print(f"  Admin ID: {auth_provider['id']}")
        print(f"  Username: {auth_provider['username']}")
        print(f"  Provider: {provider_slug}")
    else:
        print("  ✗ Provider admin authentication failed!")
    
    print()
    print("=" * 50)
    print("  SETUP COMPLETE!")
    print("=" * 50)
    print()
    print("LOGIN OPTIONS:")
    print()
    print("  Option 1 - Super Admin (Full System Access):")
    print("    URL: http://127.0.0.1:8000/api/admin/login")
    print("    Username: Admin")
    print("    Password: Changeme")
    print()
    print("  Option 2 - Provider Admin (Celebration Waters):")
    print("    URL: http://127.0.0.1:8000/api/admin/login")
    print("    Username: Francis")
    print("    Password: 12345678")
    print("    Provider: celebration-water")
    print()
    print("NEXT STEPS:")
    print("  1. Make sure MongoDB is running")
    print("  2. Start the backend server:")
    print("       python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
    print("  3. Start the frontend:")
    print("       cd frontend && npm run dev")
    print("  4. Open http://localhost:5173 in your browser")
    print()


if __name__ == "__main__":
    create_super_admin()

