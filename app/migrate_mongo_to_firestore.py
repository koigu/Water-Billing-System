"""
One-time migration from Mongo tenant databases to Firestore.

Usage:
  python -m app.migrate_mongo_to_firestore

Optional:
  MIGRATE_PROVIDER_SLUG=celebration-waters python -m app.migrate_mongo_to_firestore
"""

import os
from datetime import datetime

from bson import ObjectId
from dotenv import load_dotenv

from app import mongodb_multitenant as mt_db
from app.firebase_auth import get_firestore_client


COLLECTION_MAP = {
    "customers": "customers",
    "meter_readings": "meterReadings",
    "invoices": "invoices",
    "payments": "payments",
    "customer_auth": "customerAuth",
    "usage_alerts": "usageAlerts",
}


def clean(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items() if key != "_id"}
    return value


def migrate_provider(provider: dict):
    firestore_client = get_firestore_client()
    provider_slug = provider["slug"]
    provider_ref = firestore_client.collection("providers").document(provider_slug)

    provider_ref.set(
        clean({
            "slug": provider_slug,
            "name": provider.get("name"),
            "isActive": provider.get("is_active", True),
            "contactEmail": provider.get("contact_email"),
            "contactPhone": provider.get("contact_phone"),
            "address": provider.get("address"),
            "ratePerUnit": (provider.get("settings") or {}).get("rate_per_unit", 1.5),
            "currency": (provider.get("settings") or {}).get("currency", "KES"),
            "settings": provider.get("settings", {}),
            "branding": provider.get("branding", {}),
            "createdAt": provider.get("created_at"),
            "updatedAt": provider.get("updated_at"),
            "migratedFromMongoAt": datetime.utcnow(),
        }),
        merge=True,
    )

    db = mt_db.get_provider_db(provider_slug)
    counts = {}

    for mongo_name, firestore_name in COLLECTION_MAP.items():
        count = 0
        for doc in db[mongo_name].find():
            doc_id = str(doc.get("id") or doc.get("customer_id") or doc["_id"])
            provider_ref.collection(firestore_name).document(doc_id).set(clean(doc), merge=True)
            count += 1
        counts[firestore_name] = count

    rate_config = db["rate_config"].find_one({})
    if rate_config:
        provider_ref.collection("settings").document("rateConfig").set(clean(rate_config), merge=True)

    reminder_config = db["reminder_config"].find_one({"setting_name": "default"})
    if reminder_config:
        provider_ref.collection("settings").document("reminderConfig").set(clean(reminder_config), merge=True)

    for counter in db["counters"].find():
        counter_id = str(counter.get("_id"))
        provider_ref.collection("counters").document(counter_id).set(clean(counter), merge=True)

    print(f"Migrated {provider_slug}: {counts}")


def main():
    load_dotenv()
    mt_db.init_master_collections()

    only_slug = os.getenv("MIGRATE_PROVIDER_SLUG", "").strip()
    if only_slug:
        provider = mt_db.get_provider(only_slug)
        if not provider:
            raise RuntimeError(f"Provider '{only_slug}' not found in Mongo")
        providers = [provider]
    else:
        providers = mt_db.list_providers(active_only=False)

    for provider in providers:
        migrate_provider(provider)


if __name__ == "__main__":
    main()
