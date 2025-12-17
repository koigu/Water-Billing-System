"""
Analytics service for MongoDB collections.
Handles usage trends, payment analytics, customer behavior, and staff metrics.
Includes async support, validation, caching, and advanced analytics.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pymongo import MongoClient
from bson import ObjectId
import logging
import math
from statistics import mean, stdev

from app.schemas_analytics import (
    UsageTrendCreate, UsageTrendResponse, UsageTrendAnalytics,
    PaymentAnalyticsCreate, PaymentAnalyticsResponse, PaymentMethodsResponse,
    PaymentTimingAnalysis, CustomerBehaviorCreate, CustomerBehaviorResponse,
    CustomerProfile, CustomerSegment, CustomerSegmentStats,
    StaffMetricsCreate, StaffMetricsResponse, ReminderConfigCreate,
    ReminderConfigResponse, RevenueAnalytics, RevenueForecast, RevenueSummary,
    DataQualityReport, DataQualityMetric, DashboardAnalytics, TrendDirection,
    PaginationParams, PaginatedResponse, DateRangeParams
)
from app.exceptions_analytics import (
    AnalyticsException, DatabaseException, ValidationException,
    DocumentNotFoundException, InsufficientDataException, handle_exception
)
from app.cache_decorators import (
    get_cache, cache_decorator, cached_method, invalidate_cache_on_change
)

logger = logging.getLogger("analytics")


class AnalyticsService:
    """Enhanced service class for analytics operations on MongoDB."""

    def __init__(self, db):
        self.db = db
        self.usage_trends = db["usage_trends"] if db is not None else None
        self.payment_analytics = db["payment_analytics"] if db is not None else None
        self.customer_behavior = db["customer_behavior"] if db is not None else None
        self.staff_metrics = db["staff_metrics"] if db is not None else None
        self.reminder_config = db["reminder_config"] if db is not None else None
        self._cache = get_cache()

    # ==================== USAGE TRENDS ====================

    def upsert_usage_trend(
        self,
        customer_id: int,
        month: str,
        year: int,
        total_usage: float,
        readings_count: int,
        avg_reading: float,
        min_reading: float,
        max_reading: float
    ) -> bool:
        """Insert or update usage trend data."""
        if self.usage_trends is None:
            return False
        try:
            result = self.usage_trends.update_one(
                {"customer_id": customer_id, "month": month},
                {
                    "$set": {
                        "customer_id": customer_id,
                        "month": month,
                        "year": year,
                        "total_usage": total_usage,
                        "readings_count": readings_count,
                        "avg_reading": avg_reading,
                        "min_reading": min_reading,
                        "max_reading": max_reading,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error upserting usage trend: {e}")
            return False

    def get_customer_usage_trends(self, customer_id: int, months: int = 12) -> List[Dict]:
        """Get usage trends for a specific customer."""
        if self.usage_trends is None:
            return []
        try:
            trends = self.usage_trends.find(
                {"customer_id": customer_id}
            ).sort("month", -1).limit(months)
            return list(trends)
        except Exception as e:
            logger.error(f"Error getting customer usage trends: {e}")
            return []

    def get_monthly_usage_trends(self, year: int = None, month: int = None) -> List[Dict]:
        """Get aggregated monthly usage trends."""
        if self.usage_trends is None:
            return []
        try:
            query = {}
            if year:
                query["year"] = year
            if month:
                query["month"] = f"{year:04d}-{month:02d}"

            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$month",
                    "total_usage": {"$sum": "$total_usage"},
                    "customer_count": {"$sum": 1},
                    "avg_usage_per_customer": {"$avg": "$total_usage"},
                    "total_readings": {"$sum": "$readings_count"}
                }},
                {"$sort": {"_id": -1}}
            ]
            return list(self.usage_trends.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting monthly usage trends: {e}")
            return []

    def get_yearly_usage_trends(self, year: int = None) -> List[Dict]:
        """Get aggregated yearly usage trends."""
        if self.usage_trends is None:
            return []
        try:
            pipeline = [
                {"$match": {"year": year} if year else {}},
                {"$group": {
                    "_id": "$year",
                    "total_usage": {"$sum": "$total_usage"},
                    "customer_count": {"$sum": 1},
                    "avg_usage_per_customer": {"$avg": "$total_usage"},
                    "total_readings": {"$sum": "$readings_count"}
                }},
                {"$sort": {"_id": -1}}
            ]
            return list(self.usage_trends.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting yearly usage trends: {e}")
            return []

    # ==================== PAYMENT ANALYTICS ====================

    def record_payment_analytics(
        self,
        customer_id: int,
        invoice_id: int,
        payment_method: str,
        payment_date: datetime,
        due_date: datetime,
        amount: float
    ) -> bool:
        """Record payment analytics data."""
        if self.payment_analytics is None:
            return False
        try:
            days_to_pay = (payment_date - due_date).days
            month = payment_date.strftime("%Y-%m")
            year = payment_date.year

            result = self.payment_analytics.update_one(
                {"invoice_id": invoice_id},
                {
                    "$set": {
                        "customer_id": customer_id,
                        "invoice_id": invoice_id,
                        "payment_method": payment_method,
                        "payment_date": payment_date,
                        "due_date": due_date,
                        "days_to_pay": days_to_pay,
                        "amount": amount,
                        "month": month,
                        "year": year,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error recording payment analytics: {e}")
            return False

    def get_payment_methods_analysis(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get payment method preferences analysis."""
        if self.payment_analytics is None:
            return {"methods": [], "preferred_method": None, "trend": "stable"}
        try:
            query = {}
            if start_date and end_date:
                query["payment_date"] = {"$gte": start_date, "$lte": end_date}

            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$payment_method",
                    "count": {"$sum": 1},
                    "total_amount": {"$sum": "$amount"},
                    "avg_days_to_pay": {"$avg": "$days_to_pay"}
                }},
                {"$sort": {"count": -1}}
            ]
            results = list(self.payment_analytics.aggregate(pipeline))

            total = sum(r["count"] for r in results)
            methods = []
            for r in results:
                methods.append({
                    "method": r["_id"],
                    "count": r["count"],
                    "percentage": round((r["count"] / total * 100), 2) if total > 0 else 0,
                    "total_amount": round(r["total_amount"], 2),
                    "avg_days_to_pay": round(r["avg_days_to_pay"], 1)
                })

            preferred = methods[0]["method"] if methods else None
            trend = "stable"

            return {
                "methods": methods,
                "preferred_method": preferred,
                "trend": trend,
                "total_payments": total,
                "total_amount": sum(m["total_amount"] for m in methods)
            }
        except Exception as e:
            logger.error(f"Error getting payment methods analysis: {e}")
            return {"methods": [], "preferred_method": None, "trend": "stable"}

    def get_payment_timing_analysis(self, customer_id: int = None) -> List[Dict]:
        """Get payment timing patterns analysis."""
        if self.payment_analytics is None:
            return []
        try:
            match = {}
            if customer_id:
                match["customer_id"] = customer_id

            pipeline = [
                {"$match": match},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$payment_date"},
                        "month": {"$month": "$payment_date"}
                    },
                    "avg_days_to_pay": {"$avg": "$days_to_pay"},
                    "early_payments": {"$sum": {"$cond": [{"$lt": ["$days_to_pay", 0]}, 1, 0]}},
                    "on_time_payments": {"$sum": {"$cond": [{"$and": [{"$gte": ["$days_to_pay", 0]}, {"$lte": ["$days_to_pay", 3]}]}, 1, 0]}},
                    "late_payments": {"$sum": {"$cond": [{"$gt": ["$days_to_pay", 3]}, 1, 0]}},
                    "total_payments": {"$sum": 1}
                }},
                {"$sort": {"_id.year": -1, "_id.month": -1}}
            ]
            return list(self.payment_analytics.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting payment timing analysis: {e}")
            return []

    # ==================== CUSTOMER BEHAVIOR ====================

    def update_customer_behavior(
        self,
        customer_id: int,
        total_invoices: int,
        total_paid: float,
        avg_payment_days: float,
        preferred_payment_method: str,
        avg_monthly_usage: float,
        payment_rate: float,
        status: str = "active"
    ) -> bool:
        """Update customer behavior profile."""
        if self.customer_behavior is None:
            return False
        try:
            result = self.customer_behavior.update_one(
                {"customer_id": customer_id},
                {
                    "$set": {
                        "customer_id": customer_id,
                        "total_invoices": total_invoices,
                        "total_paid": total_paid,
                        "avg_payment_days": avg_payment_days,
                        "preferred_payment_method": preferred_payment_method,
                        "avg_monthly_usage": avg_monthly_usage,
                        "payment_rate": payment_rate,
                        "status": status,
                        "last_activity": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error updating customer behavior: {e}")
            return False

    def get_customer_profile(self, customer_id: int) -> Optional[Dict]:
        """Get full customer profile with analytics."""
        if self.customer_behavior is None:
            return None
        try:
            profile = self.customer_behavior.find_one({"customer_id": customer_id})
            if profile:
                profile["usage_trends"] = self.get_customer_usage_trends(customer_id, 12)
                profile["payment_timing"] = self.get_payment_timing_analysis(customer_id)
            return profile
        except Exception as e:
            logger.error(f"Error getting customer profile: {e}")
            return None

    def get_active_inactive_counts(self) -> Dict:
        """Get count of active and inactive customers."""
        if self.customer_behavior is None:
            return {"active": 0, "inactive": 0}
        try:
            active = self.customer_behavior.count_documents({"status": "active"})
            inactive = self.customer_behavior.count_documents({"status": "inactive"})
            return {"active": active, "inactive": inactive, "total": active + inactive}
        except Exception as e:
            logger.error(f"Error getting active/inactive counts: {e}")
            return {"active": 0, "inactive": 0, "total": 0}

    # ==================== STAFF METRICS ====================

    def update_staff_metrics(
        self,
        staff_id: str,
        month: str,
        year: int,
        invoices_generated: int = 0,
        payments_collected: float = 0,
        customers_added: int = 0,
        readings_recorded: int = 0
    ) -> bool:
        """Update staff performance metrics."""
        if self.staff_metrics is None:
            return False
        try:
            efficiency_score = self._calculate_efficiency_score(
                invoices_generated, payments_collected, customers_added, readings_recorded
            )

            result = self.staff_metrics.update_one(
                {"staff_id": staff_id, "month": month},
                {
                    "$set": {
                        "staff_id": staff_id,
                        "month": month,
                        "year": year,
                        "invoices_generated": invoices_generated,
                        "payments_collected": payments_collected,
                        "customers_added": customers_added,
                        "readings_recorded": readings_recorded,
                        "efficiency_score": efficiency_score,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error updating staff metrics: {e}")
            return False

    def _calculate_efficiency_score(
        self,
        invoices: int,
        payments: float,
        customers: int,
        readings: int
    ) -> float:
        """Calculate staff efficiency score."""
        score = (invoices * 10) + (payments / 100) + (customers * 20) + (readings * 5)
        return round(score, 2)

    def get_staff_trends(self, staff_id: str = None, months: int = 6) -> List[Dict]:
        """Get staff performance trends."""
        if self.staff_metrics is None:
            return []
        try:
            query = {}
            if staff_id:
                query["staff_id"] = staff_id

            metrics = self.staff_metrics.find(query).sort(
                [("year", -1), ("month", -1)]
            ).limit(months)
            return list(metrics)
        except Exception as e:
            logger.error(f"Error getting staff trends: {e}")
            return []

    def get_top_performing_staff(self, limit: int = 5) -> List[Dict]:
        """Get top performing staff members."""
        if self.staff_metrics is None:
            return []
        try:
            pipeline = [
                {"$group": {
                    "_id": "$staff_id",
                    "total_invoices": {"$sum": "$invoices_generated"},
                    "total_payments": {"$sum": "$payments_collected"},
                    "total_customers": {"$sum": "$customers_added"},
                    "total_readings": {"$sum": "$readings_recorded"},
                    "avg_efficiency": {"$avg": "$efficiency_score"},
                    "months_active": {"$sum": 1}
                }},
                {"$sort": {"total_payments": -1}},
                {"$limit": limit}
            ]
            return list(self.staff_metrics.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting top staff: {e}")
            return []

    # ==================== REMINDER CONFIG ====================

    def get_reminder_config(self) -> Dict:
        """Get reminder configuration."""
        if self.reminder_config is None:
            return {"reminder_days": 5, "auto_resend_invoice": True, "max_reminders": 3}
        try:
            config = self.reminder_config.find_one({"setting_name": "reminder_settings"})
            if config:
                return {
                    "reminder_days": config.get("reminder_days", 5),
                    "auto_resend_invoice": config.get("auto_resend_invoice", True),
                    "max_reminders": config.get("max_reminders", 3),
                    "updated_by": config.get("updated_by"),
                    "updated_at": config.get("updated_at")
                }
            return {"reminder_days": 5, "auto_resend_invoice": True, "max_reminders": 3}
        except Exception as e:
            logger.error(f"Error getting reminder config: {e}")
            return {"reminder_days": 5, "auto_resend_invoice": True, "max_reminders": 3}

    def set_reminder_config(
        self,
        reminder_days: int,
        auto_resend_invoice: bool,
        max_reminders: int,
        updated_by: str
    ) -> bool:
        """Set reminder configuration."""
        if self.reminder_config is None:
            return False
        try:
            result = self.reminder_config.update_one(
                {"setting_name": "reminder_settings"},
                {
                    "$set": {
                        "setting_name": "reminder_settings",
                        "reminder_days": reminder_days,
                        "auto_resend_invoice": auto_resend_invoice,
                        "max_reminders": max_reminders,
                        "updated_by": updated_by,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error setting reminder config: {e}")
            return False


    # ==================== ADVANCED ANALYTICS METHODS ====================

    def get_usage_trend_analysis(
        self,
        customer_id: int,
        months: int = 12
    ) -> Dict:
        """Get comprehensive usage trend analysis with trend direction and forecasting."""
        trends = self.get_customer_usage_trends(customer_id, months)

        if len(trends) < 2:
            return {
                "customer_id": customer_id,
                "current_usage": 0,
                "previous_usage": 0,
                "usage_change": 0,
                "trend_direction": "stable",
                "trend_percentage": 0,
                "months_analyzed": len(trends),
                "avg_monthly_usage": 0,
                "prediction_next_month": None,
                "confidence_score": 0
            }

        # Calculate trend direction and percentage
        current_usage = trends[0].get("total_usage", 0) if isinstance(trends[0], dict) else trends[0].total_usage
        previous_usage = trends[1].get("total_usage", 0) if len(trends) > 1 else current_usage

        usage_change = current_usage - previous_usage
        trend_percentage = (usage_change / previous_usage * 100) if previous_usage > 0 else 0

        if trend_percentage > 5:
            trend_direction = "increasing"
        elif trend_percentage < -5:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        # Calculate average monthly usage
        usages = [t.get("total_usage", 0) for t in trends]
        avg_monthly_usage = sum(usages) / len(usages)

        # Simple forecasting (moving average)
        prediction_next_month = None
        confidence_score = 0
        if len(trends) >= 3:
            recent_usages = usages[:3]
            prediction_next_month = sum(recent_usages) / len(recent_usages)
            # Confidence based on data consistency
            variance = sum((u - prediction_next_month) ** 2 for u in recent_usages) / len(recent_usages)
            std_dev = variance ** 0.5
            confidence_score = max(0, min(100, 100 - (std_dev / prediction_next_month * 100))) if prediction_next_month > 0 else 0

        return {
            "customer_id": customer_id,
            "current_usage": round(current_usage, 2),
            "previous_usage": round(previous_usage, 2),
            "usage_change": round(usage_change, 2),
            "trend_direction": trend_direction,
            "trend_percentage": round(trend_percentage, 2),
            "months_analyzed": len(trends),
            "avg_monthly_usage": round(avg_monthly_usage, 2),
            "prediction_next_month": round(prediction_next_month, 2) if prediction_next_month else None,
            "confidence_score": round(confidence_score, 2)
        }

    def get_payment_timing_with_trends(
        self,
        customer_id: int = None,
        months: int = 12
    ) -> List[PaymentTimingAnalysis]:
        """Get payment timing patterns with trend analysis."""
        raw_data = self.get_payment_timing_analysis(customer_id)

        results = []
        for data in raw_data[-months:]:
            year = data.get("_id", {}).get("year", 0)
            month = data.get("_id", {}).get("month", 0)
            total = data.get("total_payments", 0)

            on_time_pct = (data.get("on_time_payments", 0) / total * 100) if total > 0 else 0
            early_pct = (data.get("early_payments", 0) / total * 100) if total > 0 else 0
            late_pct = (data.get("late_payments", 0) / total * 100) if total > 0 else 0

            # Determine trend based on payment patterns
            trend = "stable"
            if on_time_pct > 80:
                trend = "improving"
            elif late_pct > 30:
                trend = "declining"

            results.append(PaymentTimingAnalysis(
                year=year,
                month=month,
                avg_days_to_pay=round(data.get("avg_days_to_pay", 0), 1),
                early_payments=data.get("early_payments", 0),
                on_time_payments=data.get("on_time_payments", 0),
                late_payments=data.get("late_payments", 0),
                total_payments=total,
                on_time_percentage=round(on_time_pct, 2),
                early_percentage=round(early_pct, 2),
                late_percentage=round(late_pct, 2),
                trend=TrendDirection(trend)
            ))

        return results

    # ==================== CUSTOMER SEGMENTATION ====================

    def get_customer_segment(
        self,
        customer_id: int
    ) -> Dict:
        """Determine customer segment based on behavior patterns."""
        behavior = self.customer_behavior.find_one({"customer_id": customer_id}) if self.customer_behavior else None

        if not behavior:
            return {
                "customer_id": customer_id,
                "segment": "new",
                "risk_score": 0,
                "loyalty_score": 0,
                "recommendations": ["Collect more data for accurate segmentation"]
            }

        payment_rate = behavior.get("payment_rate", 0)
        avg_payment_days = behavior.get("avg_payment_days", 0)
        total_paid = behavior.get("total_paid", 0)
        status = behavior.get("status", "inactive")

        # Calculate risk score (0-100, higher is riskier)
        risk_factors = []
        risk_score = 0

        if payment_rate < 70:
            risk_score += 30
            risk_factors.append("Low payment rate")
        elif payment_rate < 90:
            risk_score += 15
            risk_factors.append("Below average payment rate")

        if avg_payment_days > 10:
            risk_score += 25
            risk_factors.append("Slow payments")
        elif avg_payment_days > 5:
            risk_score += 10
            risk_factors.append("Occasional late payments")

        if status == "inactive":
            risk_score += 20
            risk_factors.append("Inactive customer")

        if avg_payment_days < 0:
            risk_score -= 10  # Early payments reduce risk

        risk_score = max(0, min(100, risk_score))

        # Calculate loyalty score (0-100, higher is more loyal)
        loyalty_score = 0

        if payment_rate >= 95:
            loyalty_score += 40
        elif payment_rate >= 90:
            loyalty_score += 30
        elif payment_rate >= 80:
            loyalty_score += 20

        if avg_payment_days <= 3:
            loyalty_score += 30
        elif avg_payment_days <= 5:
            loyalty_score += 20

        if total_paid > 1000:
            loyalty_score += 20
        elif total_paid > 500:
            loyalty_score += 10

        loyalty_score = min(100, loyalty_score)

        # Determine segment
        if risk_score >= 50:
            segment = "at_risk"
        elif loyalty_score >= 80:
            segment = "loyal"
        elif loyalty_score >= 50 and risk_score < 30:
            segment = "high_value"
        elif behavior.get("total_invoices", 0) <= 3:
            segment = "new"
        elif risk_score >= 30:
            segment = "churning"
        else:
            segment = "average"

        # Generate recommendations
        recommendations = []
        if risk_score >= 50:
            recommendations.append("Consider proactive outreach to reduce churn risk")
        if avg_payment_days > 5:
            recommendations.append("Send payment reminders before due date")
        if segment == "high_value":
            recommendations.append("Consider loyalty rewards program")
        if segment == "new":
            recommendations.append("Onboard with welcome materials and support")
        if not recommendations:
            recommendations.append("Continue current engagement strategy")

        return {
            "customer_id": customer_id,
            "segment": segment,
            "risk_score": risk_score,
            "loyalty_score": loyalty_score,
            "recommendations": recommendations
        }

    def get_segment_stats(self) -> List[CustomerSegmentStats]:
        """Get statistics for all customer segments."""
        if not self.customer_behavior:
            return []

        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$payment_rate", 95]}, "then": "loyal"},
                                {"case": {"$and": [{"$gte": ["$payment_rate", 80]}, {"$lt": ["$payment_rate", 95]}]}, "then": "average"},
                            ],
                            "default": "at_risk"
                        }
                    },
                    "count": {"$sum": 1},
                    "total_revenue": {"$sum": "$total_paid"},
                    "avg_payment_rate": {"$avg": "$payment_rate"},
                    "avg_monthly_usage": {"$avg": "$avg_monthly_usage"}
                }
            }
        ]

        results = list(self.customer_behavior.aggregate(pipeline))
        total_customers = sum(r["count"] for r in results)

        segment_stats = []
        for r in results:
            segment = r["_id"] if r["_id"] else "average"
            pct = (r["count"] / total_customers * 100) if total_customers > 0 else 0

            segment_stats.append(CustomerSegmentStats(
                segment=CustomerSegment(segment),
                count=r["count"],
                total_revenue=round(r["total_revenue"], 2),
                avg_payment_rate=round(r["avg_payment_rate"], 2),
                avg_monthly_usage=round(r["avg_monthly_usage"], 2),
                percentage_of_total=round(pct, 2)
            ))

        return segment_stats

    # ==================== REVENUE ANALYTICS ====================

    def get_revenue_analytics(
        self,
        year: int = None,
        month: int = None
    ) -> List[RevenueAnalytics]:
        """Get revenue analytics by month."""
        if not self.db:
            return []

        try:
            # Get invoices for the period
            match_query = {}
            if year:
                match_query["year"] = year
            if month:
                match_query["month"] = f"{year:04d}-{month:02d}"

            # Aggregate invoice data
            pipeline = [
                {"$match": match_query},
                {"$group": {
                    "_id": "$month",
                    "total_revenue": {"$sum": "$amount"},
                    "invoice_count": {"$sum": 1},
                    "paid_amount": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, "$amount", 0]}},
                    "pending_amount": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, "$amount", 0]}},
                    "overdue_amount": {"$sum": {"$cond": [{"$eq": ["$status", "overdue"]}, "$amount", 0]}}
                }},
                {"$sort": {"_id": -1}}
            ]

            results = list(self.db["invoices"].aggregate(pipeline))

            revenue_analytics = []
            for r in results:
                month_str = r["_id"]
                month_year = int(month_str.split("-")[0]) if month_str else 0
                month_num = int(month_str.split("-")[1]) if month_str else 0

                collection_rate = (r["paid_amount"] / r["total_revenue"] * 100) if r["total_revenue"] > 0 else 0
                avg_invoice = r["total_revenue"] / r["invoice_count"] if r["invoice_count"] > 0 else 0

                # Calculate revenue trend
                revenue_trend = "stable"
                # This would need comparison with previous month for full trend calculation

                revenue_analytics.append(RevenueAnalytics(
                    month=month_str,
                    year=month_year,
                    total_revenue=round(r["total_revenue"], 2),
                    invoice_count=r["invoice_count"],
                    paid_amount=round(r["paid_amount"], 2),
                    pending_amount=round(r["pending_amount"], 2),
                    overdue_amount=round(r["overdue_amount"], 2),
                    collection_rate=round(collection_rate, 2),
                    avg_invoice_value=round(avg_invoice, 2),
                    revenue_trend=TrendDirection(revenue_trend),
                    revenue_change_percentage=0
                ))

            return revenue_analytics

        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return []

    def get_revenue_forecast(
        self,
        months_ahead: int = 3
    ) -> RevenueForecast:
        """Generate revenue forecast using historical data."""
        historical = self.get_revenue_analytics()

        if len(historical) < 3:
            raise InsufficientDataException(
                required_data_points=3,
                available_data_points=len(historical),
                forecast_type="revenue"
            )

        # Use last 6 months for forecasting
        recent_data = historical[:6]

        revenues = [r.total_revenue for r in recent_data]
        avg_revenue = sum(revenues) / len(revenues)

        # Simple moving average forecast
        predicted_revenue = avg_revenue

        # Calculate confidence interval
        variance = sum((r - avg_revenue) ** 2 for r in revenues) / len(revenues)
        std_dev = variance ** 0.5

        confidence_low = max(0, predicted_revenue - 1.96 * std_dev)
        confidence_high = predicted_revenue + 1.96 * std_dev

        # Confidence score based on data consistency
        cv = (std_dev / avg_revenue * 100) if avg_revenue > 0 else 100
        confidence_score = max(0, min(100, 100 - cv))

        # Determine next month
        last_month = recent_data[0].month if recent_data else datetime.utcnow().strftime("%Y-%m")
        next_month = datetime.strptime(last_month, "%Y-%m")
        next_month = next_month.replace(month=(next_month.month % 12) + 1)
        predicted_month = next_month.strftime("%Y-%m")

        return RevenueForecast(
            predicted_month=predicted_month,
            predicted_revenue=round(predicted_revenue, 2),
            confidence_low=round(confidence_low, 2),
            confidence_high=round(confidence_high, 2),
            confidence_score=round(confidence_score, 2),
            factors=["Historical average", f"Based on {len(recent_data)} months of data"]
        )

    def get_revenue_summary(self) -> RevenueSummary:
        """Get comprehensive revenue summary with forecast."""
        current_month = datetime.utcnow().strftime("%Y-%m")

        # Get current and previous month revenue
        current_data = self.get_revenue_analytics(month=int(current_month.split("-")[1]))
        previous_month = datetime.now().replace(month=(datetime.now().month - 1) or 12)
        previous_data = self.get_revenue_analytics(month=previous_month.month)

        current_revenue = current_data[0].total_revenue if current_data else 0
        previous_revenue = previous_data[0].total_revenue if previous_data else 0

        mom_change = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0

        # Get year to date
        current_year = datetime.utcnow().year
        ytd_data = self.get_revenue_analytics(year=current_year)
        ytd_revenue = sum(r.total_revenue for r in ytd_data)

        # Generate forecast
        forecast = self.get_revenue_forecast()

        return RevenueSummary(
            current_month=current_month,
            current_month_revenue=round(current_revenue, 2),
            previous_month_revenue=round(previous_revenue, 2),
            month_over_month_change=round(mom_change, 2),
            year_to_date_revenue=round(ytd_revenue, 2),
            projected_monthly_revenue=round(forecast.predicted_revenue, 2),
            forecast=[forecast]
        )

    # ==================== DATA QUALITY ====================

    def get_data_quality_report(self) -> DataQualityReport:
        """Generate data quality report for all collections."""
        metrics = []
        issues = []
        recommendations = []

        collections = {
            "customers": self.db["customers"] if self.db else None,
            "meter_readings": self.db["meter_readings"] if self.db else None,
            "invoices": self.db["invoices"] if self.db else None,
            "payments": self.db["payments"] if self.db else None
        }

        for name, collection in collections.items():
            if not collection:
                continue

            try:
                # Count documents
                doc_count = collection.count_documents({})

                # Count indexes
                index_count = len(collection.index_information())

                # Check for null values in key fields
                null_checks = {
                    "customers": "name",
                    "meter_readings": "customer_id",
                    "invoices": "customer_id",
                    "payments": "invoice_id"
                }

                key_field = null_checks.get(name)
                if key_field:
                    null_count = collection.count_documents({key_field: {"$in": [None, ""]}})
                    null_percentage = (null_count / doc_count * 100) if doc_count > 0 else 0

                    if null_percentage > 5:
                        status = "warning"
                        issues.append(f"{name}: {null_percentage:.1f}% records have null {key_field}")
                        recommendations.append(f"Clean up null values in {name}.{key_field}")
                    else:
                        status = "good"

                    metrics.append(DataQualityMetric(
                        collection_name=name,
                        metric_name="null_values",
                        value=null_percentage,
                        status=status,
                        threshold=5,
                        description=f"Percentage of records with null {key_field}"
                    ))

                # Document count metric
                metrics.append(DataQualityMetric(
                    collection_name=name,
                    metric_name="document_count",
                    value=doc_count,
                    status="good",
                    threshold=0,
                    description=f"Total number of documents in collection"
                ))

                # Index count metric
                metrics.append(DataQualityMetric(
                    collection_name=name,
                    metric_name="index_count",
                    value=index_count,
                    status="good" if index_count > 0 else "warning",
                    threshold=1,
                    description=f"Number of indexes on collection"
                ))

            except Exception as e:
                logger.error(f"Error checking data quality for {name}: {e}")
                metrics.append(DataQualityMetric(
                    collection_name=name,
                    metric_name="error",
                    value=0,
                    status="critical",
                    threshold=0,
                    description=f"Error collecting metrics: {str(e)}"
                ))

        # Calculate overall score
        good_metrics = sum(1 for m in metrics if m.status == "good")
        total_metrics = len(metrics)
        overall_score = (good_metrics / total_metrics * 100) if total_metrics > 0 else 0

        return DataQualityReport(
            generated_at=datetime.utcnow(),
            overall_score=round(overall_score, 2),
            metrics=metrics,
            issues=issues,
            recommendations=recommendations
        )

    def get_collection_stats(self) -> List[Dict]:
        """Get statistics for all collections."""
        if not self.db:
            return []

        stats = []
        collection_names = ["customers", "meter_readings", "invoices", "payments",
                           "usage_trends", "payment_analytics", "customer_behavior", "staff_metrics"]

        for name in collection_names:
            if name not in self.db.list_collection_names():
                continue

            try:
                coll = self.db[name]
                count = coll.count_documents({})
                indexes = len(coll.index_information())

                # Get collection stats (if available)
                try:
                    coll_stats = self.db.command("collStats", name)
                    size = coll_stats.get("size", 0)
                except Exception:
                    size = 0

                stats.append({
                    "collection_name": name,
                    "document_count": count,
                    "index_count": indexes,
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2)
                })
            except Exception as e:
                logger.error(f"Error getting stats for {name}: {e}")

        return stats

    # ==================== DASHBOARD ANALYTICS ====================

    def get_dashboard_analytics(self) -> DashboardAnalytics:
        """Get comprehensive dashboard analytics."""
        # Get active/inactive counts
        counts = self.get_active_inactive_counts()

        # Get revenue summary
        revenue = self.get_revenue_summary()

        # Get payment methods
        payment_methods = self.get_payment_methods_analysis()

        # Get segment stats
        segments = self.get_segment_stats()

        # Get data quality
        quality = self.get_data_quality_report()

        return DashboardAnalytics(
            total_customers=counts.get("total", 0),
            active_customers=counts.get("active", 0),
            inactive_customers=counts.get("inactive", 0),
            total_revenue=revenue.year_to_date_revenue,
            revenue_this_month=revenue.current_month_revenue,
            revenue_last_month=revenue.previous_month_revenue,
            avg_payment_days=0,  # Would need to aggregate
            collection_rate=0,  # Would need to calculate from invoices
            top_payment_methods=[],
            customer_segments=segments,
            data_quality_score=quality.overall_score
        )

    # ==================== CACHE MANAGEMENT ====================

    def clear_cache(self, prefix: str = None) -> int:
        """Clear cached data."""
        cache = self._cache

        if prefix:
            return cache.invalidate_prefix(prefix)
        else:
            count = len(cache._cache)
            cache.clear()
            return count

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self._cache.get_stats()


def get_analytics_service():
    """Factory function to get analytics service instance."""
    from app.mongodb import get_db
    db = get_db()
    if db is not None:
        return AnalyticsService(db)
    return None


# ==================== ASYNC SUPPORT ====================

async def get_analytics_async():
    """Factory function to get analytics service in async context."""
    from app.mongodb import get_db
    db = await get_db_async()
    if db is not None:
        return AnalyticsService(db)
    return None


async def get_db_async():
    """Get MongoDB database instance asynchronously."""
    from pymongo import MongoClient
    import os
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    try:
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.admin.command('ping')
        )
        return client["water_billing"]
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB asynchronously: {e}")
        return None

