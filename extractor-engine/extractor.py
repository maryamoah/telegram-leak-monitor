import os
import re
import zipfile
import py7zr
import rarfile
from PyPDF2 import PdfReader

# =========================================================
# CONFIG
# =========================================================

STREAM_CHUNK_SIZE = 4_000_000  # 4 MB
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN")

# =========================================================
# REGEX DEFINITIONS (bytes-safe extractors)
# =========================================================

EMAIL_RE = re.compile(
    rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE
)

CRED_RE = re.compile(
    rb"(?P<user>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb"[:|,;]"
    rb"(?P<pw>[^\s]{1,100})",
    re.IGNORECASE
)

URL_CRED_RE = re.compile(
    rb"https?://[^\s:]+:"
    rb"(?P<user>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb":"
    rb"(?P<pw>[^\s]{1,200})",
    re.IGNORECASE
)

GENERIC_CRED_RE = re.compile(
    rb"[^\s:]{3,}:"
    rb"(?P<user>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb":"
    rb"(?P<pw>[^\s]{1,200})",
    re.IGNORECASE
)

# =========================================================
# VALIDATION HELPERS
# =========================================================

EMAIL_VALIDATE_RE = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}"
    r"@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

def normalize_email(email: str) -> str:
    return email.lstrip("+-._")

def is_valid_email(email: str) -> bool:
    if len(email) > 254:
        return False
    return bool(EMAIL_VALIDATE_RE.match(email))

def is_msisdn_email(email: str) -> bool:
    local = email.split("@", 1)[0]
    return local.startswith("+") and local[1:].isdigit()

def domain_allowed(email: str) -> bool:
    if not TARGET_DOMAIN:
        return True
    return email.endswith("@" + TARGET_DOMAIN.lower())

# =========================================================
# FILE READERS
# =========================================================

def read_raw(path: str, limit: int = 10_000_000) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(limit)
    except Exception:
        return b""

def read_raw_stream(path: str):
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(STREAM_CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
    except Exception:
        return

def read_pdf(path: str) -> bytes:
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.encode(errors="ignore")
    except Exception:
        return b""

def read_zip(path: str) -> bytes:
    buf = b""
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                try:
                    buf += z.read(name)
                except Exception:
                    pass
    except Exception:
        pass
    return buf

def read_rar(path: str) -> bytes:
    buf = b""
    try:
        with rarfile.RarFile(path) as rf:
            for entry in rf.infolist():
                try:
                    buf += rf.read(entry)
                except Exception:
                    pass
    except Exception:
        pass
    return buf

def read_7z(path: str) -> bytes:
    buf = b""
    try:
        with py7zr.SevenZipFile(path, "r") as z:
            files = z.readall()
            for _, f in files.items():
                try:
                    buf += f.read()
                except Exception:
                    pass
    except Exception:
        pass
    return buf

# =========================================================
# CORE EXTRACTION
# =========================================================

def extract_all(raw: bytes) -> list:
    if not isinstance(raw, (bytes, bytearray)):
        return []

    found = []

    for m in CRED_RE.finditer(raw):
        found.append((
            m.group("user").decode(errors="ignore").lower(),
            m.group("pw").decode(errors="ignore")
        ))

    for m in URL_CRED_RE.finditer(raw):
        found.append((
            m.group("user").decode(errors="ignore").lower(),
            m.group("pw").decode(errors="ignore")
        ))

    for m in GENERIC_CRED_RE.finditer(raw):
        found.append((
            m.group("user").decode(errors="ignore").lower(),
            m.group("pw").decode(errors="ignore")
        ))

    return found

# =========================================================
# PUBLIC ENTRYPOINT
# =========================================================

def extract_emails(path: str) -> dict:
    if not path or not os.path.exists(path):
        return {"emails": [], "creds": []}

    lower = path.lower()
    creds = []

    if lower.endswith(".pdf"):
        creds = extract_all(read_pdf(path))

    elif lower.endswith(".zip"):
        creds = extract_all(read_zip(path))

    elif lower.endswith(".rar"):
        creds = extract_all(read_rar(path))

    elif lower.endswith(".7z"):
        creds = extract_all(read_7z(path))

    else:
        chunk_count = 0
        for chunk in read_raw_stream(path):
            chunk_count += 1
            chunk_creds = extract_all(chunk)
            if chunk_creds:
                creds.extend(chunk_creds)

            if chunk_count % 5 == 0:
                print(
                    f"[extractor] chunks={chunk_count} extracted={len(creds)}",
                    flush=True
                )

    dedup = {}

    for email, password in creds:
        email = normalize_email(email)

        if not is_valid_email(email):
            continue

        if is_msisdn_email(email):
            continue

        if not domain_allowed(email):
            continue

        dedup[(email, password)] = {
            "email": email,
            "password": password
        }

    final_creds = list(dedup.values())
    final_emails = sorted({c["email"] for c in final_creds})

    return {
        "emails": final_emails,
        "creds": final_creds
    }
