"""
AI Classifier Module
Sends file metadata to Gemini and parses the JSON classification.

Falls back to a simple rule-based heuristic if no API key is configured,
so the app remains demoable without a live API key.
"""

import os
import json
import re

from .safety import enforce_safety, is_protected

import streamlit as st

api_key = st.secrets["GEMINI_API_KEY"]
print(api_key)

SYSTEM_PROMPT = """You are a system cleanup assistant.

You will be given information about a single file: its path, size in MB,
and how many days ago it was last modified.

Classify the file into exactly one of:
- SAFE_DELETE: file is very likely safe to delete (e.g. old logs, temp files, caches)
- REVIEW: file might be deletable but a human should check (e.g. old backups, large unknown files)
- KEEP: file should not be deleted (e.g. source code, documents, recently modified files)

Respond with ONLY a JSON object in this exact format, no extra text:
{
  "classification": "SAFE_DELETE" | "REVIEW" | "KEEP",
  "reason": "short explanation"
}
"""


def _build_user_prompt(file_info):
    return (
        f"File: {file_info['path']}\n"
        f"Size: {file_info['size_mb']} MB\n"
        f"Age: {file_info['age_days']} days\n"
        f"Extension: {file_info['extension']}\n"
    )


def _heuristic_classify(file_info):
    """
    Simple offline fallback used when GEMINI_API_KEY is not set.
    Mirrors common-sense rules so the demo still works without internet/API access.
    """
    ext = file_info["extension"]
    age = file_info["age_days"]
    size = file_info["size_mb"]

    if ext in (".log", ".tmp", ".bak", ".cache"):
        if age > 30:
            return {"classification": "SAFE_DELETE",
                    "reason": f"{ext} file not modified for {age} days"}
        return {"classification": "REVIEW",
                "reason": f"{ext} file but only {age} days old"}

    if ext == ".zip" and age > 180:
        return {"classification": "REVIEW",
                "reason": f"Old backup archive ({age} days), verify before deleting"}

    if size > 500 and age > 90:
        return {"classification": "REVIEW",
                "reason": f"Large file ({size} MB) not modified for {age} days"}

    return {"classification": "KEEP",
            "reason": "No rule matched; keeping by default"}


def _call_gemini(file_info):
    from google import genai

    client = genai.Client(api_key=API_KEY)

    prompt = SYSTEM_PROMPT + "\n\n" + _build_user_prompt(file_info)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    return json.loads(text)


def classify_file(file_info):
    """
    Classify a single file. Returns a dict:
        {
            "classification": "SAFE_DELETE" | "REVIEW" | "KEEP",
            "reason": str
        }

    Applies the rule-based safety layer to override unsafe SAFE_DELETE results.
    """
    try:
        if API_KEY:
            result = _call_gemini(file_info)
        else:
            result = _heuristic_classify(file_info)
    except Exception as e:
        # If the AI call fails for any reason, fall back to heuristic
        # and surface the error in the reason for transparency.
        result = _heuristic_classify(file_info)
        result["reason"] += f" (AI call failed, used fallback: {e})"

    # Validate classification value
    if result.get("classification") not in ("SAFE_DELETE", "REVIEW", "KEEP"):
        result["classification"] = "REVIEW"
        result["reason"] = "Unrecognized classification from model; flagged for review"

    # Apply safety override
    original = result["classification"]
    safe_classification = enforce_safety(file_info, original)
    if safe_classification != original:
        result["classification"] = safe_classification
        result["reason"] += " [overridden by safety rule: protected file type]"

    result["protected"] = is_protected(file_info["path"])
    return result


if __name__ == "__main__":
    sample = {
        "path": "data/sample_disk/logs/old.log",
        "size_mb": 250.0,
        "age_days": 400,
        "extension": ".log",
    }
    print(json.dumps(classify_file(sample), indent=2))
