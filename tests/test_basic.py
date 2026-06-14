"""
Basic test suite for the Disk Cleanup Recommender.

Run with:
    pytest tests/
"""

import os
import shutil
import sys
import tempfile

import pytest

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scanner import scan_directory
from src.safety import is_protected, enforce_safety, PROTECTED_EXTENSIONS
from src.classifier import _heuristic_classify, classify_file
from src.deleter import move_to_recycle
from src.report_generator import generate_csv_report, generate_markdown_report


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# Scanner tests
# ---------------------------------------------------------------------------

def test_scan_directory_finds_files(temp_dir):
    open(os.path.join(temp_dir, "a.txt"), "w").write("hello")
    sub = os.path.join(temp_dir, "sub")
    os.makedirs(sub)
    open(os.path.join(sub, "b.log"), "w").write("world")

    results = scan_directory(temp_dir)
    paths = {os.path.basename(r["path"]) for r in results}

    assert "a.txt" in paths
    assert "b.log" in paths
    for r in results:
        assert "size_mb" in r
        assert "age_days" in r
        assert "extension" in r


def test_scan_directory_invalid_path():
    with pytest.raises(ValueError):
        scan_directory("/this/path/does/not/exist")


# ---------------------------------------------------------------------------
# Safety layer tests
# ---------------------------------------------------------------------------

def test_protected_extensions_detected():
    for ext in PROTECTED_EXTENSIONS:
        assert is_protected(f"some/path/file{ext}")


def test_unprotected_extension_not_flagged():
    assert not is_protected("some/path/old.log")


def test_enforce_safety_overrides_protected_safe_delete():
    file_info = {"path": "documents/report.pdf"}
    result = enforce_safety(file_info, "SAFE_DELETE")
    assert result == "KEEP"


def test_enforce_safety_does_not_change_unprotected():
    file_info = {"path": "logs/old.log"}
    result = enforce_safety(file_info, "SAFE_DELETE")
    assert result == "SAFE_DELETE"


# ---------------------------------------------------------------------------
# Classifier tests (heuristic fallback, no API key required)
# ---------------------------------------------------------------------------

def test_heuristic_classify_old_log_is_safe_delete():
    file_info = {
        "path": "logs/old.log",
        "size_mb": 0.01,
        "age_days": 400,
        "extension": ".log",
    }
    result = _heuristic_classify(file_info)
    assert result["classification"] == "SAFE_DELETE"


def test_heuristic_classify_recent_log_is_review():
    file_info = {
        "path": "logs/app.log",
        "size_mb": 0.01,
        "age_days": 2,
        "extension": ".log",
    }
    result = _heuristic_classify(file_info)
    assert result["classification"] == "REVIEW"


def test_classify_file_applies_safety_override():
    # A .pdf that the heuristic would never mark SAFE_DELETE anyway,
    # but explicitly verify the safety flag and classification.
    file_info = {
        "path": "documents/report.pdf",
        "size_mb": 5.0,
        "age_days": 10,
        "extension": ".pdf",
    }
    result = classify_file(file_info)
    assert result["classification"] in ("KEEP", "REVIEW")
    assert result["protected"] is True


# ---------------------------------------------------------------------------
# Deleter tests
# ---------------------------------------------------------------------------

def test_move_to_recycle(temp_dir):
    src_file = os.path.join(temp_dir, "old.log")
    open(src_file, "w").write("data")

    recycle_dir = os.path.join(temp_dir, "deleted")
    new_path = move_to_recycle(src_file, recycle_dir, source_root=temp_dir)

    assert not os.path.exists(src_file)
    assert os.path.exists(new_path)
    assert new_path.startswith(recycle_dir)


def test_move_to_recycle_avoids_collision(temp_dir):
    recycle_dir = os.path.join(temp_dir, "deleted")
    os.makedirs(recycle_dir)
    # Pre-create a colliding file in recycle
    open(os.path.join(recycle_dir, "dup.txt"), "w").write("existing")

    src_file = os.path.join(temp_dir, "dup.txt")
    open(src_file, "w").write("new")

    new_path = move_to_recycle(src_file, recycle_dir, source_root=temp_dir)

    assert os.path.exists(new_path)
    assert new_path != os.path.join(recycle_dir, "dup.txt")


# ---------------------------------------------------------------------------
# Report generator tests
# ---------------------------------------------------------------------------

def test_generate_csv_and_markdown_reports(temp_dir):
    results = [
        {
            "path": "logs/old.log",
            "size_mb": 1.5,
            "age_days": 400,
            "classification": "SAFE_DELETE",
            "reason": "old log",
            "action": "MOVED_TO_RECYCLE",
            "moved_to": "deleted/logs/old.log",
        },
        {
            "path": "documents/report.pdf",
            "size_mb": 5.0,
            "age_days": 10,
            "classification": "KEEP",
            "reason": "protected file",
            "action": "NONE",
            "moved_to": "",
        },
    ]

    csv_path = os.path.join(temp_dir, "report.csv")
    md_path = os.path.join(temp_dir, "report.md")

    generate_csv_report(results, csv_path)
    generate_markdown_report(results, md_path)

    assert os.path.exists(csv_path)
    assert os.path.exists(md_path)

    with open(md_path) as f:
        content = f.read()
        assert "Disk Cleanup Report" in content
        assert "old.log" in content
        assert "Recovered Space" in content
