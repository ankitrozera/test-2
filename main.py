# import requests
# import urllib3
# import base64

# # Disable SSL warnings for testing
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# # url = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"
# url = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"

# PROXY = "http://223.185.53.133:8888"
# proxies = {"http": PROXY, "https": PROXY}

# params = {"AadharNo": "Njk3OTgzNzUyMjk3"}  # 225866565460


# # Send get
# response = requests.get(url, params=params, proxies=proxies,  verify=False)


# data = response.json()
# # Decode Base64 fields
# for item in data:
#     for key in ["Mobileno", "NewMemberID", "NewFamilyID"]:
#         if item.get(key):
#             try:
#                 decoded = base64.b64decode(item[key]).decode("utf-8")
#                 item[key] = decoded
#             except Exception as e:
#                 print("Error:", e)
#                 pass

# print("Decoded Data:", data)            

# print("Raw Response Body:\n", response.text)

# print("Status Code:", response.status_code)
# print("Response Headers:", dict(response.headers))
# print("Response Body:", response.text)



# proxy_test_and_fetch.py
# Simple: test proxy (httpbin) then call target URL and base64-decode fields.
import os
import requests
import urllib3
import base64
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----- CONFIG (replace or use env vars) -----
PROXY_HOST = os.getenv("PROXY_HOST") or "103.167.33.6"   # <-- replace with provider host/IP
PROXY_USER = os.getenv("PROXY_USER") or "shivnathjan2001"  # <-- from email
PROXY_PASS = os.getenv("PROXY_PASS") or "gA5vkef6fE"       # <-- from email
HTTP_PORT = os.getenv("PROXY_HTTP_PORT") or "49155"        # email said HTTP:49155
SOCKS_PORT = os.getenv("PROXY_SOCKS_PORT") or "49156"      # email said SOCKS:49156

# Example: choose which transport to use: "http" or "socks5"
# For http proxy use "http". For socks use "socks5h" (requires requests[socks]).
PROXY_SCHEME = os.getenv("PROXY_SCHEME") or "http"

# Target request settings
TARGET_URL = os.getenv("TARGET_URL") or "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"  # <-- put real URL
PARAMS = {"AadharNo": "Njk3OTgzNzUyFjk3"}  # as in your code

# ---------------------------------------------

def make_proxy_url(scheme, user, passwd, host, port):
    """Build proxy URL with auth: scheme://user:pass@host:port"""
    if user and passwd:
        return f"{scheme}://{user}:{passwd}@{host}:{port}"
    else:
        return f"{scheme}://{host}:{port}"

def proxies_for_scheme(proxy_url):
    """requests expects dict for http and https"""
    return {"http": proxy_url, "https": proxy_url}

def mask(proxy_url):
    """Mask password for safe logging"""
    try:
        p = urlparse(proxy_url)
        if p.username:
            return f"{p.scheme}://{p.username}:****@{p.hostname}:{p.port}"
        return proxy_url
    except Exception:
        return proxy_url

def safe_base64_decode(s):
    if not s:
        return s
    try:
        return base64.b64decode(s).decode("utf-8", errors="replace")
    except Exception:
        return s

def test_outgoing_ip(proxy_url):
    print("Testing proxy (masked):", mask(proxy_url))
    try:
        r = requests.get("https://httpbin.org/ip", proxies=proxies_for_scheme(proxy_url), timeout=15, verify=False)
        print("httpbin status:", r.status_code)
        print("httpbin body:", r.text.strip())
        return True, r
    except Exception as e:
        print("Proxy test failed:", repr(e))
        return False, None

def fetch_target_and_decode(proxy_url):
    print("\nFetching target via proxy (masked):", mask(proxy_url))
    try:
        r = requests.get(TARGET_URL, params=PARAMS, proxies=proxies_for_scheme(proxy_url), timeout=25, verify=False)
    except Exception as e:
        print("Request failed:", repr(e))
        return

    print("Status:", r.status_code)
    # Try parse JSON
    try:
        data = r.json()
    except Exception:
        print("Response not JSON — raw body (first 2000 chars):")
        print(r.text[:2000])
        return

    # decode fields if present
    def decode_item(it):
        if not isinstance(it, dict):
            return it
        for key in ["Mobileno", "NewMemberID", "NewFamilyID"]:
            if key in it and it[key]:
                it[key] = safe_base64_decode(it[key])
        return it

    if isinstance(data, list):
        decoded = [decode_item(x) for x in data]
    elif isinstance(data, dict):
        decoded = decode_item(data)
    else:
        decoded = data

    print("\nDecoded Data:")
    print(decoded)
    print("\nRaw response body (first 4000 chars):")
    print(r.text[:4000])

if __name__ == "__main__":
    # Build proxy URL using chosen scheme and HTTP port; if you want to test SOCKS, change PROXY_SCHEME and port
    proxy_url = make_proxy_url(PROXY_SCHEME, PROXY_USER, PROXY_PASS, PROXY_HOST, HTTP_PORT if PROXY_SCHEME.startswith("http") else SOCKS_PORT)
    ok, test_resp = test_outgoing_ip(proxy_url)
    if not ok:
        print("Proxy test failed. If you only have ports but no host, ask provider for proxy host. Exiting.")
    else:
        # optionally print outgoing IP reported
        try:
            print("Outgoing IP info:", test_resp.json())
        except Exception:
            pass
        fetch_target_and_decode(proxy_url)

