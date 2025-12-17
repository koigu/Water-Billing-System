"""
Multi-Tenant CRUD Operations for Water Billing System.
All operations are automatically scoped to the provider's database.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId

from app import mongodb_multitenant as mt_db
from app.models import ProviderSettings

logger = logging.getLogger("crud_multitenant")


def get_provider_db(provider_slug: str):
    """Get MongoDB database for a provider."""
    return mt_db.get_provider_db(provider_slug)


def get_next_id(provider_slug: str, collection_name: str) -> int:
    """Get next auto-increment ID for a collection in provider's database."""
    db = get_provider_db(provider_slug)
    
    counter = db["counters"].find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return counter.get("seq", 1)


def get_next_invoice_number(provider_slug: str) -> str:
    """Generate next invoice number for provider."""
    db = get_provider_db(provider_slug)
    
    # Get or create invoice sequence
    seq_doc = db["invoice_sequences"].find_one_and_update(
        {"provider_id": mt_db.get_provider(provider_slug)["id"]},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    seq = seq_doc.get("seq", 1)
    
    # Get provider settings for prefix
    provider = mt_db.get_provider(provider_slug)
    prefix = provider.get("settings", {}).get("invoice_number_prefix", "INV")
    
    return f"{prefix}{seq:06d}"


# ==================== CUSTOMER CRUD ====================

def create_customer(provider_slug: str, customer_data: dict) -> Optional[dict]:
    """
    Create a new customer in provider's database.
    
    Args:
        provider_slug: Provider identifier
        customer_data: Customer information
    
    Returns:
        Created customer document
    """
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    customer_id = get_next_id(provider_slug, "customers")
    
    customer = {
        "id": customer_id,
        "name": customer_data.get("name"),
        "phone": customer_data.get("phone"),
        "email": customer_data.get("email"),
        "location": customer_data.get("location"),
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    
    result = db["customers"].insert_one(customer)
    customer["_id"] = result.inserted_id
    
    # Add initial reading if provided
    initial_reading = customer_data.get("initial_reading")
    if initial_reading is not None:
        add_reading(provider_slug, customer_id, initial_reading)
    
    logger.info(f"Created customer {customer_id} for provider {provider_slug}")
    
    return customer


def get_customer(provider_slug: str, customer_id: int) -> Optional[dict]:
    """Get a customer by ID from provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    return db["customers"].find_one({"id": customer_id, "is_active": True})


def list_customers(provider_slug: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """List all customers from provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["customers"].find({"is_active": True}).skip(skip).limit(limit))


def search_customers_by_name(provider_slug: str, name_query: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """Search customers by name in provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["customers"].find({
        "name": {"$regex": name_query, "$options": "i"},
        "is_active": True
    }).skip(skip).limit(limit))


def update_customer(provider_slug: str, customer_id: int, update_data: dict) -> Optional[dict]:
    """Update a customer in provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = db["customers"].find_one_and_update(
        {"id": customer_id},
        {"$set": update_data},
        return_document=True
    )
    
    return result


def delete_customer(provider_slug: str, customer_id: int) -> bool:
    """Soft delete a customer from provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return False
    
    # Delete related data
    db["meter_readings"].delete_many({"customer_id": customer_id})
    db["invoices"].delete_many({"customer_id": customer_id})
    db["customer_auth"].delete_many({"customer_id": customer_id})
    db["usage_alerts"].delete_many({"customer_id": customer_id})
    db["customer_behavior"].delete_many({"customer_id": customer_id})
    
    # Soft delete customer
    result = db["customers"].update_one(
        {"id": customer_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    return result.modified_count > 0


def get_customers_count(provider_slug: str) -> int:
    """Get count of active customers."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0
    return db["customers"].count_documents({"is_active": True})


# ==================== METER READING CRUD ====================

def add_reading(provider_slug: str, customer_id: int, reading_value: float) -> Optional[dict]:
    """Add a meter reading for a customer."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    reading_id = get_next_id(provider_slug, "meter_readings")
    
    reading = {
        "id": reading_id,
        "customer_id": customer_id,
        "reading_value": reading_value,
        "recorded_at": datetime.utcnow()
    }
    
    result = db["meter_readings"].insert_one(reading)
    reading["_id"] = result.inserted_id
    
    return reading


def get_customer_readings(provider_slug: str, customer_id: int, limit: int = 100) -> List[dict]:
    """Get all readings for a customer."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["meter_readings"].find(
        {"customer_id": customer_id}
    ).sort("recorded_at", -1).limit(limit))


