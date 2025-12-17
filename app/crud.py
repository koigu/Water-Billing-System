"""
MongoDB CRUD operations for Water Billing System.
Complete rewrite for MongoDB-only implementation.
"""
import os
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app import mongodb
from app import schemas

logger = mongodb.logger


def get_db():
    """Get MongoDB database instance."""
    return mongodb.get_db()


def get_next_id(db, collection_name: str) -> int:
    """Get next auto-increment ID for a collection."""
    counter = db["counters"].find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return counter.get("seq", 1)


# ==================== CUSTOMER CRUD ====================

def create_customer(customer_data: dict) -> dict:
    """Create a new customer in MongoDB."""
    db = get_db()
    if db is None:
        return None
    
    customer_id = get_next_id(db, "customers")
    
    customer = {
        "id": customer_id,
        "name": customer_data.get("name"),
        "phone": customer_data.get("phone"),
        "email": customer_data.get("email"),
        "location": customer_data.get("location"),
        "created_at": datetime.utcnow()
    }
    
    result = db["customers"].insert_one(customer)
    customer["_id"] = result.inserted_id
    
    # Add initial reading if provided
    if customer_data.get("initial_reading") is not None:
        add_reading(customer_id, customer_data["initial_reading"])
    
    return customer


def get_customer(customer_id: int) -> Optional[dict]:
    """Get a customer by ID."""
    db = get_db()
    if db is None:
        return None
    return db["customers"].find_one({"id": customer_id})


def list_customers(skip: int = 0, limit: int = 100) -> List[dict]:
    """List all customers with pagination."""
    db = get_db()
    if db is None:
        return []
    return list(db["customers"].find().skip(skip).limit(limit))


