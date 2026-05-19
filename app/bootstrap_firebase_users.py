"""
Bootstrap one provider admin and one customer portal user.

Usage:
  python -m app.bootstrap_firebase_users

Optional environment variables:
  BOOTSTRAP_PROVIDER_SLUG
  BOOTSTRAP_ADMIN_EMAIL
  BOOTSTRAP_ADMIN_PASSWORD
  BOOTSTRAP_CUSTOMER_EMAIL
  BOOTSTRAP_CUSTOMER_PASSWORD
  BOOTSTRAP_CUSTOMER_USERNAME
  BOOTSTRAP_CUSTOMER_ID
"""

import os
from datetime import datetime

from dotenv import load_dotenv

from app import crud_multitenant as crud
from app.crud_providers import crud_providers, get_admin_user_by_email
from app.firebase_auth import upsert_firebase_user
from app.firebase_firestore import (
    get_provider as get_firestore_provider,
    set_customer_portal_profile,
    set_user_profile,
)
from app.main_multitenant import ensure_mongo_provider_for_workspace


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def main():
    load_dotenv()

    provider_slug = _env("BOOTSTRAP_PROVIDER_SLUG", "celebration-waters")
    admin_email = _env("BOOTSTRAP_ADMIN_EMAIL", "admin.celebration.waters@example.com")
    admin_password = _env("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe123!")
    customer_email = _env("BOOTSTRAP_CUSTOMER_EMAIL", "customer.celebration.waters@example.com")
    customer_password = _env("BOOTSTRAP_CUSTOMER_PASSWORD", "ChangeMe123!")
    customer_username = _env("BOOTSTRAP_CUSTOMER_USERNAME", "customer1")
    customer_id = int(_env("BOOTSTRAP_CUSTOMER_ID", "1"))

    provider = get_firestore_provider(provider_slug)
    if not provider:
        provider = crud_providers.get_provider(provider_slug)
    if not provider:
        raise RuntimeError(f"Provider '{provider_slug}' not found in Firestore or Mongo")

    mongo_provider = ensure_mongo_provider_for_workspace(provider_slug, provider)

    admin_user = upsert_firebase_user(
        admin_email,
        admin_password,
        display_name="Celebration Waters Admin",
    )
    existing_admin = get_admin_user_by_email(mongo_provider["id"], admin_email)
    if not existing_admin:
        crud_providers.create_admin_user({
            "provider_slug": provider_slug,
            "username": admin_email,
            "email": admin_email,
            "full_name": "Celebration Waters Admin",
            "password": admin_password,
            "is_super_admin": False,
        })

    set_user_profile(admin_user["uid"], {
        "displayName": "Celebration Waters Admin",
        "email": admin_email,
        "providerSlug": provider_slug,
        "role": "admin",
        "isActive": True,
    })

    customer = crud.get_customer(provider_slug, customer_id)
    if not customer:
        customer = crud.create_customer(provider_slug, {
            "name": "Portal Test Customer",
            "phone": None,
            "email": customer_email,
            "location": "Unassigned",
            "initial_reading": 0,
        })
        customer_id = customer["id"]

    customer_user = upsert_firebase_user(
        customer_email,
        customer_password,
        display_name=customer.get("name") or "Portal Customer",
    )
    existing_customer_auth = crud.get_customer_auth(provider_slug, customer_id)
    if not existing_customer_auth:
        crud.create_customer_auth(provider_slug, customer_id, customer_username, customer_password)

    set_customer_portal_profile(provider_slug, customer_id, {
        "username": customer_username,
        "email": customer_email,
        "displayName": customer.get("name") or "Portal Customer",
        "role": "customer",
        "isActive": True,
        "bootstrappedAt": datetime.utcnow(),
    })
    set_user_profile(customer_user["uid"], {
        "displayName": customer.get("name") or "Portal Customer",
        "email": customer_email,
        "providerSlug": provider_slug,
        "customerId": customer_id,
        "role": "customer",
        "isActive": True,
    })

    print("Created/updated bootstrap users:")
    print(f"  Provider: {provider_slug}")
    print(f"  Admin email: {admin_email}")
    print(f"  Customer portal username: {customer_username}")
    print(f"  Customer email: {customer_email}")
    print(f"  Customer ID: {customer_id}")


if __name__ == "__main__":
    main()