def get_latest_two_readings(provider_slug: str, customer_id: int) -> List[dict]:
    """Get the two most recent readings for a customer."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["meter_readings"].find(
        {"customer_id": customer_id}
    ).sort("recorded_at", -1).limit(2))


def get_all_readings(provider_slug: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """Get all readings from provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["meter_readings"].find().sort("recorded_at", -1).skip(skip).limit(limit))


def get_readings_count(provider_slug: str) -> int:
    """Get count of all readings."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0
    return db["meter_readings"].count_documents({})


# ==================== INVOICE CRUD ====================

def create_invoice(
    provider_slug: str,
    customer_id: int,
    amount: float,
    due_date: datetime,
    location: str = None,
    billing_from: datetime = None,
    billing_to: datetime = None
) -> Optional[dict]:
    """Create a new invoice in provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    invoice_id = get_next_id(provider_slug, "invoices")
    invoice_number = get_next_invoice_number(provider_slug)
    
    now = datetime.utcnow()
    
    invoice = {
        "id": invoice_id,
        "invoice_number": invoice_number,
        "customer_id": customer_id,
        "amount": amount,
        "billing_from": billing_from or now,
        "billing_to": billing_to or now,
        "due_date": due_date,
        "sent_at": None,
        "status": "pending",
        "location": location,
        "reminder_sent_at": None,
        "created_at": now
    }
    
    result = db["invoices"].insert_one(invoice)
    invoice["_id"] = result.inserted_id
    
    return invoice


def get_invoice(provider_slug: str, invoice_id: int) -> Optional[dict]:
    """Get an invoice by ID."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    return db["invoices"].find_one({"id": invoice_id})


def get_invoice_by_number(provider_slug: str, invoice_number: str) -> Optional[dict]:
    """Get an invoice by invoice number."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    return db["invoices"].find_one({"invoice_number": invoice_number})


def list_invoices(provider_slug: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """List all invoices from provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["invoices"].find().sort("created_at", -1).skip(skip).limit(limit))


def get_customer_invoices(provider_slug: str, customer_id: int) -> List[dict]:
    """Get all invoices for a customer."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["invoices"].find(
        {"customer_id": customer_id}
    ).sort("created_at", -1))


def mark_invoice_paid(provider_slug: str, invoice_id: int) -> Optional[dict]:
    """Mark an invoice as paid."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    result = db["invoices"].find_one_and_update(
        {"id": invoice_id},
        {"$set": {"status": "paid", "paid_at": datetime.utcnow()}},
        return_document=True
    )
    
    return result


def mark_invoice_overdue(provider_slug: str, invoice_id: int) -> Optional[dict]:
    """Mark an invoice as overdue."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    result = db["invoices"].find_one_and_update(
        {"id": invoice_id},
        {"$set": {"status": "overdue"}},
        return_document=True
    )
    
    return result


def update_overdue_invoices(provider_slug: str) -> int:
    """Update all invoices past due date to overdue status."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0
    
    now = datetime.utcnow()
    result = db["invoices"].update_many(
        {"status": {"$nin": ["paid", "cancelled"]}, "due_date": {"$lt": now}},
        {"$set": {"status": "overdue"}}
    )
    
    return result.modified_count


def mark_reminder_sent(provider_slug: str, invoice_id: int, when: datetime = None) -> Optional[dict]:
    """Mark that a reminder was sent for an invoice."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    when = when or datetime.utcnow()
    result = db["invoices"].find_one_and_update(
        {"id": invoice_id},
        {"$set": {"reminder_sent_at": when}},
        return_document=True
    )
    
    return result


def get_invoices_count(provider_slug: str) -> int:
    """Get count of all invoices."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0
    return db["invoices"].count_documents({})


def get_pending_invoices_count(provider_slug: str) -> int:
    """Get count of pending invoices."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0
    return db["invoices"].count_documents({"status": "pending"})


def get_overdue_invoices_count(provider_slug: str) -> int:
    """Get count of overdue invoices."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0
    return db["invoices"].count_documents({"status": "overdue"})


# ==================== PAYMENT CRUD ====================

def create_payment(provider_slug: str, payment_data: dict) -> Optional[dict]:
    """Create a payment record."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    payment_id = get_next_id(provider_slug, "payments")
    
    payment = {
        "id": payment_id,
        "invoice_id": payment_data.get("invoice_id"),
        "customer_id": payment_data.get("customer_id"),
        "amount": payment_data.get("amount"),
        "payment_method": payment_data.get("payment_method"),
        "transaction_id": payment_data.get("transaction_id"),
        "status": payment_data.get("status", "completed"),
        "payment_date": datetime.utcnow(),
        "notes": payment_data.get("notes")
    }
    
    result = db["payments"].insert_one(payment)
    payment["_id"] = result.inserted_id
    
    return payment


