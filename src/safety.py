"""
Rule-Based Safety Layer
Prevents the agent from ever recommending deletion of critical file types,
regardless of what the LLM says.
"""

import os

# Extensions that must NEVER be deleted automatically
PROTECTED_EXTENSIONS = [
    ".exe",
    ".dll",
    ".py",
    ".docx",
    ".pdf",
    ".xlsx",
    ".pptx",
    ".sys",
    ".ini",
    ".db",
]

# Folders that should never be scanned/touched even if present under root
PROTECTED_FOLDER_NAMES = [
    "system32",
    ".git",
    "node_modules",
    "venv",
    ".venv",
]


def is_protected(file_path):
    """
    Return True if the file should never be deleted, based on extension
    or location, regardless of LLM classification.
    """
    lower_path = file_path.lower()

    for ext in PROTECTED_EXTENSIONS:
        if lower_path.endswith(ext):
            return True

    for folder in PROTECTED_FOLDER_NAMES:
        if f"{os.sep}{folder}{os.sep}".lower() in lower_path or lower_path.startswith(folder.lower()):
            return True

    return False


def enforce_safety(file_info, classification):
    """
    Given a file's metadata and the AI's classification, override the
    classification to KEEP if the file is protected.

    Returns the (possibly overridden) classification string.
    """
    if is_protected(file_info["path"]) and classification == "SAFE_DELETE":
        return "KEEP"
    return classification
