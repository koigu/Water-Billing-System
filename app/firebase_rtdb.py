from typing import Any, Optional

from app.firebase_auth import get_db_reference


def get_user_profile(firebase_uid: str) -> Optional[dict[str, Any]]:
    """Fetch a Firebase-backed application user profile by UID."""
    if not firebase_uid:
        return None
    return get_db_reference(f"users/{firebase_uid}").get()


def get_provider(provider_slug: str) -> Optional[dict[str, Any]]:
    """Fetch a provider record from Firebase Realtime Database."""
    if not provider_slug:
        return None
    return get_db_reference(f"providers/{provider_slug}").get()


def list_providers() -> list[dict[str, Any]]:
    """List providers from Firebase Realtime Database."""
    data = get_db_reference("providers").get() or {}
    providers = []
    for slug, provider in data.items():
        if isinstance(provider, dict):
            provider = {**provider}
            provider.setdefault("slug", slug)
            providers.append(provider)
    return providers
