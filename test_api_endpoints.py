#!/usr/bin/env python
"""API endpoint verification script"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, data=None, expected_status=200, description=""):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n🧪 Testing: {description}")
    print(f"   URL: {method.upper()} {url}")
    
    try:
        if method.lower() == "get":
            response = requests.get(url, timeout=5)
        elif method.lower() == "post":
            response = requests.post(url, data=data, timeout=5)
        else:
            print(f"   ❌ Unknown method: {method}")
            return False
        
        status_ok = response.status_code == expected_status
        print(f"   Status: {response.status_code} {'✅' if status_ok else '❌'}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=4, default=str)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
        
        return status_ok
        
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection failed - server may not be running")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_html_endpoint(endpoint, description=""):
    """Test HTML/template endpoints"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n🧪 Testing: {description}")
    print(f"   URL: GET {url}")
    
    try:
        response = requests.get(url, timeout=5)
        status_ok = response.status_code == 200
        print(f"   Status: {response.status_code} {'✅' if status_ok else '❌'}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   Content-Length: {len(response.text)} chars")
        return status_ok
        
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection failed - server may not be running")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    print("=" * 70)
    print("WATER BILLING SYSTEM - API ENDPOINT VERIFICATION")
    print("=" * 70)
    print("\n⚠️  Make sure the backend server is running: python -m uvicorn app.main:app --reload")
    print("\nStarting tests in 3 seconds...")
    time.sleep(3)
    
    results = []
    
    # Test HTML/template endpoints (these should work without auth)
    print("\n" + "=" * 70)
    print("HTML/TEMPLATE ENDPOINTS (No Auth Required)")
    print("=" * 70)
    
    results.append(test_html_endpoint("/", "Home page"))
    results.append(test_html_endpoint("/login", "Admin login page"))
    results.append(test_html_endpoint("/customers", "Customers page"))
    results.append(test_html_endpoint("/readings", "Meter readings page"))
    results.append(test_html_endpoint("/invoices", "Invoices page"))
    results.append(test_html_endpoint("/customer/login", "Customer login page"))
    results.append(test_html_endpoint("/customer/portal", "Customer portal page"))
    
    # Test login
    print("\n" + "=" * 70)
    print("AUTHENTICATION ENDPOINTS")
    print("=" * 70)
    
    results.append(test_endpoint("post", "/login", 
                                data={"username": "admin", "password": "changeme"},
                                expected_status=303,
                                description="Admin login (valid credentials)"))
    
    results.append(test_endpoint("post", "/login", 
                                data={"username": "wrong", "password": "wrong"},
                                expected_status=403,
                                description="Admin login (invalid credentials)"))
    
    print("\n" + "=" * 70)
    print("API ENDPOINTS (Require Auth)")
    print("=" * 70)
    
    # Test admin login and get session
    session = requests.Session()
    login_response = session.post(f"{BASE_URL}/login", 
                                  data={"username": "admin", "password": "changeme"},
                                  allow_redirects=False)
    
    if login_response.status_code == 303:
        print("\n✅ Admin login successful - testing authenticated endpoints...")
        
        # Dashboard stats
        results.append(test_endpoint("get", "/api/admin/dashboard", 
                                    description="Admin dashboard stats"))
        
        # Customers
        results.append(test_endpoint("get", "/api/admin/customers", 
                                    description="List all customers"))
        
        # Rate config
        results.append(test_endpoint("get", "/api/admin/rate", 
                                    description="Get rate configuration"))
        
    else:
        print("\n❌ Admin login failed - skipping authenticated endpoint tests")
        print(f"   Login response status: {login_response.status_code}")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed - check server status and configuration")
    
    return passed == total

if __name__ == '__main__':
    main()

