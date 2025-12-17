"""
Script to fix customer IDs that are None.
Assigns proper sequential IDs to customers that don't have one.
"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = MongoClient(MONGODB_URL)

# Provider database
provider_db_name = "wb_celebration-water_c0b8458b"
db = client[provider_db_name]

print(f"Connected to MongoDB database: {provider_db_name}")

# Get all active customers
customers = list(db["customers"].find({"is_active": True}))
print(f"Total active customers: {len(customers)}")

# Find customers without IDs
customers_needing_ids = [c for c in customers if c.get("id") is None]
print(f"Customers needing IDs: {len(customers_needing_ids)}")

if customers_needing_ids:
    # Get the current max ID
    customers_with_ids = [c for c in customers if c.get("id") is not None]
    if customers_with_ids:
        max_id = max(c.get("id", 0) for c in customers_with_ids)
    else:
        max_id = 0
    
    print(f"Current max ID: {max_id}")
    
    # Assign IDs starting from max_id + 1
    for i, c in enumerate(customers_needing_ids):
        new_id = max_id + i + 1
        db["customers"].update_one(
            {"_id": c["_id"]},
            {"$set": {"id": new_id}}
        )
        print(f"  Assigned ID {new_id} to: {c.get('name')}")

# Update the counter
max_id_final = db["customers"].find_one(sort=[("id", -1)])
if max_id_final and max_id_final.get("id"):
    db["counters"].update_one(
        {"_id": "customers"},
        {"$set": {"seq": max_id_final.get("id", 1)}},
        upsert=True
    )
    print(f"\nCounter updated to: {max_id_final.get('id')}")

# Verify
customers_after = list(db["customers"].find({"is_active": True}))
print(f"\nVerification - Total customers: {len(customers_after)}")
customers_with_ids_after = [c for c in customers_after if c.get("id") is not None]
print(f"Customers with IDs: {len(customers_with_ids_after)}")

client.close()
print("\nDone!")

