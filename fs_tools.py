"""
fs_tools.py - Part A: file system tools for the resume assistant.

Four plain Python functions. None of them knows anything about an LLM,
so they can be imported and tested on their own.

Every tool returns an error as data instead of raising an exception:
    {"success": False, "error": "..."}
"""

import os
import re
from datetime import datetime

from docx import Document
from pypdf import PdfReader

SUPPORTED = (".pdf", ".docx", ".txt")


def _error(message):
    """Standard failure response shared by the tools."""
    return {"success": False, "error": message}


def read_file(filepath):
    """Read a PDF, DOCX or TXT file. Returns its text content and metadata."""
    if not os.path.isfile(filepath):
        return _error(f"File not found: {filepath}")

    extension = os.path.splitext(filepath)[1].lower()
    if extension not in SUPPORTED:
        return _error(f"Unsupported file type '{extension}'. Supported: {', '.join(SUPPORTED)}")

    try:
        if extension == ".pdf":
            content = "\n".join(page.extract_text() or "" for page in PdfReader(filepath).pages)
        elif extension == ".docx":
            content = "\n".join(p.text for p in Document(filepath).paragraphs)
        else:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                content = f.read()
    except Exception as exc:
        return _error(f"Could not read {filepath}: {exc}")

    return {
        "success": True,
        "content": content,
        "metadata": {
            "filename": os.path.basename(filepath),
            "extension": extension,
            "size_bytes": os.path.getsize(filepath),
            "word_count": len(content.split()),
        },
    }


def list_files(directory, extension=None):
    """List files in a directory, optionally filtered by extension ('.pdf' or 'pdf')."""
    if not os.path.isdir(directory):
        return [{"error": f"Directory not found: {directory}"}]

    if extension and not extension.startswith("."):
        extension = "." + extension

    results = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if extension and not name.lower().endswith(extension.lower()):
            continue
        results.append({
            "name": name,
            "path": path,
            "size_bytes": os.path.getsize(path),
            "modified": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M"),
        })
    return results


def write_file(filepath, content):
    """Write text to a file, creating parent folders if needed."""
    if not filepath.strip():
        return _error("filepath must not be empty.")
    try:
        folder = os.path.dirname(filepath)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as exc:
        return _error(f"Could not write {filepath}: {exc}")
    return {"success": True, "filepath": filepath, "chars_written": len(content)}


def search_in_file(filepath, keyword, context_chars=50):
    """Case-insensitive keyword search. Returns each match with surrounding text."""
    if not keyword.strip():
        return _error("keyword must not be empty.")

    file_result = read_file(filepath)
    if not file_result["success"]:
        return file_result

    content = file_result["content"]
    matches = []
    for m in re.finditer(re.escape(keyword), content, re.IGNORECASE):
        start = max(0, m.start() - context_chars)
        end = m.end() + context_chars
        matches.append({
            "position": m.start(),
            "context": content[start:end].replace("\n", " "),
        })

    return {
        "success": True,
        "filepath": filepath,
        "keyword": keyword,
        "match_count": len(matches),
        "matches": matches,
    }
