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
import requests, urllib3, base64
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIG ===
PROXY_HOST = "103.167.33.6"
HTTP_PORT  = "49155"
SOCKS_PORT = "49156"
PROXY_USER = "shivnathjan2001"
PROXY_PASS = "gA5vkef6fE"

URL = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"   # test URL first
PARAMS = {"AadharNo": "Njk3OTgzNzUyFjk3"}
# ==============

# Build both proxy URLs
http_proxy  = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{HTTP_PORT}"
socks_proxy = f"socks5h://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{SOCKS_PORT}"

proxies_http  = {"http": http_proxy,  "https": http_proxy}
proxies_socks = {"http": socks_proxy, "https": socks_proxy}

def test_proxy(name, proxies):
    print(f"\nTesting {name} proxy:")
    try:
        r = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=15, verify=False)
        print("Status:", r.status_code, "| Body:", r.text.strip())
    except Exception as e:
        print("Error:", e)

print("=== Checking proxies ===")
test_proxy("HTTP",  proxies_http)
test_proxy("SOCKS", proxies_socks)

# Example: use one proxy (choose HTTP or SOCKS) for your real request
chosen = proxies_http  # or proxies_socks

print("\nNow requesting target URL through chosen proxy...")
try:
    response = requests.get(URL, params=PARAMS, proxies=chosen, verify=False, timeout=25)
    print("Status:", response.status_code)
    try:
        data = response.json()
        for item in data:
            for k in ["Mobileno", "NewMemberID", "NewFamilyID"]:
                if item.get(k):
                    item[k] = base64.b64decode(item[k]).decode("utf-8")
        print("Decoded data:", data)
    except Exception:
        print("Raw body:", response.text[:1000])
except Exception as e:
    print("Request failed:", e)
