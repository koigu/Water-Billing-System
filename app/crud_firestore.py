"""
Firestore-backed tenant CRUD operations.

This module mirrors the public function names used by main_multitenant.py so the
application can switch from MongoDB to Firestore with DATA_BACKEND=firestore.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.firebase_auth import get_firestore_client
from app.firebase_firestore import get_provider

logger = logging.getLogger("crud_firestore")


def _provider_ref(provider_slug: str):
    return get_firestore_client().collection("providers").document(provider_slug)


def _collection(provider_slug: str, name: str):
    return _provider_ref(provider_slug).collection(name)


def _doc_to_dict(doc) -> Optional[dict]:
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data.setdefault("id", _coerce_id(doc.id))
    return data


def _coerce_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _clean(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def _list_docs(query) -> List[dict]:
    return [_doc_to_dict(doc) for doc in query.stream() if doc.exists]


def get_next_id(provider_slug: str, collection_name: str) -> int:
    client = get_firestore_client()
    counter_ref = _provider_ref(provider_slug).collection("counters").document(collection_name)

    @firestore.transactional
    def increment(transaction):
        snapshot = counter_ref.get(transaction=transaction)
        current = int((snapshot.to_dict() or {}).get("seq", 0)) if snapshot.exists else 0
        next_id = current + 1
        transaction.set(counter_ref, {"seq": next_id, "updatedAt": datetime.utcnow()}, merge=True)
        return next_id

    return increment(client.transaction())


def get_next_invoice_number(provider_slug: str) -> str:
    seq = get_next_id(provider_slug, "invoice_sequences")
    provider = get_provider(provider_slug) or {}
    prefix = (provider.get("settings") or {}).get("invoice_number_prefix", "INV")
    return f"{prefix}{seq:06d}"


def create_customer(provider_slug: str, customer_data: dict) -> Optional[dict]:
    customer_id = get_next_id(provider_slug, "customers")
    customer = {
        "id": customer_id,
        "name": customer_data.get("name"),
        "phone": customer_data.get("phone"),
        "email": customer_data.get("email"),
        "location": customer_data.get("location"),
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }
    _collection(provider_slug, "customers").document(str(customer_id)).set(_clean(customer))

    initial_reading = customer_data.get("initial_reading")
    if initial_reading is not None:
        add_reading(provider_slug, customer_id, initial_reading)

    logger.info("Created Firestore customer %s for provider %s", customer_id, provider_slug)
    return customer


def get_customer(provider_slug: str, customer_id: int) -> Optional[dict]:
    customer = _doc_to_dict(_collection(provider_slug, "customers").document(str(customer_id)).get())
    if not customer or not customer.get("is_active", True):
        return None
    return customer


def list_customers(provider_slug: str, skip: int = 0, limit: int = 100) -> List[dict]:
    docs = sorted(_list_docs(
        _collection(provider_slug, "customers")
        .where(filter=FieldFilter("is_active", "==", True))
        .limit(skip + limit)
    ), key=lambda customer: customer.get("id", 0))
    return docs[skip:]


def search_customers_by_name(provider_slug: str, name_query: str, skip: int = 0, limit: int = 100) -> List[dict]:
    needle = name_query.lower()
    customers = [c for c in list_customers(provider_slug, 0, 1000) if needle in (c.get("name") or "").lower()]
    return customers[skip : skip + limit]


def update_customer(provider_slug: str, customer_id: int, update_data: dict) -> Optional[dict]:
    ref = _collection(provider_slug, "customers").document(str(customer_id))
    if not ref.get().exists:
        return None
    ref.update(_clean({**update_data, "updated_at": datetime.utcnow()}))
    return get_customer(provider_slug, customer_id)


def delete_customer(provider_slug: str, customer_id: int) -> bool:
    customer = get_customer(provider_slug, customer_id)
    if not customer:
        return False
    _collection(provider_slug, "customers").document(str(customer_id)).update({
        "is_active": False,
        "updated_at": datetime.utcnow(),
    })
    return True


def get_customers_count(provider_slug: str) -> int:
    return len(list_customers(provider_slug, 0, 10000))


def add_reading(provider_slug: str, customer_id: int, reading_value: float) -> Optional[dict]:
    reading_id = get_next_id(provider_slug, "meter_readings")
    reading = {
        "id": reading_id,
        "customer_id": customer_id,
        "reading_value": reading_value,
        "recorded_at": datetime.utcnow(),
    }
    _collection(provider_slug, "meterReadings").document(str(reading_id)).set(_clean(reading))
    return reading


def get_customer_readings(provider_slug: str, customer_id: int, limit: int = 100) -> List[dict]:
    readings = _list_docs(
        _collection(provider_slug, "meterReadings")
        .where(filter=FieldFilter("customer_id", "==", customer_id))
        .limit(limit)
    )
    return sorted(readings, key=lambda reading: reading.get("recorded_at") or datetime.min, reverse=True)[:limit]


def get_latest_two_readings(provider_slug: str, customer_id: int) -> List[dict]:
    return get_customer_readings(provider_slug, customer_id, limit=2)


def get_all_readings(provider_slug: str, skip: int = 0, limit: int = 100) -> List[dict]:
    docs = _list_docs(
        _collection(provider_slug, "meterReadings")
        .order_by("recorded_at", direction=firestore.Query.DESCENDING)
        .limit(skip + limit)
    )
    return docs[skip:]


def get_readings_count(provider_slug: str) -> int:
    return len(get_all_readings(provider_slug, 0, 10000))


def create_invoice(
    provider_slug: str,
    customer_id: int,
    amount: float,
    due_date: datetime,
    location: str = None,
    billing_from: datetime = None,
    billing_to: datetime = None,
) -> Optional[dict]:
    invoice_id = get_next_id(provider_slug, "invoices")
    now = datetime.utcnow()
    invoice = {
        "id": invoice_id,
        "invoice_number": get_next_invoice_number(provider_slug),
        "customer_id": customer_id,
        "amount": amount,
        "billing_from": billing_from or now,
        "billing_to": billing_to or now,
        "due_date": due_date,
        "sent_at": None,
        "status": "pending",
        "location": location,
        "reminder_sent_at": None,
        "created_at": now,
    }
    _collection(provider_slug, "invoices").document(str(invoice_id)).set(_clean(invoice))
    return invoice


def get_invoice(provider_slug: str, invoice_id: int) -> Optional[dict]:
    return _doc_to_dict(_collection(provider_slug, "invoices").document(str(invoice_id)).get())


def get_invoice_by_number(provider_slug: str, invoice_number: str) -> Optional[dict]:
    docs = _list_docs(
        _collection(provider_slug, "invoices")
        .where(filter=FieldFilter("invoice_number", "==", invoice_number))
        .limit(1)
    )
    return docs[0] if docs else None


def list_invoices(provider_slug: str, skip: int = 0, limit: int = 100) -> List[dict]:
    docs = _list_docs(
        _collection(provider_slug, "invoices")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(skip + limit)
    )
    return docs[skip:]


def get_customer_invoices(provider_slug: str, customer_id: int) -> List[dict]:
    invoices = _list_docs(
        _collection(provider_slug, "invoices")
        .where(filter=FieldFilter("customer_id", "==", customer_id))
    )
    return sorted(invoices, key=lambda invoice: invoice.get("created_at") or datetime.min, reverse=True)


def _update_invoice(provider_slug: str, invoice_id: int, update_data: dict) -> Optional[dict]:
    ref = _collection(provider_slug, "invoices").document(str(invoice_id))
    if not ref.get().exists:
        return None
    ref.update(_clean(update_data))
    return get_invoice(provider_slug, invoice_id)


def mark_invoice_paid(provider_slug: str, invoice_id: int) -> Optional[dict]:
    return _update_invoice(provider_slug, invoice_id, {"status": "paid", "paid_at": datetime.utcnow()})


def mark_invoice_overdue(provider_slug: str, invoice_id: int) -> Optional[dict]:
    return _update_invoice(provider_slug, invoice_id, {"status": "overdue"})


def update_overdue_invoices(provider_slug: str) -> int:
    now = datetime.utcnow()
    changed = 0
    for invoice in list_invoices(provider_slug, 0, 10000):
        if invoice.get("status") not in ("paid", "cancelled") and invoice.get("due_date") and invoice["due_date"] < now:
            if mark_invoice_overdue(provider_slug, invoice["id"]):
                changed += 1
    return changed


def mark_reminder_sent(provider_slug: str, invoice_id: int, when: datetime = None) -> Optional[dict]:
    return _update_invoice(provider_slug, invoice_id, {"reminder_sent_at": when or datetime.utcnow()})


def get_invoices_count(provider_slug: str) -> int:
    return len(list_invoices(provider_slug, 0, 10000))


def get_pending_invoices_count(provider_slug: str) -> int:
    return sum(1 for inv in list_invoices(provider_slug, 0, 10000) if inv.get("status") == "pending")


def get_overdue_invoices_count(provider_slug: str) -> int:
    return sum(1 for inv in list_invoices(provider_slug, 0, 10000) if inv.get("status") == "overdue")


def create_payment(provider_slug: str, payment_data: dict) -> Optional[dict]:
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
        "notes": payment_data.get("notes"),
    }
    _collection(provider_slug, "payments").document(str(payment_id)).set(_clean(payment))
    return payment


def get_payment(provider_slug: str, payment_id: int) -> Optional[dict]:
    return _doc_to_dict(_collection(provider_slug, "payments").document(str(payment_id)).get())


def get_invoice_payments(provider_slug: str, invoice_id: int) -> List[dict]:
    payments = _list_docs(
        _collection(provider_slug, "payments")
        .where(filter=FieldFilter("invoice_id", "==", invoice_id))
    )
    return sorted(payments, key=lambda payment: payment.get("payment_date") or datetime.min, reverse=True)


def get_customer_payments(provider_slug: str, customer_id: int) -> List[dict]:
    payments = _list_docs(
        _collection(provider_slug, "payments")
        .where(filter=FieldFilter("customer_id", "==", customer_id))
    )
    return sorted(payments, key=lambda payment: payment.get("payment_date") or datetime.min, reverse=True)


def get_payments_count(provider_slug: str) -> int:
    return len(_list_docs(_collection(provider_slug, "payments")))


def get_rate_config(provider_slug: str) -> Dict[str, Any]:
    doc = _provider_ref(provider_slug).collection("settings").document("rateConfig").get()
    if doc.exists:
        return _doc_to_dict(doc)
    provider = get_provider(provider_slug) or {}
    default_rate = provider.get("ratePerUnit", (provider.get("settings") or {}).get("rate_per_unit", 1.5))
    config = {"mode": "fixed", "value": default_rate, "currency": provider.get("currency", "KES"), "created_at": datetime.utcnow()}
    _provider_ref(provider_slug).collection("settings").document("rateConfig").set(config)
    return config


def set_rate_config(provider_slug: str, mode: str, value: float) -> Dict[str, Any]:
    config = {"mode": mode, "value": value, "updated_at": datetime.utcnow()}
    _provider_ref(provider_slug).collection("settings").document("rateConfig").set(config, merge=True)
    return get_rate_config(provider_slug)


def get_effective_rate(provider_slug: str) -> float:
    rc = get_rate_config(provider_slug)
    if rc.get("mode") == "fixed":
        return float(rc.get("value", 1.5))
    try:
        base = float(os.getenv("RATE_PER_UNIT", "1.5"))
    except Exception:
        base = 1.5
    return base * (1.0 + (float(rc.get("value") or 0.0) / 100.0))


def get_reminder_config(provider_slug: str) -> Dict[str, Any]:
    doc = _provider_ref(provider_slug).collection("settings").document("reminderConfig").get()
    if doc.exists:
        return _doc_to_dict(doc)
    config = {"reminder_days": 5, "auto_resend_invoice": True, "max_reminders": 3, "updated_at": None}
    _provider_ref(provider_slug).collection("settings").document("reminderConfig").set(config)
    return config


def set_reminder_config(
    provider_slug: str,
    reminder_days: int,
    auto_resend_invoice: bool = True,
    max_reminders: int = 3,
    updated_by: str = None,
) -> Dict[str, Any]:
    config = {
        "reminder_days": reminder_days,
        "auto_resend_invoice": auto_resend_invoice,
        "max_reminders": max_reminders,
        "updated_by": updated_by,
        "updated_at": datetime.utcnow(),
    }
    _provider_ref(provider_slug).collection("settings").document("reminderConfig").set(config, merge=True)
    return get_reminder_config(provider_slug)


def calculate_amount_from_readings(provider_slug: str, customer_id: int, rate_per_unit: float = None):
    rate = rate_per_unit if rate_per_unit is not None else get_effective_rate(provider_slug)
    readings = get_latest_two_readings(provider_slug, customer_id)
    if len(readings) < 2:
        return None
    latest, previous = readings[0], readings[1]
    usage = max((latest.get("reading_value") or 0) - (previous.get("reading_value") or 0), 0)
    return usage * rate, previous.get("recorded_at"), latest.get("recorded_at")


def calculate_total_usage(provider_slug: str) -> float:
    rate = get_effective_rate(provider_slug)
    total_amount = sum(inv.get("amount", 0) for inv in list_invoices(provider_slug, 0, 10000) if inv.get("status") != "cancelled")
    return round(total_amount / rate, 2) if rate > 0 else 0.0


def calculate_total_revenue(provider_slug: str) -> float:
    return sum(inv.get("amount", 0) for inv in list_invoices(provider_slug, 0, 10000) if inv.get("status") == "paid")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_customer_auth(provider_slug: str, customer_id: int, username: str, password: str) -> Optional[dict]:
    auth = {
        "customer_id": customer_id,
        "username": username,
        "password_hash": hash_password(password),
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None,
    }
    _collection(provider_slug, "customerAuth").document(str(customer_id)).set(auth)
    return auth


def get_customer_auth(provider_slug: str, customer_id: int) -> Optional[dict]:
    return _doc_to_dict(_collection(provider_slug, "customerAuth").document(str(customer_id)).get())


def get_auth_by_username(provider_slug: str, username: str) -> Optional[dict]:
    docs = _list_docs(
        _collection(provider_slug, "customerAuth")
        .where(filter=FieldFilter("username", "==", username))
        .limit(1)
    )
    return docs[0] if docs else None


def authenticate_customer(provider_slug: str, username: str, password: str) -> Optional[dict]:
    auth = get_auth_by_username(provider_slug, username)
    if not auth or not auth.get("is_active", True):
        return None
    if auth.get("password_hash") != hash_password(password):
        return None
    _collection(provider_slug, "customerAuth").document(str(auth["customer_id"])).update({"last_login": datetime.utcnow()})
    auth["last_login"] = datetime.utcnow()
    return auth


def create_usage_alert(provider_slug: str, alert_data: dict) -> Optional[dict]:
    alert_id = get_next_id(provider_slug, "usage_alerts")
    alert = {
        "id": alert_id,
        "customer_id": alert_data.get("customer_id"),
        "alert_type": alert_data.get("alert_type"),
        "message": alert_data.get("message"),
        "threshold_value": alert_data.get("threshold_value"),
        "actual_value": alert_data.get("actual_value"),
        "created_at": datetime.utcnow(),
        "is_read": False,
        "resolved_at": None,
    }
    _collection(provider_slug, "usageAlerts").document(str(alert_id)).set(_clean(alert))
    return alert


def get_customer_alerts(provider_slug: str, customer_id: int, unread_only: bool = False) -> List[dict]:
    alerts = _list_docs(
        _collection(provider_slug, "usageAlerts")
        .where(filter=FieldFilter("customer_id", "==", customer_id))
    )
    filtered = [alert for alert in alerts if not unread_only or not alert.get("is_read")]
    return sorted(filtered, key=lambda alert: alert.get("created_at") or datetime.min, reverse=True)


def mark_alert_read(provider_slug: str, alert_id: int) -> Optional[dict]:
    ref = _collection(provider_slug, "usageAlerts").document(str(alert_id))
    if not ref.get().exists:
        return None
    ref.update({"is_read": True})
    return _doc_to_dict(ref.get())


def get_dashboard_stats(provider_slug: str) -> Dict[str, Any]:
    customers = list_customers(provider_slug, 0, 10000)
    readings = get_all_readings(provider_slug, 0, 10000)
    invoices = list_invoices(provider_slug, 0, 10000)
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    active_customer_ids = {r.get("customer_id") for r in readings if r.get("recorded_at") and r["recorded_at"] >= ninety_days_ago}
    return {
        "total_customers": len(customers),
        "active_customers": len(active_customer_ids),
        "inactive_customers": max(len(customers) - len(active_customer_ids), 0),
        "total_water_usage": calculate_total_usage(provider_slug),
        "total_revenue": round(calculate_total_revenue(provider_slug), 2),
        "pending_invoices": sum(1 for inv in invoices if inv.get("status") == "pending"),
        "overdue_invoices": sum(1 for inv in invoices if inv.get("status") == "overdue"),
    }


def get_customer_usage_history(provider_slug: str, customer_id: int, months: int = 12) -> List[dict]:
    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    readings = [r for r in reversed(get_customer_readings(provider_slug, customer_id, 1000)) if r.get("recorded_at") and r["recorded_at"] >= cutoff]
    by_month: Dict[str, List[float]] = {}
    for reading in readings:
        key = reading["recorded_at"].strftime("%Y-%m")
        by_month.setdefault(key, []).append(reading.get("reading_value") or 0)
    return [
        {"date": month, "usage": max(values) - (sum(values) / len(values)), "reading": max(values)}
        for month, values in sorted(by_month.items())
    ]


def get_customer_benchmark(provider_slug: str, customer_id: int) -> Optional[Dict[str, Any]]:
    readings = get_customer_readings(provider_slug, customer_id, 100)
    if not readings:
        return None
    avg = sum(r.get("reading_value") or 0 for r in readings) / len(readings)
    return {"customer_average": round(avg, 2), "percentile": 50, "comparison": "Average usage"}


__all__ = [
    "get_next_id",
    "get_next_invoice_number",
    "create_customer",
    "get_customer",
    "list_customers",
    "search_customers_by_name",
    "update_customer",
    "delete_customer",
    "get_customers_count",
    "add_reading",
    "get_customer_readings",
    "get_latest_two_readings",
    "get_all_readings",
    "get_readings_count",
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
    "create_payment",
    "get_payment",
    "get_invoice_payments",
    "get_customer_payments",
    "get_payments_count",
    "get_rate_config",
    "set_rate_config",
    "get_effective_rate",
    "get_reminder_config",
    "set_reminder_config",
    "calculate_amount_from_readings",
    "calculate_total_usage",
    "calculate_total_revenue",
    "hash_password",
    "create_customer_auth",
    "get_customer_auth",
    "get_auth_by_username",
    "authenticate_customer",
    "create_usage_alert",
    "get_customer_alerts",
    "mark_alert_read",
    "get_dashboard_stats",
    "get_customer_usage_history",
    "get_customer_benchmark",
]