def get_payment(provider_slug: str, payment_id: int) -> Optional[dict]:
    """Get a payment by ID."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    return db["payments"].find_one({"id": payment_id})


def get_invoice_payments(provider_slug: str, invoice_id: int) -> List[dict]:
    """Get all payments for an invoice."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["payments"].find(
        {"invoice_id": invoice_id}
    ).sort("payment_date", -1))


def get_customer_payments(provider_slug: str, customer_id: int) -> List[dict]:
    """Get all payments for a customer."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    return list(db["payments"].find(
        {"customer_id": customer_id}
    ).sort("payment_date", -1))


def get_payments_count(provider_slug: str) -> int:
    """Get count of all payments."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0
    return db["payments"].count_documents({})


# ==================== RATE CONFIG CRUD ====================

def get_rate_config(provider_slug: str) -> Dict[str, Any]:
    """Get current rate configuration from provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return {"mode": "fixed", "value": 1.5}
    
    rc = db["rate_config"].find_one({})
    if not rc:
        # Get default from provider settings
        provider = mt_db.get_provider(provider_slug)
        default_rate = provider.get("settings", {}).get("rate_per_unit", 1.5) if provider else 1.5
        
        rc = {
            "mode": "fixed",
            "value": default_rate,
            "currency": "KES",
            "created_at": datetime.utcnow()
        }
        db["rate_config"].insert_one(rc)
    
    return rc


def set_rate_config(provider_slug: str, mode: str, value: float) -> Dict[str, Any]:
    """Set rate configuration in provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    now = datetime.utcnow()
    result = db["rate_config"].find_one_and_update(
        {},
        {"$set": {"mode": mode, "value": value, "updated_at": now}},
        upsert=True,
        return_document=True
    )
    
    return result


def get_effective_rate(provider_slug: str) -> float:
    """Get the effective rate per unit."""
    rc = get_rate_config(provider_slug)
    
    if rc.get("mode") == "fixed":
        return rc.get("value", 1.5)
    
    # percent mode: percentage relative to base rate
    try:
        base = float(os.getenv("RATE_PER_UNIT", "1.5"))
    except Exception:
        base = 1.5
    
    return base * (1.0 + (rc.get("value") or 0.0) / 100.0)


# ==================== REMINDER CONFIG CRUD ====================

def get_reminder_config(provider_slug: str) -> Dict[str, Any]:
    """Get reminder configuration from provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return {
            "reminder_days": 5,
            "auto_resend_invoice": True,
            "max_reminders": 3
        }
    
    config = db["reminder_config"].find_one({"setting_name": "default"})
    if not config:
        # Get from provider settings
        provider = mt_db.get_provider(provider_slug)
        settings = provider.get("settings", {}) if provider else {}
        
        config = {
            "setting_name": "default",
            "reminder_days": settings.get("reminder_days_before_due", 5),
            "auto_resend_invoice": settings.get("auto_resend_invoices", True),
            "max_reminders": settings.get("max_reminders_per_invoice", 3),
            "updated_by": None,
            "updated_at": None
        }
        db["reminder_config"].insert_one(config)
    
    return config


def set_reminder_config(
    provider_slug: str,
    reminder_days: int,
    auto_resend_invoice: bool = True,
    max_reminders: int = 3,
    updated_by: str = None
) -> Dict[str, Any]:
    """Set reminder configuration in provider's database."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    now = datetime.utcnow()
    result = db["reminder_config"].find_one_and_update(
        {"setting_name": "default"},
        {"$set": {
            "reminder_days": reminder_days,
            "auto_resend_invoice": auto_resend_invoice,
            "max_reminders": max_reminders,
            "updated_by": updated_by,
            "updated_at": now
        }},
        upsert=True,
        return_document=True
    )
    
    return result


# ==================== CALCULATIONS ====================

def calculate_amount_from_readings(provider_slug: str, customer_id: int, rate_per_unit: float = None):
    """Calculate invoice amount from latest two readings."""
    if rate_per_unit is None:
        rate_per_unit = get_effective_rate(provider_slug)
    
    readings = get_latest_two_readings(provider_slug, customer_id)
    
    if len(readings) < 2:
        return None
    
    latest = readings[0]
    previous = readings[1]
    
    usage = latest.get("reading_value", 0) - previous.get("reading_value", 0)
    if usage < 0:
        usage = 0
    
    amount = usage * rate_per_unit
    return amount, previous.get("recorded_at"), latest.get("recorded_at")


