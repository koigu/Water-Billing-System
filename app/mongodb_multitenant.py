"""
Multi-Tenant MongoDB Connection Manager for Water Billing System.
Implements database-per-provider architecture with connection pooling.
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from dotenv import load_dotenv

logger = logging.getLogger("mongodb_multitenant")
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

# ==================== CONFIGURATION ====================

# Master database (provider registry)
MASTER_DB_NAME = os.getenv("MASTER_DB_NAME", "water_billing_master")

# MongoDB connection URL
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

# Provider database name prefix
PROVIDER_DB_PREFIX = "wb_"

# ==================== GLOBAL STATE ====================

# Master database client and reference
_master_client: Optional[MongoClient] = None
_master_db: Optional[Database] = None

# Provider connection cache {db_name: (client, db)}
_provider_connections: Dict[str, tuple[MongoClient, Database]] = {}

# Provider cache {slug: provider_doc}
_provider_cache: Dict[str, Dict[str, Any]] = {}

# ==================== MASTER DATABASE FUNCTIONS ====================

def get_master_client() -> MongoClient:
    """Get or create master database client."""
    global _master_client
    if _master_client is None:
        try:
            _master_client = MongoClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=1
            )
            # Test connection
            _master_client.admin.command('ping')
            logger.info(f"Connected to master MongoDB at {MONGODB_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to master MongoDB: {e}")
            raise
    return _master_client


def get_master_db() -> Database:
    """Get master database instance."""
    global _master_db
    if _master_db is None:
        client = get_master_client()
        _master_db = client[MASTER_DB_NAME]
        logger.info(f"Using master database: {MASTER_DB_NAME}")
    return _master_db


def close_master_connection():
    """Close master database connection."""
    global _master_client, _master_db
    if _master_client is not None:
        _master_client.close()
        _master_client = None
        _master_db = None
        logger.info("Master database connection closed")


# ==================== PROVIDER DATABASE FUNCTIONS ====================

def get_provider_client(provider_slug: str) -> MongoClient:
    """Get MongoDB client for a specific provider."""
    provider = get_provider(provider_slug)
    if provider is None:
        raise ValueError(f"Provider '{provider_slug}' not found")
    
    db_name = provider.get("database_name")
    
    # Check if we already have a connection
    if db_name in _provider_connections:
        client, _ = _provider_connections[db_name]
        return client
    
    # Create new client for this provider
    try:
        client = MongoClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10,
            minPoolSize=1
        )
        # Test connection
        client.admin.command('ping')
        
        # Cache the connection
        _provider_connections[db_name] = (client, client[db_name])
        logger.info(f"Connected to provider database: {db_name}")
        
        return client
    except Exception as e:
        logger.error(f"Failed to connect to provider database {db_name}: {e}")
        raise


def get_provider_db(provider_slug: str) -> Database:
    """Get database instance for a specific provider."""
    provider = get_provider(provider_slug)
    if provider is None:
        raise ValueError(f"Provider '{provider_slug}' not found")
    
    db_name = provider.get("database_name")
    
    # Check cache first
    if db_name in _provider_connections:
        _, db = _provider_connections[db_name]
        return db
    
    # Create new connection
    client = get_provider_client(provider_slug)
    _, db = _provider_connections[db_name]
    return db


def get_provider_collection(provider_slug: str, collection_name: str) -> Collection:
    """Get a collection from a specific provider's database."""
    db = get_provider_db(provider_slug)
    return db[collection_name]


def close_provider_connection(provider_slug: str):
    """Close connection to a provider's database."""
    provider = get_provider(provider_slug)
    if provider is None:
        return
    
    db_name = provider.get("database_name")
    if db_name in _provider_connections:
        client, _ = _provider_connections[db_name]
        client.close()
        del _provider_connections[db_name]
        logger.info(f"Closed connection to provider database: {db_name}")


def close_all_provider_connections():
    """Close all provider database connections."""
    global _provider_connections
    for db_name, (client, _) in list(_provider_connections.items()):
        client.close()
        logger.info(f"Closed connection to provider database: {db_name}")
    _provider_connections.clear()


# ==================== PROVIDER MANAGEMENT ====================

def get_providers_collection() -> Collection:
    """Get the providers collection from master database."""
    return get_master_db()["providers"]


