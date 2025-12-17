#!/usr/bin/env python
"""Database status verification script"""
import sqlite3
import os

def check_database():
    db_path = 'app/water_billing.db'
    print(f'Database exists: {os.path.exists(db_path)}')
    print(f'Database size: {os.path.getsize(db_path) / 1024:.2f} KB' if os.path.exists(db_path) else 'N/A')

    if not os.path.exists(db_path):
        print('\n❌ Database not found - initializing...')
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f'\n📊 Tables in database: {len(tables)}')
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f'   - {table_name}: {count} records')
    
    # Show sample data from customers table
    print('\n👥 Sample customer data (first 5):')
    cursor.execute('SELECT id, name, phone, location FROM customers LIMIT 5')
    customers = cursor.fetchall()
    if customers:
        for c in customers:
            print(f'   ID: {c[0]}, Name: {c[1]}, Phone: {c[2]}, Location: {c[3]}')
    else:
        print('   No customers found')
    
    # Show rate configuration
    print('\n💰 Rate configuration:')
    cursor.execute('SELECT * FROM rate_config LIMIT 1')
    rate = cursor.fetchone()
    if rate:
        print(f'   ID: {rate[0]}, Mode: {rate[1]}, Value: {rate[2]}')
    else:
        print('   No rate configuration found')
    
    # Show recent invoices
    print('\n🧾 Recent invoices (last 5):')
    cursor.execute('SELECT id, customer_id, amount, status, due_date FROM invoices ORDER BY id DESC LIMIT 5')
    invoices = cursor.fetchall()
    if invoices:
        for inv in invoices:
            print(f'   ID: {inv[0]}, Customer: {inv[1]}, Amount: {inv[2]}, Status: {inv[3]}, Due: {inv[4]}')
    else:
        print('   No invoices found')
    
    # Show recent meter readings
    print('\n📈 Recent meter readings (last 5):')
    cursor.execute('SELECT id, customer_id, reading_value, recorded_at FROM meter_readings ORDER BY recorded_at DESC LIMIT 5')
    readings = cursor.fetchall()
    if readings:
        for r in readings:
            print(f'   ID: {r[0]}, Customer: {r[1]}, Reading: {r[2]}, Date: {r[3]}')
    else:
        print('   No meter readings found')
    
    # Show payments
    print('\n💳 Recent payments (last 5):')
    cursor.execute('SELECT id, invoice_id, amount, payment_method, status FROM payments ORDER BY payment_date DESC LIMIT 5')
    payments = cursor.fetchall()
    if payments:
        for p in payments:
            print(f'   ID: {p[0]}, Invoice: {p[1]}, Amount: {p[2]}, Method: {p[3]}, Status: {p[4]}')
    else:
        print('   No payments found')
    
    conn.close()
    return True

if __name__ == '__main__':
    print('=' * 60)
    print('WATER BILLING SYSTEM - DATABASE STATUS CHECK')
    print('=' * 60)
    check_database()
    print('\n' + '=' * 60)

