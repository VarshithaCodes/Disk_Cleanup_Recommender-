"""
Report Generator Module
Generates CSV and Markdown cleanup reports.
"""

import csv
import os
from datetime import datetime


def generate_csv_report(results, output_path="outputs/cleanup_report.csv"):
    """
    results: list of dicts with keys:
        path, size_mb, age_days, classification, reason, action, moved_to
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = ["path", "size_mb", "age_days", "classification",
                   "reason", "action", "moved_to"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    return output_path


def generate_markdown_report(results, output_path="outputs/cleanup_report.md"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    total_files = len(results)
    deleted = [r for r in results if r.get("action") == "MOVED_TO_RECYCLE"]
    recovered_mb = sum(r["size_mb"] for r in deleted)

    safe_delete_count = sum(1 for r in results if r["classification"] == "SAFE_DELETE")
    review_count = sum(1 for r in results if r["classification"] == "REVIEW")
    keep_count = sum(1 for r in results if r["classification"] == "KEEP")

    lines = []
    lines.append("# Disk Cleanup Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total Files Scanned: **{total_files}**")
    lines.append(f"- Classified SAFE_DELETE: **{safe_delete_count}**")
    lines.append(f"- Classified REVIEW: **{review_count}**")
    lines.append(f"- Classified KEEP: **{keep_count}**")
    lines.append(f"- Files Moved to Recycle Folder: **{len(deleted)}**")
    lines.append(f"- Recovered Space: **{round(recovered_mb, 2)} MB**")
    lines.append("")
    lines.append("## Details")
    lines.append("")
    lines.append("| File | Size (MB) | Age (days) | Classification | Action | Reason |")
    lines.append("|------|-----------|------------|-----------------|--------|--------|")

    for r in results:
        lines.append(
            f"| {r['path']} | {r['size_mb']} | {r['age_days']} | "
            f"{r['classification']} | {r.get('action', 'NONE')} | {r['reason']} |"
        )

    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path
