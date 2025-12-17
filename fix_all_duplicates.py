"""
Script to properly fix duplicates - keeps one customer per account_number.
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

# First, restore ALL customers
result = db["customers"].update_many(
    {},
    {"$set": {"is_active": True, "is_duplicate": False, "duplicate_of": None}}
)
print(f"Restored {result.modified_count} customers")

# Get all customers
all_customers = list(db["customers"].find())
print(f"Total customers: {len(all_customers)}")

# Group by account_number
from collections import defaultdict
account_groups = defaultdict(list)

for c in all_customers:
    acct = c.get("account_number")
    if acct:
        account_groups[acct].append(c)

# Fix true duplicates - keep first one, mark others as inactive
duplicates_removed = 0
for acct, group in account_groups.items():
    if len(group) > 1:
        print(f"\nFixing duplicates for account: {acct}")
        # Sort by created_at (oldest first)
        group.sort(key=lambda x: str(x.get("created_at", "")))
        
        # Keep first, mark rest as inactive
        keep = group[0]
        print(f"  Keeping: {keep.get('name')} (id={keep.get('id')}, created={keep.get('created_at')})")
        
        for dup in group[1:]:
            db["customers"].update_one(
                {"_id": dup["_id"]},
                {"$set": {"is_active": False, "is_duplicate": True, "duplicate_of": keep.get("account_number")}}
            )
            print(f"  Removed: {dup.get('name')} (id={dup.get('id')})")
            duplicates_removed += 1

print(f"\n{'='*50}")
print(f"Duplicates removed: {duplicates_removed}")

# Count active customers now
active_count = db["customers"].count_documents({"is_active": True})
print(f"Active customers: {active_count}")

client.close()
print("\nDone!")

