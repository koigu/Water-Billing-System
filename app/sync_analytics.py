"""
Data sync service for MongoDB analytics collections.
Syncs data within MongoDB collections for analytics purposes.
"""
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger("sync")


class SyncService:
    """Service to sync and aggregate data in MongoDB analytics collections."""

    def __init__(self, db):
        self.db = db
        self.analytics = None  # Will be set when needed

    def get_analytics(self):
        """Lazy load analytics service."""
        if self.analytics is None:
            from app.analytics import AnalyticsService
            self.analytics = AnalyticsService(self.db)
        return self.analytics

    def sync_all_usage_trends(self) -> Dict:
        """Sync all customer usage data to usage_trends collection."""
        results = {"success": 0, "failed": 0}

        try:
            # Get all customers
            customers = list(self.db["customers"].find({}))
            
            for customer in customers:
                try:
                    customer_id = customer.get("id")
                    
                    # Get readings for this customer
                    readings = list(self.db["meter_readings"].find(
                        {"customer_id": customer_id}
                    ).sort("recorded_at", 1))

                    if len(readings) < 2:
                        continue

                    # Group readings by month
                    monthly_data = {}
                    for reading in readings:
                        if isinstance(reading.get("recorded_at"), datetime):
                            month_key = reading["recorded_at"].strftime("%Y-%m")
                        else:
                            continue
                        
                        if month_key not in monthly_data:
                            monthly_data[month_key] = []
                        monthly_data[month_key].append(reading.get("reading_value", 0))

                    # Calculate monthly totals and upsert to MongoDB
                    for month, values in monthly_data.items():
                        if len(values) >= 2:
                            year = int(month.split("-")[0])
                            total_usage = max(values) - min(values)

                            success = self.get_analytics().upsert_usage_trend(
                                customer_id=customer_id,
                                month=month,
                                year=year,
                                total_usage=total_usage,
                                readings_count=len(values),
                                avg_reading=sum(values) / len(values),
                                min_reading=min(values),
                                max_reading=max(values)
                            )
                            if success:
                                results["success"] += 1
                            else:
                                results["failed"] += 1

                except Exception as e:
                    logger.error(f"Error syncing usage for customer {customer_id}: {e}")
                    results["failed"] += 1

        except Exception as e:
            logger.error(f"Error in sync_all_usage_trends: {e}")

        return results

    def sync_customer_usage_trend(self, customer_id: int) -> bool:
        """Sync usage data for a single customer."""
        try:
            customer = self.db["customers"].find_one({"id": customer_id})
            if not customer:
                return False

            readings = list(self.db["meter_readings"].find(
                {"customer_id": customer_id}
            ).sort("recorded_at", 1))

            if len(readings) < 2:
                return True

            # Group readings by month
            monthly_data = {}
            for reading in readings:
                if isinstance(reading.get("recorded_at"), datetime):
                    month_key = reading["recorded_at"].strftime("%Y-%m")
                else:
                    continue
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = []
                monthly_data[month_key].append(reading.get("reading_value", 0))

            # Sync each month
            for month, values in monthly_data.items():
                if len(values) >= 2:
                    year = int(month.split("-")[0])
                    total_usage = max(values) - min(values)

                    self.get_analytics().upsert_usage_trend(
                        customer_id=customer_id,
                        month=month,
                        year=year,
                        total_usage=total_usage,
                        readings_count=len(values),
                        avg_reading=sum(values) / len(values),
                        min_reading=min(values),
                        max_reading=max(values)
                    )

            return True

        except Exception as e:
            logger.error(f"Error syncing customer usage trend: {e}")
            return False

    def sync_all_payment_analytics(self) -> Dict:
        """Sync all payment data to payment_analytics collection."""
        results = {"success": 0, "failed": 0}

        try:
            payments = list(self.db["payments"].find({}))
            
            for payment in payments:
                try:
                    invoice_id = payment.get("invoice_id")
                    invoice = self.db["invoices"].find_one({"id": invoice_id})
                    
                    if not invoice:
                        continue

                    payment_date = payment.get("payment_date", datetime.utcnow())
                    due_date = invoice.get("due_date", datetime.utcnow())
                    
                    if isinstance(due_date, str):
                        from datetime import datetime as dt
                        due_date = dt.fromisoformat(due_date.replace("Z", "+00:00"))

                    success = self.get_analytics().record_payment_analytics(
                        customer_id=invoice.get("customer_id"),
                        invoice_id=invoice_id,
                        payment_method=payment.get("payment_method", "cash"),
                        payment_date=payment_date,
                        due_date=due_date,
                        amount=payment.get("amount", 0)
                    )

                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1

                except Exception as e:
                    logger.error(f"Error syncing payment analytics: {e}")
                    results["failed"] += 1

        except Exception as e:
            logger.error(f"Error in sync_all_payment_analytics: {e}")

        return results

    def sync_all_customer_behavior(self) -> Dict:
        """Sync all customer behavior profiles to MongoDB."""
        results = {"success": 0, "failed": 0}

        try:
            customers = list(self.db["customers"].find({}))
            
            for customer in customers:
                try:
                    customer_id = customer.get("id")

                    # Get invoice stats
                    invoices = list(self.db["invoices"].find({"customer_id": customer_id}))
                    
                    total_invoices = len(invoices)
                    total_paid = sum(
                        inv.get("amount", 0) for inv in invoices if inv.get("status") == "paid"
                    )

                    # Get payment stats
                    payments = list(self.db["payments"].find({}))

                    customer_payments = []
                    for p in payments:
                        inv = next((i for i in invoices if i.get("id") == p.get("invoice_id")), None)
                        if inv:
                            customer_payments.append((p, inv))

                    if customer_payments:
                        payment_days_sum = 0
                        method_counts = {}
                        
                        for p, inv in customer_payments:
                            payment_date = p.get("payment_date", datetime.utcnow())
                            due_date = inv.get("due_date", datetime.utcnow())
                            
                            if isinstance(due_date, str):
                                from datetime import datetime as dt
                                due_date = dt.fromisoformat(due_date.replace("Z", "+00:00"))
                            
                            payment_days_sum += (payment_date - due_date).days
                            method = p.get("payment_method", "unknown")
                            method_counts[method] = method_counts.get(method, 0) + 1
                        
                        avg_payment_days = payment_days_sum / len(customer_payments)
                        preferred_method = max(method_counts, key=method_counts.get) if method_counts else None
                    else:
                        avg_payment_days = 0
                        preferred_method = None

                    # Calculate payment rate
                    paid_invoices = sum(1 for inv in invoices if inv.get("status") == "paid")
                    payment_rate = (paid_invoices / total_invoices * 100) if total_invoices > 0 else 0

                    # Get average monthly usage from readings
                    readings = list(self.db["meter_readings"].find(
                        {"customer_id": customer_id}
                    ).sort("recorded_at", 1))

                    if len(readings) >= 2:
                        usage_values = []
                        for i in range(len(readings) - 1):
                            r1 = readings[i].get("reading_value", 0)
                            r2 = readings[i + 1].get("reading_value", 0)
                            if r2 >= r1:
                                usage_values.append(r2 - r1)
                        avg_monthly_usage = sum(usage_values) / len(usage_values) if usage_values else 0
                    else:
                        avg_monthly_usage = 0

                    # Determine status based on recent activity
                    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
                    recent_readings = self.db["meter_readings"].count_documents({
                        "customer_id": customer_id,
                        "recorded_at": {"$gte": ninety_days_ago}
                    })

                    status = "active" if recent_readings > 0 else "inactive"

                    success = self.get_analytics().update_customer_behavior(
                        customer_id=customer_id,
                        total_invoices=total_invoices,
                        total_paid=total_paid,
                        avg_payment_days=round(avg_payment_days, 1),
                        preferred_payment_method=preferred_method,
                        avg_monthly_usage=round(avg_monthly_usage, 2),
                        payment_rate=round(payment_rate, 1),
                        status=status
                    )

                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1

                except Exception as e:
                    logger.error(f"Error syncing customer behavior for {customer_id}: {e}")
                    results["failed"] += 1

        except Exception as e:
            logger.error(f"Error in sync_all_customer_behavior: {e}")

        return results

    def run_full_sync(self) -> Dict:
        """Run a full sync of all data to MongoDB analytics."""
        logger.info("Starting full sync to MongoDB analytics...")
        results = {
            "usage_trends": self.sync_all_usage_trends(),
            "payment_analytics": self.sync_all_payment_analytics(),
            "customer_behavior": self.sync_all_customer_behavior()
        }
        logger.info(f"Full sync completed: {results}")
        return results


def get_sync_service(db=None):
    """Factory function to get sync service instance."""
    if db is None:
        from app.mongodb import get_db
        db = get_db()
    
    if db is None:
        return None
    
    return SyncService(db)

