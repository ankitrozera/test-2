# import requests
# import urllib3
# import base64

# # Disable SSL warnings for testing
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# # url = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"
# url = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"

# # PROXY = "http://223.185.53.133:8888"
# # proxies = {"http": PROXY, "https": PROXY}

# proxies = [
#     "http://shivnathjan2001:gA5vkef6fE@223.185.53.133:49155",
#     "socks5h://shivnathjan2001:gA5vkef6fE@223.185.53.133:49156",
# ]

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



#!/usr/bin/env python3
"""
debug_proxy_test.py
DEBUG-friendly single-file proxy + target tester.
Replace the placeholders below with your real local credentials for testing only.
After testing, delete this file or remove credentials.

Requires: pip install requests[socks]
Run: python debug_proxy_test.py
"""

import time
import requests
import urllib3
import base64
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------- EDIT THESE LOCALLY (DO NOT SHARE) -----------------
DEBUG = True

# Target endpoint (change only on local machine)
TARGET_URL = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"

# Param for the request (example)
AADHAR_PARAM = "Njk3OTgzNzUyMjk3"

# Proxy credentials - CHANGE THESE LOCALLY
# Format examples:
#   http:  "http://user:pass@host:49155"
#   socks: "socks5h://user:pass@host:49156"
PROXY_HTTP = "http://shivnathjan2001:REPLACE_PASS@"103.167.33.6":49155"
PROXY_SOCKS = "socks5h://shivnathjan2001:REPLACE_PASS@"103.167.33.6":49156"

# Timeouts / behavior
REQUEST_TIMEOUT = 20    # seconds
RETRY_ON_FAIL = 1       # number of retries per proxy
DELAY_BETWEEN = 0.6     # polite delay between tests
# ---------------------------------------------------------------------

def mask(s):
    try:
        p = urlparse(s)
        if p.username:
            return f"{p.scheme}://{p.username}:****@{p.hostname}:{p.port}"
    except Exception:
        pass
    return s

def try_request(proxy_url):
    """
    Try target request via given proxy_url.
    Returns tuple (ok:bool, info:str)
    """
    proxies = {"http": proxy_url, "https": proxy_url}
    print("\n---")
    print("Using proxy:", mask(proxy_url))
    # 1) quick httpbin check to show outgoing IP
    try:
        t0 = time.time()
        r = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=REQUEST_TIMEOUT, verify=False)
        t = round(time.time() - t0, 3)
        print(f"[httpbin] {r.status_code} time={t}s body={r.text.strip()}")
    except Exception as e:
        print("[httpbin] ERROR:", repr(e))
        return False, f"httpbin-fail: {e!r}"
    # 2) target request
    try:
        params = {"AadharNo": AADHAR_PARAM} if AADHAR_PARAM else {}
        t0 = time.time()
        r2 = requests.get(TARGET_URL, params=params, proxies=proxies, timeout=REQUEST_TIMEOUT, verify=False)
        total = round(time.time() - t0, 3)
        print(f"[target] status={r2.status_code} time={total}s")
        # Safe attempt to parse JSON
        ct = r2.headers.get("Content-Type", "")
        if "application/json" in ct.lower() or r2.text.strip().startswith(("{","[")):
            try:
                data = r2.json()
                print("Response JSON type:", type(data).__name__)
                # Show small sample safely
                if isinstance(data, list) and data:
                    sample = data[0]
                elif isinstance(data, dict):
                    sample = {k: data.get(k) for k in ("Mobileno","NewMemberID","NewFamilyID") if k in data}
                else:
                    sample = str(data)[:300]
                print("Sample:", sample)
            except Exception as e:
                print("JSON parse failed:", e)
                print("Body snippet:", (r2.text or "")[:600].replace("\n"," "))
        else:
            print("Body snippet:", (r2.text or "")[:800].replace("\n"," "))
        # Return success if 200
        return (r2.status_code == 200), f"status={r2.status_code}"
    except Exception as e:
        print("[target] ERROR:", repr(e))
        return False, f"target-fail: {e!r}"

def main():
    proxies = [PROXY_HTTP, PROXY_SOCKS]
    for p in proxies:
        p = p.strip()
        if not p:
            continue
        # try with a small retry loop
        for attempt in range(1, RETRY_ON_FAIL + 2):
            ok, info = try_request(p)
            if ok:
                print("=> SUCCESS via", mask(p))
                break
            else:
                print(f"=> Attempt {attempt} failed: {info}")
                if attempt <= RETRY_ON_FAIL:
                    print("   Retrying after short pause...")
                    time.sleep(1.0)
        time.sleep(DELAY_BETWEEN)
    print("\nAll done. Remember to delete this file or remove credentials when finished.")

if __name__ == "__main__":
    if not (PROXY_HTTP or PROXY_SOCKS):
        print("No proxies configured. Edit file and add PROXY_HTTP / PROXY_SOCKS locally.")
    else:
        if DEBUG:
            print("DEBUG MODE: verbose output enabled.")
        main()