def calculate_total_usage(provider_slug: str) -> float:
    """Calculate total water usage from invoices."""
    rate = get_effective_rate(provider_slug)
    
    db = get_provider_db(provider_slug)
    if db is None:
        return 0.0
    
    pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    result = list(db["invoices"].aggregate(pipeline))
    
    total_amount = result[0]["total"] if result else 0.0
    total_usage = total_amount / rate if rate > 0 else 0.0
    
    return round(total_usage, 2)


def calculate_total_revenue(provider_slug: str) -> float:
    """Calculate total revenue from paid invoices."""
    db = get_provider_db(provider_slug)
    if db is None:
        return 0.0
    
    pipeline = [
        {"$match": {"status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    result = list(db["invoices"].aggregate(pipeline))
    
    return result[0]["total"] if result else 0.0


# ==================== CUSTOMER AUTH CRUD ====================

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 (for backward compatibility)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def create_customer_auth(provider_slug: str, customer_id: int, username: str, password: str) -> Optional[dict]:
    """Create customer authentication record."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    auth = {
        "customer_id": customer_id,
        "username": username,
        "password_hash": hash_password(password),
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    result = db["customer_auth"].insert_one(auth)
    auth["_id"] = result.inserted_id
    
    return auth


def get_customer_auth(provider_slug: str, customer_id: int) -> Optional[dict]:
    """Get customer authentication record."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    return db["customer_auth"].find_one({"customer_id": customer_id})


def get_auth_by_username(provider_slug: str, username: str) -> Optional[dict]:
    """Get auth record by username."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    return db["customer_auth"].find_one({"username": username})


def authenticate_customer(provider_slug: str, username: str, password: str) -> Optional[dict]:
    """Authenticate customer and update last login."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    hashed_password = hash_password(password)
    auth = db["customer_auth"].find_one({
        "username": username,
        "password_hash": hashed_password,
        "is_active": True
    })
    
    if auth:
        # Update last login
        db["customer_auth"].update_one(
            {"_id": auth["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        auth["last_login"] = datetime.utcnow()
    
    return auth


# ==================== USAGE ALERTS CRUD ====================

def create_usage_alert(provider_slug: str, alert_data: dict) -> Optional[dict]:
    """Create a usage alert."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    alert = {
        "customer_id": alert_data.get("customer_id"),
        "alert_type": alert_data.get("alert_type"),
        "message": alert_data.get("message"),
        "threshold_value": alert_data.get("threshold_value"),
        "actual_value": alert_data.get("actual_value"),
        "created_at": datetime.utcnow(),
        "is_read": False,
        "resolved_at": None
    }
    
    result = db["usage_alerts"].insert_one(alert)
    alert["_id"] = result.inserted_id
    
    return alert


def get_customer_alerts(provider_slug: str, customer_id: int, unread_only: bool = False) -> List[dict]:
    """Get all alerts for a customer."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    
    query = {"customer_id": customer_id}
    if unread_only:
        query["is_read"] = False
    
    return list(db["usage_alerts"].find(query).sort("created_at", -1))


def mark_alert_read(provider_slug: str, alert_id: int) -> Optional[dict]:
    """Mark an alert as read."""
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    result = db["usage_alerts"].find_one_and_update(
        {"id": alert_id},
        {"$set": {"is_read": True}},
        return_document=True
    )
    
    return result


# ==================== DASHBOARD STATS ====================

def get_dashboard_stats(provider_slug: str) -> Dict[str, Any]:
    """Get dashboard statistics for a provider."""
    db = get_provider_db(provider_slug)
    if db is None:
        return {
            "total_customers": 0,
            "active_customers": 0,
            "total_water_usage": 0,
            "total_revenue": 0,
            "pending_invoices": 0,
            "overdue_invoices": 0
        }
    
    # Total customers
    total_customers = db["customers"].count_documents({"is_active": True})
    
    # Active customers (with readings in last 90 days)
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    active_customers = db["customers"].count_documents({
        "id": {"$in": db["meter_readings"].distinct("customer_id", {"recorded_at": {"$gte": ninety_days_ago}})}
    })
    
    # Invoice counts
    pending_invoices = db["invoices"].count_documents({"status": "pending"})
    overdue_invoices = db["invoices"].count_documents({"status": "overdue"})
    
    # Calculate totals
    total_usage = calculate_total_usage(provider_slug)
    total_revenue = calculate_total_revenue(provider_slug)
    
    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "inactive_customers": total_customers - active_customers,
        "total_water_usage": total_usage,
        "total_revenue": round(total_revenue, 2),
        "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices
    }


# ==================== ANALYTICS HELPERS ====================

def get_customer_usage_history(provider_slug: str, customer_id: int, months: int = 12) -> List[dict]:
    """Get customer's usage history."""
    db = get_provider_db(provider_slug)
    if db is None:
        return []
    
    start_date = datetime.utcnow() - timedelta(days=months * 30)
    
    pipeline = [
        {"$match": {"customer_id": customer_id, "recorded_at": {"$gte": start_date}}},
        {"$sort": {"recorded_at": 1}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$recorded_at"}},
            "avg_reading": {"$avg": "$reading_value"},
            "max_reading": {"$max": "$reading_value"},
            "min_reading": {"$min": "$reading_value"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = list(db["meter_readings"].aggregate(pipeline))
    
    usage_data = []
    for r in results:
        usage_data.append({
            "date": r["_id"],
            "usage": r["max_reading"] - r["avg_reading"],
            "reading": r["max_reading"]
        })
    
    return usage_data


def get_customer_benchmark(provider_slug: str, customer_id: int) -> Optional[Dict[str, Any]]:
    """Get customer's usage benchmark."""
    customer = get_customer(provider_slug, customer_id)
    if not customer:
        return None
    
    db = get_provider_db(provider_slug)
    if db is None:
        return None
    
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    
    # Get customer's average usage
    customer_usage = list(db["meter_readings"].aggregate([
        {"$match": {"customer_id": customer_id, "recorded_at": {"$gte": ninety_days_ago}}},
        {"$group": {"_id": None, "avg": {"$avg": "$reading_value"}}}
    ]))
    
    if not customer_usage:
        return None
    
    customer_avg = customer_usage[0]["avg"]
    
    # Get all customer averages
    all_usages = list(db["meter_readings"].aggregate([
        {"$match": {"recorded_at": {"$gte": ninety_days_ago}}},
        {"$group": {"_id": "$customer_id", "avg": {"$avg": "$reading_value"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 3}}}
    ]))
    
    if all_usages:
        sorted_usages = sorted([u["avg"] for u in all_usages])
        percentile = sum(1 for u in sorted_usages if u <= customer_avg) / len(sorted_usages) * 100
    else:
        percentile = 50
    
    # Determine comparison
    if percentile <= 25:
        comparison = "Below average - Great conservation!"
    elif percentile <= 75:
        comparison = "Average usage"
    else:
        comparison = "Above average - Consider conservation measures"
    
    return {
        "customer_average": round(customer_avg, 2),
        "percentile": round(percentile, 1),
        "comparison": comparison
    }


# ==================== EXPORTED FUNCTIONS ====================

__all__ = [
    # Database access
    "get_provider_db",
    "get_next_id",
    "get_next_invoice_number",
    
    # Customer CRUD
    "create_customer",
    "get_customer",
    "list_customers",
    "search_customers_by_name",
    "update_customer",
    "delete_customer",
    "get_customers_count",
    
    # Meter Reading CRUD
    "add_reading",
    "get_customer_readings",
    "get_latest_two_readings",
    "get_all_readings",
    "get_readings_count",
    
    # Invoice CRUD
    "create_invoice",
    "get_invoice",
    "get_invoice_by_number",
    "list_invoices",
    "get_customer_invoices",
    "mark_invoice_paid",
    "mark_invoice_overdue",
    "update_overdue_invoices",
    "mark_reminder_sent",
    "get_invoices_count",
    "get_pending_invoices_count",
    "get_overdue_invoices_count",
    
    # Payment CRUD
    "create_payment",
    "get_payment",
    "get_invoice_payments",
    "get_customer_payments",
    "get_payments_count",
    
    # Rate Config
    "get_rate_config",
    "set_rate_config",
    "get_effective_rate",
    
    # Reminder Config
    "get_reminder_config",
    "set_reminder_config",
    
    # Calculations
    "calculate_amount_from_readings",
    "calculate_total_usage",
    "calculate_total_revenue",
    
    # Customer Auth
    "create_customer_auth",
    "get_customer_auth",
    "get_auth_by_username",
    "authenticate_customer",
    
    # Usage Alerts
    "create_usage_alert",
    "get_customer_alerts",
    "mark_alert_read",
    
    # Dashboard Stats
    "get_dashboard_stats",
    
    # Analytics Helpers
    "get_customer_usage_history",
    "get_customer_benchmark",
]

