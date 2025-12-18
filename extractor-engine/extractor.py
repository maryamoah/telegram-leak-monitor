import os
import re
import zipfile
import py7zr
import rarfile
from PyPDF2 import PdfReader

# =========================================================
# CONFIG (PUBLIC SAFE)
# =========================================================

TARGET_DOMAIN = os.getenv("TARGET_DOMAIN", "").strip().lower()

if TARGET_DOMAIN:
    TARGET_DOMAIN_BYTES = f"@{TARGET_DOMAIN}".encode()
else:
    TARGET_DOMAIN_BYTES = None

STREAM_CHUNK_SIZE = 4_000_000  # 4 MB

# =========================================================
# REGEX DEFINITIONS (bytes-safe)
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

# =========================================================
# FILE READERS
# =========================================================

def read_raw(path: str, limit: int = 10_000_000) -> bytes:
    """
    Legacy compatibility function.
    Kept so extractor-engine/app.py imports do not break.
    NOT used for large text processing.
    """
    try:
        with open(path, "rb") as f:
            return f.read(limit)
    except Exception:
        return b""


def read_raw_stream(path: str):
    """Stream large text files safely"""
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
    """Extract (email, password) tuples from raw bytes"""
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

    return found

# =========================================================
# PUBLIC ENTRYPOINT
# =========================================================

def extract_emails(path: str) -> dict:
    """
    Domain-gated, streaming-safe extractor.
    Public GitHub safe (no hard-coded org data).
    """

    # Fail closed if domain not configured
    if not TARGET_DOMAIN_BYTES:
        return {"emails": [], "creds": []}

    if not path or not os.path.exists(path):
        return {"emails": [], "creds": []}

    lower = path.lower()
    creds = []

    # ----------------------------
    # Archive / binary formats
    # ----------------------------
    if lower.endswith(".pdf"):
        creds = extract_all(read_pdf(path))

    elif lower.endswith(".zip"):
        creds = extract_all(read_zip(path))

    elif lower.endswith(".rar"):
        creds = extract_all(read_rar(path))

    elif lower.endswith(".7z"):
        creds = extract_all(read_7z(path))

    # ----------------------------
    # Large Telegram text dumps
    # ----------------------------
    else:
        chunk_count = 0
        for chunk in read_raw_stream(path):
            chunk_count += 1

            # Domain gate (huge performance win)
            if TARGET_DOMAIN_BYTES not in chunk.lower():
                continue

            creds.extend(extract_all(chunk))

            if chunk_count % 5 == 0:
                print(
                    f"[extractor] chunks={chunk_count} matches={len(creds)}",
                    flush=True
                )

    # ----------------------------
    # Deduplicate + scope
    # ----------------------------
    dedup = {}
    for email, password in creds:
        if email.endswith(TARGET_DOMAIN):
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
