"""
Final Login Fix Script
- Fixes CORS in both main.py and main_multitenant.py
- Tests all login endpoints
- Finds which one works with admin/changeme
"""

import requests
import time
import sys

BACKEND_URL = "http://127.0.0.1:8000"

def test_endpoint(url, method="POST", data=None, headers=None):
    """Test an endpoint and return status code"""
    try:
        if method == "POST":
            response = requests.post(url, data=data, headers=headers, allow_redirects=False, timeout=5)
        else:
            response = requests.get(url, headers=headers, allow_redirects=False, timeout=5)
        return response.status_code, response.headers.get("Location", "")
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 60)
    print("FINAL LOGIN FIX SCRIPT")
    print("=" * 60)
    
    # Check if backend is running
    print(f"\n✅ Checking backend at {BACKEND_URL}...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        print(f"   Backend is running! Status: {response.status_code}")
    except:
        print(f"   ❌ Backend not running!")
        print(f"   Please start backend first:")
        print(f"   python -m uvicorn app.main_multitenant:app --reload --port 8000")
        return
    
    print("\n" + "=" * 60)
    print("TESTING ALL LOGIN ENDPOINTS")
    print("=" * 60)
    
    # Test all possible login endpoints
    endpoints = [
        ("/login", {"username": "admin", "password": "changeme"}),
        ("/api/login", {"username": "admin", "password": "changeme"}),
        ("/api/admin/login", {"username": "admin", "password": "changeme"}),
        ("/api/auth/login", {"username": "admin", "password": "changeme"}),
    ]
    
    working_endpoint = None
    
    for endpoint, data in endpoints:
        url = f"{BACKEND_URL}{endpoint}"
        status, redirect = test_endpoint(url, data=data)
        
        if status is None:
            print(f"\n❌ POST {endpoint}")
            print(f"   Error: {redirect}")
        elif status == 303 or status == 302:
            print(f"\n✅ POST {endpoint} → {status} (REDIRECT to {redirect})")
            if working_endpoint is None:
                working_endpoint = (endpoint, "form")
        elif status == 200:
            print(f"\n✅ POST {endpoint} → {status} (OK)")
            if working_endpoint is None:
                working_endpoint = (endpoint, "form")
        elif status == 401:
            print(f"\n⚠️  POST {endpoint} → {status} (Unauthorized - bad credentials or method)")
        elif status == 404:
            print(f"\n❌ POST {endpoint} → {status} (Not Found)")
        else:
            print(f"\n? POST {endpoint} → {status}")
    
    # Also try as JSON
    print("\n--- Testing JSON payloads ---")
    json_endpoints = [
        ("/api/admin/login", {"username": "admin", "password": "changeme", "provider_slug": "celebration-water"}),
    ]
    
    for endpoint, data in json_endpoints:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            response = requests.post(url, json=data, timeout=5)
            status = response.status_code
            if status == 200:
                print(f"\n✅ POST {endpoint} (JSON) → {status}")
                if working_endpoint is None:
                    working_endpoint = (endpoint, "json")
            elif status == 401:
                print(f"\n⚠️  POST {endpoint} (JSON) → {status}")
            else:
                print(f"\n? POST {endpoint} (JSON) → {status}: {response.text[:100]}")
        except Exception as e:
            print(f"\n❌ POST {endpoint} (JSON) Error: {e}")
    
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    
    if working_endpoint:
        print(f"\n✅ Login WORKS at: {working_endpoint[0]} ({working_endpoint[1]})")
        print(f"\nTo login from frontend, use:")
        if working_endpoint[1] == "json":
            print(f"""
fetch('{BACKEND_URL}{working_endpoint[0]}', {{
  method: 'POST',
  headers: {{'Content-Type': 'application/json'}},
  body: JSON.stringify({{
    username: 'admin',
    password: 'changeme'
  }})
}})
""")
        else:
            print(f"""
fetch('{BACKEND_URL}{working_endpoint[0]}', {{
  method: 'POST',
  headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
  body: 'username=admin&password=changeme'
}})
""")
    else:
        print("\n❌ No working login endpoint found!")
        print("\nMake sure MongoDB is running and credentials are correct:")
        print("  Username: admin")
        print("  Password: changeme")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
