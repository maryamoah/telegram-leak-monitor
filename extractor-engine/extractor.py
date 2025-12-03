import os, re, zipfile, subprocess
from pathlib import Path
import py7zr, rarfile
from PyPDF2 import PdfReader

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@squ\.edu\.om", re.I)

def read_head(path, max_bytes=5000000):
    try:
        with open(path, "rb") as f:
            return f.read(max_bytes).decode(errors="ignore")
    except:
        return ""

def extract_txt(path):
    return read_head(path)

def extract_pdf(path):
    try:
        reader = PdfReader(path)
        text = ""
        for p in reader.pages:
            text += p.extract_text() or ""
        return text
    except:
        return ""

def extract_zip(path):
    text = ""
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                try:
                    text += z.read(name).decode(errors="ignore")
                except:
                    pass
        return text
    except:
        return ""

def extract_rar(path):
    text = ""
    try:
        rf = rarfile.RarFile(path)
        for f in rf.infolist():
            try:
                text += rf.read(f).decode(errors="ignore")
            except:
                pass
        return text
    except:
        return ""

def extract_7z(path):
    text = ""
    try:
        with py7zr.SevenZipFile(path, "r") as z:
            files = z.readall()
            for name, file in files.items():
                try:
                    text += file.read().decode(errors="ignore")
                except:
                    pass
        return text
    except:
        return ""

def extract_all(path):
    lower = path.lower()

    if lower.endswith(".txt") or lower.endswith(".csv") or lower.endswith(".log"):
        return extract_txt(path)
    elif lower.endswith(".pdf"):
        return extract_pdf(path)
    elif lower.endswith(".zip"):
        return extract_zip(path)
    elif lower.endswith(".rar"):
        return extract_rar(path)
    elif lower.endswith(".7z"):
        return extract_7z(path)
    else:
        # fallback to strings
        try:
            out = subprocess.check_output(["strings", path], timeout=20)
            return out.decode(errors="ignore")
        except:
            return read_head(path)
