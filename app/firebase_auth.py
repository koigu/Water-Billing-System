import os
from functools import lru_cache

import firebase_admin
from firebase_admin import auth, credentials, db, firestore


@lru_cache(maxsize=1)
def get_firebase_app():
    """Initialize and return the Firebase Admin app."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    if not service_account_path:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_PATH is not configured")
    database_url = os.getenv("FIREBASE_DATABASE_URL", "").strip()

    cred = credentials.Certificate(service_account_path)
    options = {}
    if database_url:
        options["databaseURL"] = database_url
    try:
        return firebase_admin.initialize_app(cred, options or None)
    except ValueError:
        # Another request/thread initialized the default app first.
        return firebase_admin.get_app()


def verify_firebase_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded payload."""
    get_firebase_app()
    return auth.verify_id_token(id_token)


def upsert_firebase_user(email: str, password: str, display_name: str = None) -> dict:
    """Create or update a Firebase Auth user and return its core fields."""
    get_firebase_app()
    try:
        user = auth.get_user_by_email(email)
        update_kwargs = {}
        if password:
            update_kwargs["password"] = password
        if display_name:
            update_kwargs["display_name"] = display_name
        if update_kwargs:
            user = auth.update_user(user.uid, **update_kwargs)
    except auth.UserNotFoundError:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
        )

    return {
        "uid": user.uid,
        "email": user.email,
        "displayName": user.display_name,
    }


def get_db_reference(path: str = "/"):
    """Return a Firebase Realtime Database reference."""
    get_firebase_app()
    return db.reference(path)


def get_firestore_client():
    """Return a Firestore client bound to the initialized Firebase app."""
    app = get_firebase_app()
    return firestore.client(app=app)
