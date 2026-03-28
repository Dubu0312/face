#!/usr/bin/env python3
"""
Script to reorganize face match images into folder structure:
<camera_id>/<year>/<month>/<date>/<filename>

Filename format: 20260109_073526_819_match_id97_det0.84_blur970.6_rec0.325.jpg
                 YYYYMMDD_...
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Tuple

# Configuration
MATCH_DIR = Path("/home/danglt/manh/face/app/captures/match")
CAMERA_ID = "3"


def parse_date_from_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    """
    Extract year, month, day from filename.
    Filename format: YYYYMMDD_...
    Returns: (year, month, day) or None if invalid
    """
    try:
        date_part = filename[:8]  # 20260109
        year = date_part[:4]      # 2026
        month = date_part[4:6]    # 01
        day = date_part[6:8]      # 09

        # Validate
        if len(year) == 4 and len(month) == 2 and len(day) == 2:
            if year.isdigit() and month.isdigit() and day.isdigit():
                return year, month, day
    except Exception:
        pass
    return None


def reorganize_files():
    """Move files from match folder to new structure."""

    if not MATCH_DIR.exists():
        print(f"Error: Directory not found: {MATCH_DIR}")
        return

    # Get all jpg files in match directory (not in subdirectories)
    files = [f for f in MATCH_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.jpg']

    print(f"Found {len(files)} files to process")

    moved_count = 0
    error_count = 0

    for file_path in files:
        filename = file_path.name

        # Parse date from filename
        date_info = parse_date_from_filename(filename)
        if date_info is None:
            print(f"Warning: Could not parse date from: {filename}")
            error_count += 1
            continue

        year, month, day = date_info

        # Create target directory: match/3/2026/01/09/
        target_dir = MATCH_DIR / CAMERA_ID / year / month / day
        target_dir.mkdir(parents=True, exist_ok=True)

        # Move file
        target_path = target_dir / filename

        if target_path.exists():
            print(f"Warning: File already exists: {target_path}")
            error_count += 1
            continue

        shutil.move(str(file_path), str(target_path))
        moved_count += 1

        if moved_count % 100 == 0:
            print(f"Moved {moved_count} files...")

    print(f"\nDone!")
    print(f"  Moved: {moved_count} files")
    print(f"  Errors: {error_count} files")


if __name__ == "__main__":
    reorganize_files()
