from datetime import datetime
from typing import Any, Optional

from google.cloud.firestore_v1.base_query import FieldFilter

from app.firebase_auth import get_firestore_client


def _doc_to_dict(doc) -> Optional[dict[str, Any]]:
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data.setdefault("id", doc.id)
    return data


def get_user_profile(firebase_uid: str) -> Optional[dict[str, Any]]:
    """Fetch an application user profile from Firestore."""
    if not firebase_uid:
        return None
    client = get_firestore_client()
    doc = client.collection("users").document(firebase_uid).get()
    return _doc_to_dict(doc)


def set_user_profile(firebase_uid: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create or update an application user profile in Firestore."""
    if not firebase_uid:
        raise ValueError("firebase_uid is required")
    client = get_firestore_client()
    ref = client.collection("users").document(firebase_uid)
    existing = ref.get()
    now = datetime.utcnow()
    profile = {
        **payload,
        "updatedAt": now,
    }
    if not existing.exists:
        profile["createdAt"] = now
    ref.set(profile, merge=True)
    data = ref.get().to_dict() or {}
    data.setdefault("id", firebase_uid)
    return data


def set_customer_portal_profile(provider_slug: str, customer_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Create or update a customer portal profile in Firestore."""
    if not provider_slug:
        raise ValueError("provider_slug is required")
    if not customer_id:
        raise ValueError("customer_id is required")

    client = get_firestore_client()
    doc_id = f"{provider_slug}_{customer_id}"
    ref = client.collection("customerPortalUsers").document(doc_id)
    existing = ref.get()
    now = datetime.utcnow()
    profile = {
        **payload,
        "providerSlug": provider_slug,
        "customerId": customer_id,
        "updatedAt": now,
    }
    if not existing.exists:
        profile["createdAt"] = now
    ref.set(profile, merge=True)
    data = ref.get().to_dict() or {}
    data.setdefault("id", doc_id)
    return data


def get_provider(provider_slug: str) -> Optional[dict[str, Any]]:
    """Fetch a provider by slug from Firestore."""
    if not provider_slug:
        return None
    client = get_firestore_client()
    doc = client.collection("providers").document(provider_slug).get()
    data = _doc_to_dict(doc)
    if data:
        data.setdefault("slug", provider_slug)
    return data


def list_providers(active_only: bool = False) -> list[dict[str, Any]]:
    """List providers from Firestore."""
    client = get_firestore_client()
    query = client.collection("providers")
    if active_only:
        query = query.where(filter=FieldFilter("isActive", "==", True))
    providers = []
    for doc in query.stream():
        data = _doc_to_dict(doc)
        if data:
            data.setdefault("slug", doc.id)
            providers.append(data)
    return providers


def create_provider(provider_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a provider document in Firestore."""
    client = get_firestore_client()
    ref = client.collection("providers").document(provider_slug)
    if ref.get().exists:
        raise ValueError(f"Provider '{provider_slug}' already exists")

    now = datetime.utcnow()
    provider = {
        "slug": provider_slug,
        "name": payload["name"],
        "isActive": True,
        "contactEmail": payload.get("contact_email"),
        "contactPhone": payload.get("contact_phone"),
        "address": payload.get("address"),
        "ratePerUnit": payload.get("rate_per_unit", 1.5),
        "currency": payload.get("currency", "KES"),
        "createdAt": now,
        "updatedAt": None,
    }
    ref.set(provider)
    provider["id"] = provider_slug
    return provider


def update_provider(provider_slug: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Update a provider document in Firestore."""
    client = get_firestore_client()
    ref = client.collection("providers").document(provider_slug)
    if not ref.get().exists:
        return None

    update_map = {}
    field_map = {
        "name": "name",
        "contact_email": "contactEmail",
        "contact_phone": "contactPhone",
        "address": "address",
        "is_active": "isActive",
        "rate_per_unit": "ratePerUnit",
    }
    for key, value in payload.items():
        target = field_map.get(key)
        if target and value is not None:
            update_map[target] = value
    update_map["updatedAt"] = datetime.utcnow()
    ref.update(update_map)
    return get_provider(provider_slug)


def set_provider_active(provider_slug: str, is_active: bool) -> bool:
    """Activate or deactivate a provider in Firestore."""
    provider = update_provider(provider_slug, {"is_active": is_active})
    return provider is not None


def get_platform_stats() -> dict[str, Any]:
    """Return Firestore-backed provider summary stats."""
    providers = list_providers(active_only=False)
    total_providers = len(providers)
    active_providers = sum(1 for provider in providers if provider.get("isActive", True))
    return {
        "total_providers": total_providers,
        "active_providers": active_providers,
        "total_customers": 0,
        "total_invoices": 0,
        "total_payments": 0,
        "total_revenue": 0,
        "pending_invoices": 0,
        "overdue_invoices": 0,
        "period_start": None,
        "period_end": None,
    }
