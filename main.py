import requests
import urllib3
import base64

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# url = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"
url = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"

PROXY = "http://223.185.53.133:8888"
proxies = {"http": PROXY, "https": PROXY}

params = {"AadharNo": "Njk3OTgzNzUyMjk3"}  # 225866565460


# Send get
response = requests.get(url, params=params,  verify=False)


data = response.json()
# Decode Base64 fields
for item in data:
    for key in ["Mobileno", "NewMemberID", "NewFamilyID"]:
        if item.get(key):
            try:
                decoded = base64.b64decode(item[key]).decode("utf-8")
                item[key] = decoded
            except Exception as e:
                print("Error:", e)
                pass

print("Decoded Data:", data)            

print("Raw Response Body:\n", response.text)

print("Status Code:", response.status_code)
print("Response Headers:", dict(response.headers))
print("Response Body:", response.text)