def get_admin_users_collection() -> Collection:
    """Get the admin users collection from master database."""
    return get_master_db()["admin_users"]


def get_provider(provider_slug: str) -> Optional[Dict[str, Any]]:
    """Get provider by slug from cache or database."""
    global _provider_cache
    
    # Check cache first
    if provider_slug in _provider_cache:
        return _provider_cache[provider_slug]
    
    # Query master database
    provider = get_providers_collection().find_one({"slug": provider_slug})
    
    if provider:
        # Cache for future requests
        _provider_cache[provider_slug] = provider
    
    return provider


def get_provider_by_id(provider_id: int) -> Optional[Dict[str, Any]]:
    """Get provider by ID."""
    return get_providers_collection().find_one({"id": provider_id})


def list_providers(active_only: bool = True) -> List[Dict[str, Any]]:
    """List all providers."""
    query = {} if not active_only else {"is_active": True}
    return list(get_providers_collection().find(query))


def create_provider(provider_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new provider in the master database."""
    providers_coll = get_providers_collection()
    
    # Check if provider with this slug already exists
    existing = providers_coll.find_one({"slug": provider_data["slug"]})
    if existing:
        raise ValueError(f"Provider with slug '{provider_data['slug']}' already exists")
    
    # Generate database name
    import secrets
    suffix = secrets.token_hex(4)
    database_name = f"wb_{provider_data['slug']}_{suffix}"
    
    # Add provider data
    provider_doc = {
        "id": get_next_provider_id(),
        "name": provider_data["name"],
        "slug": provider_data["slug"],
        "database_name": database_name,
        "database_suffix": suffix,
        "contact_email": provider_data.get("contact_email"),
        "contact_phone": provider_data.get("contact_phone"),
        "address": provider_data.get("address"),
        "is_active": True,
        "settings": provider_data.get("settings", {}),
        "branding": provider_data.get("branding", {}),
        "created_at": datetime.utcnow(),
        "updated_at": None,
        "created_by": provider_data.get("created_by")
    }
    
    result = providers_coll.insert_one(provider_doc)
    provider_doc["_id"] = result.inserted_id
    
    # Cache the provider
    _provider_cache[provider_doc["slug"]] = provider_doc
    
    # Initialize the provider's database with indexes
    initialize_provider_database(provider_doc)
    
    logger.info(f"Created provider: {provider_doc['name']} (slug: {provider_doc['slug']}, DB: {database_name})")
    
    return provider_doc


def update_provider(provider_slug: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update provider information."""
    providers_coll = get_providers_collection()
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = providers_coll.find_one_and_update(
        {"slug": provider_slug},
        {"$set": update_data},
        return_document=True
    )
    
    if result:
        # Update cache
        _provider_cache[provider_slug] = result
        logger.info(f"Updated provider: {provider_slug}")
    
    return result


def deactivate_provider(provider_slug: str) -> bool:
    """Deactivate a provider (soft delete)."""
    result = update_provider(provider_slug, {"is_active": False})
    return result is not None


def delete_provider(provider_slug: str, delete_database: bool = False) -> bool:
    """Delete a provider from the master database."""
    providers_coll = get_providers_collection()
    
    provider = get_provider(provider_slug)
    if provider is None:
        return False
    
    # Delete admin users
    get_admin_users_collection().delete_many({"provider_id": provider["id"]})
    
    # Delete from master database
    result = providers_coll.delete_one({"slug": provider_slug})
    
    # Remove from cache
    if provider_slug in _provider_cache:
        del _provider_cache[provider_slug]
    
    # Optionally delete the provider's database
    if delete_database:
        try:
            db = get_provider_db(provider_slug)
            db.client.drop_database(db.name)
            logger.info(f"Deleted provider database: {provider['database_name']}")
        except Exception as e:
            logger.error(f"Failed to delete provider database: {e}")
    
    logger.info(f"Deleted provider: {provider_slug}")
    
    return result.deleted_count > 0


# ==================== PROVIDER DATABASE INITIALIZATION ====================

def initialize_provider_database(provider_doc: Dict[str, Any]):
    """Initialize a provider's database with collections and indexes."""
    db_name = provider_doc.get("database_name")
    
    try:
        # Get or create client for this provider
        if db_name not in _provider_connections:
            client = MongoClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=1
            )
            _provider_connections[db_name] = (client, client[db_name])
        
        _, db = _provider_connections[db_name]
        
        # Initialize collections with indexes
        _init_provider_collections(db)
        
        # Initialize counters
        _init_counters(db)
        
        # Initialize default rate configuration
        _init_rate_config(db, provider_doc)
        
        logger.info(f"Initialized database for provider: {provider_doc['name']}")
        
    except Exception as e:
        logger.error(f"Failed to initialize provider database {db_name}: {e}")
        raise


