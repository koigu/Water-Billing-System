"""
Script to remove duplicate customers from MongoDB.
Keeps the customer with the lowest ID and marks others as duplicates.
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

# Get all customers
customers = list(db["customers"].find())
print(f"Total customers found: {len(customers)}")

# Group by name + phone + location (composite key for duplicates)
from collections import defaultdict
customer_groups = defaultdict(list)

for c in customers:
    # Create composite key
    key = (
        c.get("name", "").strip().lower(),
        c.get("phone", "").strip().lower() if c.get("phone") else "",
        c.get("location", "").strip().lower() if c.get("location") else ""
    )
    customer_groups[key].append(c)

# Find and remove duplicates
duplicates_found = 0
duplicates_removed = 0

for key, group in customer_groups.items():
    if len(group) > 1:
        # Sort by ID to keep the one with lowest ID
        group.sort(key=lambda x: x.get("id", 0))
        
        # Keep first (lowest ID), mark others as duplicates
        keep = group[0]
        to_remove = group[1:]
        
        print(f"\nDuplicate group: {key[0]}")
        print(f"  Keeping: ID={keep.get('id')}, created={keep.get('created_at')}")
        
        for dup in to_remove:
            dup_id = dup.get("id")
            # Soft delete - mark as inactive
            db["customers"].update_one(
                {"_id": dup["_id"]},
                {"$set": {"is_active": False, "is_duplicate": True, "duplicate_of": keep.get("id")}}
            )
            print(f"  Removed duplicate: ID={dup_id}")
            duplicates_removed += 1
        
        duplicates_found += len(group) - 1

print(f"\n{'='*50}")
print(f"Summary:")
print(f"  Duplicate groups: {duplicates_found}")
print(f"  Duplicates removed: {duplicates_removed}")
print(f"  Unique customers remaining: {len(customers) - duplicates_removed}")

# Also rebuild the counter to match the actual max ID
max_id = db["customers"].find_one(sort=[("id", -1)])
if max_id:
    current_counter = db["counters"].find_one({"_id": "customers"})
    if current_counter:
        db["counters"].update_one(
            {"_id": "customers"},
            {"$set": {"seq": max_id.get("id", 1)}}
        )
        print(f"\nCounter updated to: {max_id.get('id', 1)}")

client.close()
print("\nDone!")