def search_customers_by_name(name_query: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """Search customers by name (partial, case-insensitive)."""
    db = get_db()
    if db is None:
        return []
    return list(db["customers"].find({
        "name": {"$regex": name_query, "$options": "i"}
    }).skip(skip).limit(limit))


def update_customer(customer_id: int, update_data: dict) -> Optional[dict]:
    """Update a customer."""
    db = get_db()
    if db is None:
        return None
    
    update_data["updated_at"] = datetime.utcnow()
    result = db["customers"].find_one_and_update(
        {"id": customer_id},
        {"$set": update_data},
        return_document=True
    )
    return result


def delete_customer(customer_id: int) -> bool:
    """Delete a customer and all related data."""
    db = get_db()
    if db is None:
        return False
    
    # Delete related data
    db["meter_readings"].delete_many({"customer_id": customer_id})
    db["invoices"].delete_many({"customer_id": customer_id})
    db["customer_auth"].delete_many({"customer_id": customer_id})
    db["usage_alerts"].delete_many({"customer_id": customer_id})
    db["customer_behavior"].delete_many({"customer_id": customer_id})
    
    # Delete customer
    result = db["customers"].delete_one({"id": customer_id})
    return result.deleted_count > 0


# ==================== METER READING CRUD ====================

def add_reading(customer_id: int, reading_value: float) -> dict:
    """Add a meter reading for a customer."""
    db = get_db()
    if db is None:
        return None
    
    reading_id = get_next_id(db, "meter_readings")
    
    reading = {
        "id": reading_id,
        "customer_id": customer_id,
        "reading_value": reading_value,
        "recorded_at": datetime.utcnow()
    }
    
    result = db["meter_readings"].insert_one(reading)
    reading["_id"] = result.inserted_id
    return reading


def get_customer_readings(customer_id: int, limit: int = 100) -> List[dict]:
    """Get all readings for a customer."""
    db = get_db()
    if db is None:
        return []
    return list(db["meter_readings"].find(
        {"customer_id": customer_id}
    ).sort("recorded_at", -1).limit(limit))


def get_latest_two_readings(customer_id: int) -> List[dict]:
    """Get the two most recent readings for a customer."""
    db = get_db()
    if db is None:
        return []
    return list(db["meter_readings"].find(
        {"customer_id": customer_id}
    ).sort("recorded_at", -1).limit(2))


def get_all_readings(skip: int = 0, limit: int = 100) -> List[dict]:
    """Get all readings with customer info."""
    db = get_db()
    if db is None:
        return []
    
    pipeline = [
        {"$sort": {"recorded_at": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ]
    return list(db["meter_readings"].aggregate(pipeline))


# ==================== INVOICE CRUD ====================

def create_invoice(customer_id: int, amount: float, due_date: datetime, location: str = None) -> dict:
    """Create a new invoice."""
    db = get_db()
    if db is None:
        return None
    
    invoice_id = get_next_id(db, "invoices")
    
    invoice = {
        "id": invoice_id,
        "customer_id": customer_id,
        "amount": amount,
        "billing_from": datetime.utcnow(),
        "billing_to": datetime.utcnow(),
        "due_date": due_date,
        "sent_at": None,
        "status": "pending",
        "location": location,
        "reminder_sent_at": None,
        "created_at": datetime.utcnow()
    }
    
    result = db["invoices"].insert_one(invoice)
    invoice["_id"] = result.inserted_id
    return invoice


def get_invoice(invoice_id: int) -> Optional[dict]:
    """Get an invoice by ID."""
    db = get_db()
    if db is None:
        return None
    return db["invoices"].find_one({"id": invoice_id})


def list_invoices(skip: int = 0, limit: int = 100) -> List[dict]:
    """List all invoices with pagination."""
    db = get_db()
    if db is None:
        return []
    return list(db["invoices"].find().sort("created_at", -1).skip(skip).limit(limit))


def get_customer_invoices(customer_id: int) -> List[dict]:
    """Get all invoices for a customer."""
    db = get_db()
    if db is None:
        return []
    return list(db["invoices"].find(
        {"customer_id": customer_id}
    ).sort("created_at", -1))


def mark_invoice_paid(invoice_id: int) -> Optional[dict]:
    """Mark an invoice as paid."""
    db = get_db()
    if db is None:
        return None
    
    result = db["invoices"].find_one_and_update(
        {"id": invoice_id},
        {"$set": {"status": "paid", "paid_at": datetime.utcnow()}},
        return_document=True
    )
    return result


def update_overdue_invoices():
    """Update all invoices that are past due date to overdue status."""
    db = get_db()
    if db is None:
        return []
    
    now = datetime.utcnow()
    result = db["invoices"].update_many(
        {"status": {"$nin": ["paid", "cancelled"]}, "due_date": {"$lt": now}},
        {"$set": {"status": "overdue"}}
    )
    return result.modified_count


def mark_reminder_sent(invoice_id: int, when: datetime = None) -> Optional[dict]:
    """Mark that a reminder was sent for an invoice."""
    db = get_db()
    if db is None:
        return None
    
    when = when or datetime.utcnow()
    result = db["invoices"].find_one_and_update(
        {"id": invoice_id},
        {"$set": {"reminder_sent_at": when}},
        return_document=True
    )
    return result


# ==================== PAYMENT CRUD ====================

def create_payment(payment_data: dict) -> dict:
    """Create a payment record."""
    db = get_db()
    if db is None:
        return None
    
    payment_id = get_next_id(db, "payments")
    
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


def get_payment(payment_id: int) -> Optional[dict]:
    """Get a payment by ID."""
    db = get_db()
    if db is None:
        return None
    return db["payments"].find_one({"id": payment_id})


def get_invoice_payments(invoice_id: int) -> List[dict]:
    """Get all payments for an invoice."""
    db = get_db()
    if db is None:
        return []
    return list(db["payments"].find(
        {"invoice_id": invoice_id}
    ).sort("payment_date", -1))


def get_customer_payments(customer_id: int) -> List[dict]:
    """Get all payments for a customer."""
    db = get_db()
    if db is None:
        return []
    return list(db["payments"].find(
        {"customer_id": customer_id}
    ).sort("payment_date", -1))


# ==================== RATE CONFIG CRUD ====================

def get_rate_config() -> dict:
    """Get current rate configuration."""
    db = get_db()
    if db is None:
        return {"mode": "fixed", "value": 1.5}
    
    rc = db["rate_config"].find_one({})
    if not rc:
        # Create default from environment
        default = float(os.getenv("RATE_PER_UNIT", "1.5"))
        rc = {"mode": "fixed", "value": default, "created_at": datetime.utcnow()}
        db["rate_config"].insert_one(rc)
    return rc


def set_rate_config(mode: str, value: float) -> dict:
    """Set rate configuration."""
    db = get_db()
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


def get_effective_rate() -> float:
    """Get the effective rate per unit."""
    rc = get_rate_config()
    if rc.get("mode") == "fixed":
        return rc.get("value", 1.5)
    
    # percent mode: percentage relative to base RATE_PER_UNIT env var
    try:
        base = float(os.getenv("RATE_PER_UNIT", "1.5"))
    except Exception:
        base = 1.5
    return base * (1.0 + (rc.get("value") or 0.0) / 100.0)


# ==================== CALCULATIONS ====================

def calculate_amount_from_readings(customer_id: int, rate_per_unit: float = None):
    """Calculate invoice amount from latest two readings."""
    if rate_per_unit is None:
        rate_per_unit = get_effective_rate()
    
    readings = get_latest_two_readings(customer_id)
    if len(readings) < 2:
        return None
    
    latest = readings[0]
    previous = readings[1]
    
    usage = latest.get("reading_value", 0) - previous.get("reading_value", 0)
    if usage < 0:
        usage = 0
    
    amount = usage * rate_per_unit
    return amount, previous.get("recorded_at"), latest.get("recorded_at")


# ==================== CUSTOMER AUTH CRUD ====================

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_customer_auth(customer_id: int, username: str, password: str) -> dict:
    """Create customer authentication record."""
    db = get_db()
    if db is None:
        return None
    
    auth = {
        "customer_id": customer_id,
        "username": username,
        "password_hash": hash_password(password),
        "is_active": 1,
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    result = db["customer_auth"].insert_one(auth)
    auth["_id"] = result.inserted_id
    return auth


def get_customer_auth(customer_id: int) -> Optional[dict]:
    """Get customer authentication record."""
    db = get_db()
    if db is None:
        return None
    return db["customer_auth"].find_one({"customer_id": customer_id})


def get_auth_by_username(username: str) -> Optional[dict]:
    """Get auth record by username."""
    db = get_db()
    if db is None:
        return None
    return db["customer_auth"].find_one({"username": username})


def authenticate_customer(username: str, password: str) -> Optional[dict]:
    """Authenticate customer and update last login."""
    db = get_db()
    if db is None:
        return None
    
    hashed_password = hash_password(password)
    auth = db["customer_auth"].find_one({
        "username": username,
        "password_hash": hashed_password,
        "is_active": 1
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

def create_usage_alert(alert_data: dict) -> dict:
    """Create a usage alert."""
    db = get_db()
    if db is None:
        return None
    
    alert = {
        "customer_id": alert_data.get("customer_id"),
        "alert_type": alert_data.get("alert_type"),
        "message": alert_data.get("message"),
        "threshold_value": alert_data.get("threshold_value"),
        "actual_value": alert_data.get("actual_value"),
        "created_at": datetime.utcnow(),
        "is_read": 0,
        "resolved_at": None
    }
    
    result = db["usage_alerts"].insert_one(alert)
    alert["_id"] = result.inserted_id
    return alert


def get_customer_alerts(customer_id: int, unread_only: bool = False) -> List[dict]:
    """Get all alerts for a customer."""
    db = get_db()
    if db is None:
        return []
    
    query = {"customer_id": customer_id}
    if unread_only:
        query["is_read"] = 0
    
    return list(db["usage_alerts"].find(query).sort("created_at", -1))


def get_alert(alert_id: int) -> Optional[dict]:
    """Get a specific alert."""
    db = get_db()
    if db is None:
        return None
    return db["usage_alerts"].find_one({"id": alert_id})


def mark_alert_read(alert_id: int) -> Optional[dict]:
    """Mark an alert as read."""
    db = get_db()
    if db is None:
        return None
    
    result = db["usage_alerts"].find_one_and_update(
        {"id": alert_id},
        {"$set": {"is_read": 1}},
        return_document=True
    )
    return result


# ==================== DASHBOARD STATS ====================

def get_dashboard_stats() -> dict:
    """Get dashboard statistics."""
    db = get_db()
    if db is None:
        return {"total_customers": 0, "active_customers": 0, "inactive_customers": 0, "total_water_usage": 0}
    
    total_customers = db["customers"].count_documents({})
    
    # Consider customers active if they have readings in the last 90 days
    from datetime import timedelta
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    active_customers = db["customers"].count_documents({
        "id": {"$in": db["meter_readings"].distinct("customer_id", {"recorded_at": {"$gte": ninety_days_ago}})}
    })
    
    # Calculate total water usage from invoices
    rate = get_effective_rate()
    pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    result = list(db["invoices"].aggregate(pipeline))
    total_invoice_amount = result[0]["total"] if result else 0.0
    
    total_usage = total_invoice_amount / rate if rate > 0 else 0.0
    
    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "inactive_customers": total_customers - active_customers,
        "total_water_usage": round(total_usage, 2)
    }


# ==================== ANALYTICS HELPERS ====================

def get_customer_usage_history(customer_id: int, months: int = 12) -> List[dict]:
    """Get customer's usage history."""
    db = get_db()
    if db is None:
        return []
    
    from datetime import timedelta
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


def get_customer_benchmark(customer_id: int) -> Optional[dict]:
    """Get customer's usage benchmark."""
    customer = get_customer(customer_id)
    if not customer:
        return None
    
    db = get_db()
    if db is None:
        return None
    
    from datetime import timedelta
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    
    # Get customer's average usage
    customer_usage = db["meter_readings"].aggregate([
        {"$match": {"customer_id": customer_id, "recorded_at": {"$gte": ninety_days_ago}}},
        {"$group": {"_id": None, "avg": {"$avg": "$reading_value"}}}
    ])
    customer_usage = list(customer_usage)
    if not customer_usage:
        return None
    
    customer_avg = customer_usage[0]["avg"]
    
    # Get location average
    location_avg = None
    if customer.get("location"):
        location_result = db["meter_readings"].aggregate([
            {"$lookup": {
                "from": "customers",
                "localField": "customer_id",
                "foreignField": "id",
                "as": "customer"
            }},
            {"$unwind": "$customer"},
            {"$match": {
                "customer.location": customer["location"],
                "recorded_at": {"$gte": ninety_days_ago}
            }},
            {"$group": {"_id": None, "avg": {"$avg": "$reading_value"}}}
        ])
        location_result = list(location_result)
        if location_result:
            location_avg = location_result[0]["avg"]
    
    # Calculate percentile
    all_usages = db["meter_readings"].aggregate([
        {"$match": {"recorded_at": {"$gte": ninety_days_ago}}},
        {"$group": {"_id": "$customer_id", "avg": {"$avg": "$reading_value"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 3}}}
    ])
    all_usages = list(all_usages)
    
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
        "location_average": round(location_avg, 2) if location_avg else None,
        "percentile": round(percentile, 1),
        "comparison": comparison
    }