def _init_provider_collections(db: Database):
    """Initialize all collections with indexes for a provider."""
    
    # customers collection
    customers = db["customers"]
    customers.create_index("name")
    customers.create_index("phone", sparse=True)
    customers.create_index("email", sparse=True)
    customers.create_index("created_at")
    customers.create_index("is_active")
    
    # meter_readings collection
    meter_readings = db["meter_readings"]
    meter_readings.create_index("customer_id")
    meter_readings.create_index("recorded_at")
    meter_readings.create_index([("customer_id", 1), ("recorded_at", -1)])
    
    # invoices collection
    invoices = db["invoices"]
    invoices.create_index("customer_id")
    invoices.create_index("status")
    invoices.create_index("due_date")
    invoices.create_index("invoice_number", unique=True, sparse=True)
    invoices.create_index([("customer_id", 1), ("status", 1)])
    invoices.create_index("created_at")
    
    # payments collection
    payments = db["payments"]
    payments.create_index("invoice_id")
    payments.create_index("customer_id")
    payments.create_index("payment_method")
    payments.create_index("payment_date")
    payments.create_index("status")
    
    # rate_config collection
    rate_config = db["rate_config"]
    rate_config.create_index("mode")
    
    # customer_auth collection
    customer_auth = db["customer_auth"]
    customer_auth.create_index("customer_id", unique=True)
    customer_auth.create_index("username", unique=True)
    customer_auth.create_index("is_active")
    
    # usage_alerts collection
    usage_alerts = db["usage_alerts"]
    usage_alerts.create_index("customer_id")
    usage_alerts.create_index("alert_type")
    usage_alerts.create_index("is_read")
    usage_alerts.create_index("created_at")
    
    # usage_trends collection
    usage_trends = db["usage_trends"]
    usage_trends.create_index([("customer_id", 1), ("month", 1)], unique=True)
    usage_trends.create_index("month")
    usage_trends.create_index("year")
    
    # payment_analytics collection
    payment_analytics = db["payment_analytics"]
    payment_analytics.create_index([("customer_id", 1), ("payment_date", -1)])
    payment_analytics.create_index("payment_method")
    payment_analytics.create_index("invoice_id", unique=True, sparse=True)
    
    # customer_behavior collection
    customer_behavior = db["customer_behavior"]
    customer_behavior.create_index("customer_id", unique=True)
    customer_behavior.create_index("status")
    customer_behavior.create_index("last_activity")
    
    # staff_metrics collection
    staff_metrics = db["staff_metrics"]
    staff_metrics.create_index([("staff_id", 1), ("month", 1)], unique=True)
    
    # reminder_config collection
    reminder_config = db["reminder_config"]
    reminder_config.create_index("setting_name", unique=True)
    
    # invoice_sequences collection
    invoice_sequences = db["invoice_sequences"]
    invoice_sequences.create_index("provider_id", unique=True)
    
    logger.info(f"Initialized collections and indexes for database: {db.name}")


def _init_counters(db: Database):
    """Initialize counter collection for auto-increment IDs."""
    counters = ["customers", "meter_readings", "invoices", "payments"]
    for name in counters:
        db["counters"].update_one(
            {"_id": name},
            {"$setOnInsert": {"seq": 1}},
            upsert=True
        )
    logger.info(f"Initialized counters in database: {db.name}")


