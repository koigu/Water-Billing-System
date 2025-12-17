"""
MongoDB connection and client management for Water Billing System.
Complete MongoDB-only implementation.
"""
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection
from dotenv import load_dotenv
import logging

logger = logging.getLogger("mongodb")
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "water_billing")

# Global client instance
_client = None
_db = None

# Collection names
COLLECTIONS = {
    "customers": "customers",
    "meter_readings": "meter_readings",
    "invoices": "invoices",
    "payments": "payments",
    "rate_config": "rate_config",
    "customer_auth": "customer_auth",
    "usage_alerts": "usage_alerts",
    "usage_trends": "usage_trends",
    "payment_analytics": "payment_analytics",
    "customer_behavior": "customer_behavior",
    "staff_metrics": "staff_metrics",
    "reminder_config": "reminder_config",
}


def get_client() -> MongoClient:
    """Get or create MongoDB client."""
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
            # Test connection
            _client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {MONGODB_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            _client = None
    return _client


def get_db():
    """Get MongoDB database instance."""
    global _db
    if _db is None:
        client = get_client()
        if client is not None:
            _db = client[MONGODB_DB_NAME]
            logger.info(f"Using MongoDB database: {MONGODB_DB_NAME}")
    return _db


def get_collection(collection_name: str) -> Collection:
    """Get a MongoDB collection by name."""
    db = get_db()
    if db is not None:
        return db[collection_name]
    return None


def get_all_collections():
    """Get all application collections."""
    db = get_db()
    if db is None:
        return {}
    return {
        name: db[coll_name] for name, coll_name in COLLECTIONS.items()
    }


def close_connection():
    """Close MongoDB connection."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


def init_collections():
    """Initialize MongoDB collections with indexes."""
    db = get_db()
    if db is None:
        logger.warning("Cannot initialize collections: MongoDB not connected")
        return

    # customers collection indexes
    customers = db["customers"]
    customers.create_index("name")
    customers.create_index("phone", sparse=True)
    customers.create_index("email", sparse=True)
    customers.create_index("created_at")

    # meter_readings collection indexes
    meter_readings = db["meter_readings"]
    meter_readings.create_index("customer_id")
    meter_readings.create_index("recorded_at")
    meter_readings.create_index([("customer_id", 1), ("recorded_at", -1)])

    # invoices collection indexes
    invoices = db["invoices"]
    invoices.create_index("customer_id")
    invoices.create_index("status")
    invoices.create_index("due_date")
    invoices.create_index([("customer_id", 1), ("status", 1)])

    # payments collection indexes
    payments = db["payments"]
    payments.create_index("invoice_id")
    payments.create_index("payment_method")
    payments.create_index("payment_date")
    payments.create_index("status")

    # rate_config collection (single document)
    rate_config = db["rate_config"]
    rate_config.create_index("mode")

    # customer_auth collection indexes
    customer_auth = db["customer_auth"]
    customer_auth.create_index("customer_id", unique=True)
    customer_auth.create_index("username", unique=True)
    customer_auth.create_index("is_active")

    # usage_alerts collection indexes
    usage_alerts = db["usage_alerts"]
    usage_alerts.create_index("customer_id")
    usage_alerts.create_index("alert_type")
    usage_alerts.create_index("is_read")
    usage_alerts.create_index("created_at")

    # Analytics collection indexes
    usage_trends = db["usage_trends"]
    usage_trends.create_index([("customer_id", 1), ("month", 1)], unique=True)
    usage_trends.create_index("month")
    usage_trends.create_index("year")

    payment_analytics = db["payment_analytics"]
    payment_analytics.create_index([("customer_id", 1), ("payment_date", -1)])
    payment_analytics.create_index("payment_method")
    payment_analytics.create_index("invoice_id", unique=True)

    customer_behavior = db["customer_behavior"]
    customer_behavior.create_index("customer_id", unique=True)
    customer_behavior.create_index("status")
    customer_behavior.create_index("last_activity")

    staff_metrics = db["staff_metrics"]
    staff_metrics.create_index([("staff_id", 1), ("month", 1)], unique=True)

    reminder_config = db["reminder_config"]
    reminder_config.create_index("setting_name", unique=True)

    logger.info("MongoDB collections initialized with indexes")


def is_connected() -> bool:
    """Check if MongoDB is connected."""
    client = get_client()
    if client is None:
        return False
    try:
        client.admin.command('ping')
        return True
    except Exception:
        return False


def get_next_sequence(db, name: str) -> int:
    """Get next sequence number for a collection."""
    result = db["counters"].find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result.get("seq", 1)


def init_counter(db):
    """Initialize counter collection if not exists."""
    # Use upsert to avoid duplicate key errors
    counters = ["customers", "meter_readings", "invoices", "payments"]
    for name in counters:
        db["counters"].update_one(
            {"_id": name},
            {"$setOnInsert": {"seq": 1}},
            upsert=True
        )
    logger.info("Counter collection initialized")

