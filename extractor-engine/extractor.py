import os
import re
import zipfile
import subprocess
from pathlib import Path

import py7zr
import rarfile
from PyPDF2 import PdfReader

# Generic email regex (any domain)
EMAIL_RE = re.compile(
    rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE
)


def read_head(path: str, max_bytes: int = 5_000_000) -> str:
    """
    Read the first max_bytes of a file and decode as best as possible.
    Used mainly for plain-text style files (txt, csv, log).
    """
    try:
        with open(path, "rb") as f:
            return f.read(max_bytes).decode(errors="ignore")
    except Exception:
        return ""


def extract_txt(path: str) -> str:
    return read_head(path)


def extract_pdf(path: str) -> str:
    """
    Extract text from a PDF using PyPDF2.
    """
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception:
        return ""


def extract_zip(path: str) -> str:
    """
    Extract text from files contained in a ZIP.
    """
    text = ""
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                try:
                    data = z.read(name)
                    text += data.decode(errors="ignore")
                except Exception:
                    # Ignore files we can't decode
                    pass
        return text
    except Exception:
        return ""


def extract_rar(path: str) -> str:
    """
    Extract text from files contained in a RAR.
    """
    text = ""
    try:
        with rarfile.RarFile(path) as rf:
            for info in rf.infolist():
                try:
                    data = rf.read(info)
                    text += data.decode(errors="ignore")
                except Exception:
                    pass
        return text
    except Exception:
        return ""


def extract_7z(path: str) -> str:
    """
    Extract text from files contained in a 7z archive.
    """
    text = ""
    try:
        with py7zr.SevenZipFile(path, "r") as z:
            files = z.readall()
            for name, f in files.items():
                try:
                    text += f.read().decode(errors="ignore")
                except Exception:
                    pass
        return text
    except Exception:
        return ""


def extract_emails_from_text(text: str) -> list[str]:
    """
    Run email regex on decoded text.
    """
    if not text:
        return []

    raw = text.encode(errors="ignore")
    found = EMAIL_RE.findall(raw)
    # Deduplicate and decode bytes → str
    emails = list({e.decode(errors="ignore") for e in found})
    return emails


def scan_binary_for_emails(path: str) -> list[str]:
    """
    Final fallback: scan the entire file as binary in chunks
    and look for email patterns directly in bytes.

    This works even on binary dumps, partially corrupted files,
    or huge logs with strange encoding.
    """
    results: set[bytes] = set()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)  # 4 MB
            if not chunk:
                break

            found = EMAIL_RE.findall(chunk)
            for e in found:
                results.add(e)

    # Deduplicate and decode
    return [e.decode(errors="ignore") for e in results]


def extract_emails(path: str) -> list[str]:
    """
    Main entrypoint: given a file path, try multiple strategies
    to find emails inside, then fall back to raw binary scanning.
    """
    if not path or not os.path.exists(path):
        return []

    lower = path.lower()
    emails: list[str] = []

    # 1) Obvious text-like formats
    if lower.endswith((".txt", ".csv", ".log")):
        text = extract_txt(path)
        emails = extract_emails_from_text(text)
        if emails:
            return emails

    # 2) PDFs
    if lower.endswith(".pdf"):
        text = extract_pdf(path)
        emails = extract_emails_from_text(text)
        if emails:
            return emails

    # 3) Archives
    if lower.endswith(".zip"):
        text = extract_zip(path)
        emails = extract_emails_from_text(text)
        if emails:
            return emails

    if lower.endswith(".rar"):
        text = extract_rar(path)
        emails = extract_emails_from_text(text)
        if emails:
            return emails

    if lower.endswith(".7z"):
        text = extract_7z(path)
        emails = extract_emails_from_text(text)
        if emails:
            return emails

    # 4) Fallback for everything else:
    #    use binary-safe scanning on the full file
    return scan_binary_for_emails(path)