def _init_rate_config(db: Database, provider_doc: Dict[str, Any]):
    """Initialize default rate configuration for a provider."""
    settings = provider_doc.get("settings", {})
    rate_per_unit = settings.get("rate_per_unit", 1.5)
    
    rate_doc = {
        "mode": "fixed",
        "value": rate_per_unit,
        "currency": settings.get("currency", "KES"),
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    
    db["rate_config"].update_one(
        {},
        {"$set": rate_doc},
        upsert=True
    )
    
    # Initialize reminder config
    reminder_doc = {
        "setting_name": "default",
        "reminder_days": settings.get("reminder_days_before_due", 5),
        "auto_resend_invoice": settings.get("auto_resend_invoices", True),
        "max_reminders": settings.get("max_reminders_per_invoice", 3),
        "updated_by": None,
        "updated_at": None
    }
    
    db["reminder_config"].update_one(
        {"setting_name": "default"},
        {"$set": reminder_doc},
        upsert=True
    )
    
    logger.info(f"Initialized rate and reminder config in database: {db.name}")


# ==================== HELPER FUNCTIONS ====================

def get_next_provider_id() -> int:
    """Get next auto-increment provider ID."""
    master_db = get_master_db()
    result = master_db["provider_counter"].find_one_and_update(
        {"_id": "providers"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result.get("seq", 1)


def get_next_admin_id() -> int:
    """Get next auto-increment admin user ID."""
    master_db = get_master_db()
    result = master_db["provider_counter"].find_one_and_update(
        {"_id": "admin_users"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result.get("seq", 1)


def is_master_connected() -> bool:
    """Check if master database is connected."""
    try:
        client = get_master_client()
        client.admin.command('ping')
        return True
    except Exception:
        return False


def init_master_collections():
    """Initialize master database collections."""
    master_db = get_master_db()
    
    # providers collection
    providers = master_db["providers"]
    providers.create_index("slug", unique=True)
    providers.create_index("id", unique=True)
    providers.create_index("is_active")
    providers.create_index("created_at")
    
    # admin_users collection
    admin_users = master_db["admin_users"]
    admin_users.create_index("provider_id")
    admin_users.create_index("username")
    admin_users.create_index([("provider_id", 1), ("username", 1)], unique=True)
    admin_users.create_index("is_active")
    
    # provider_counter collection
    master_db["provider_counter"].create_index("_id", unique=True)
    
    # super_admins collection
    super_admins = master_db["super_admins"]
    super_admins.create_index("id", unique=True)
    super_admins.create_index("username", unique=True)
    super_admins.create_index("is_active")
    
    # login_logs collection
    login_logs = master_db["login_logs"]
    login_logs.create_index("login_time")
    login_logs.create_index("user_type")
    login_logs.create_index("username")
    
    # provider_subscriptions collection
    provider_subscriptions = master_db["provider_subscriptions"]
    provider_subscriptions.create_index("provider_id", unique=True)
    
    # payment_records collection
    payment_records = master_db["payment_records"]
    payment_records.create_index("provider_id")
    
    logger.info("Initialized master database collections")


def shutdown_all_connections():
    """Shutdown all database connections."""
    global _master_client, _master_db, _provider_connections, _provider_cache
    
    # Close all provider connections
    close_all_provider_connections()
    
    # Close master connection
    close_master_connection()
    
    # Clear caches
    _provider_cache.clear()
    
    logger.info("All database connections closed")


# ==================== CONNECTION POOLING UTILITIES ====================

def get_all_provider_connections() -> Dict[str, Database]:
    """Get all active provider database connections."""
    return {name: db for name, (_, db) in _provider_connections.items()}


def get_connection_stats() -> Dict[str, Any]:
    """Get connection statistics."""
    return {
        "master_connected": is_master_connected(),
        "master_db": MASTER_DB_NAME,
        "provider_connections": len(_provider_connections),
        "provider_cache_size": len(_provider_cache),
        "connected_providers": list(_provider_connections.keys())
    }


# ==================== EXPORTED FUNCTIONS ====================

__all__ = [
    # Master database
    "get_master_client",
    "get_master_db",
    "close_master_connection",
    
    # Provider database
    "get_provider_client",
    "get_provider_db",
    "get_provider_collection",
    "close_provider_connection",
    "close_all_provider_connections",
    
    # Provider management
    "get_provider",
    "get_provider_by_id",
    "list_providers",
    "create_provider",
    "update_provider",
    "deactivate_provider",
    "delete_provider",
    
    # Provider database initialization
    "initialize_provider_database",
    
    # Admin users
    "get_admin_users_collection",
    "get_next_admin_id",
    
    # Utilities
    "is_master_connected",
    "init_master_collections",
    "shutdown_all_connections",
    "get_connection_stats",
    
    # Configuration
    "MASTER_DB_NAME",
    "MONGODB_URL",
    "PROVIDER_DB_PREFIX",
]

