"""
Disk Scanner Module
Scans a directory and collects file metadata (path, size, age).
"""

import os
from datetime import datetime


def scan_directory(path):
    """
    Walk through the given directory and return metadata for every file.

    Returns a list of dicts:
        {
            "path": str,
            "size_mb": float,
            "age_days": int,
            "extension": str
        }
    """
    files = []

    if not os.path.isdir(path):
        raise ValueError(f"Path does not exist or is not a directory: {path}")

    for root, dirs, filenames in os.walk(path):
        for file in filenames:
            file_path = os.path.join(root, file)

            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                modified_days = (
                    datetime.now().timestamp() - os.path.getmtime(file_path)
                ) / 86400

                files.append({
                    "path": file_path,
                    "size_mb": round(size_mb, 2),
                    "age_days": int(modified_days),
                    "extension": os.path.splitext(file)[1].lower(),
                })
            except OSError:
                # Skip files that can't be accessed (permissions, broken links, etc.)
                continue

    return files


if __name__ == "__main__":
    # Quick manual test
    import json
    result = scan_directory("data/sample_disk")
    print(json.dumps(result, indent=2))
