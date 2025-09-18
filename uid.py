# uid.py

# --- Verhoeff algorithm tables (standard) ---
_d = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,6,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
_p = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8],
]
_inv = [0,4,3,2,1,5,6,7,8,9]

def _verhoeff_check_digit(num_str_wo_check: str) -> str:
    """Return Verhoeff checksum digit for a numeric string (without the check digit)."""
    c = 0
    # process right-to-left
    for i, ch in enumerate(reversed(num_str_wo_check)):
        c = _d[c][_p[(i + 1) % 8][ord(ch) - 48]]
    return str(_inv[c])

def validate_uid(uid12: str) -> bool:
    """Validate a 12-digit UID using Verhoeff checksum."""
    if not (isinstance(uid12, str) and uid12.isdigit() and len(uid12) == 12):
        return False
    c = 0
    for i, ch in enumerate(reversed(uid12)):
        c = _d[c][_p[i % 8][ord(ch) - 48]]
    return c == 0

def uid(serial: int, first_digit: int = 2) -> str:
    """
    Generate a 12-digit UID.
    - serial: non-negative integer (your running counter)
    - first_digit: 2..9 (keeps first digit Aadhaar-like; change if you want)
    Structure: [first_digit][serial as 10-digit zero-padded][verhoeff check digit]
               = 1 + 10 + 1 = 12
    """
    if serial < 0:
        raise ValueError("serial must be non-negative")
    if serial < 0 or serial >= 10**10:
        raise ValueError("serial must be between 0 and 9999999999")
    if first_digit not in range(2, 10):
        raise ValueError("first_digit must be between 2 and 9")

    body11 = str(first_digit) + f"{serial:010d}"
    check = _verhoeff_check_digit(body11)
    return body11 + check

# ---- demo ----
if __name__ == "__main__":
    for s in range(5):
        u = uid(s)              # generate from serial 0..4
        print(u, validate_uid(u))
