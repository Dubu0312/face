#!/usr/bin/env python3
"""
Script to delete duplicate face images.
Duplicate = same match_id AND time difference < 10 seconds
Keep only the first image, delete the rest.

Filename format: 20260109_073526_819_match_id97_det0.84_blur970.6_rec0.325.jpg
                 YYYYMMDD_HHMMSS_mmm_match_idXX_...
"""

import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration
MATCH_DIR = Path("/home/danglt/manh/face//match")
CAMERA_ID = "3"
TIME_THRESHOLD_SECONDS = 10


def parse_filename(filename):
    """
    Parse filename to extract timestamp and match_id.
    Returns: (datetime, match_id) or (None, None) if invalid
    """
    try:
        # Extract datetime: 20260109_073526_819 -> 2026-01-09 07:35:26.819
        date_part = filename[:8]        # 20260109
        time_part = filename[9:15]      # 073526
        ms_part = filename[16:19]       # 819

        year = int(date_part[:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6])
        ms = int(ms_part)

        dt = datetime(year, month, day, hour, minute, second, ms * 1000)

        # Extract match_id: match_id97 -> 97
        match = re.search(r'match_id(\d+)', filename)
        if match:
            match_id = int(match.group(1))
            return dt, match_id

    except Exception as e:
        pass

    return None, None


def find_duplicates():
    """Find and delete duplicate images."""

    # Scan directory: match/3/year/month/day/
    base_dir = MATCH_DIR / CAMERA_ID

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        return

    # Collect all images with their info
    all_images = []

    for jpg_file in base_dir.rglob("*.jpg"):
        dt, match_id = parse_filename(jpg_file.name)
        if dt and match_id:
            all_images.append({
                'path': jpg_file,
                'datetime': dt,
                'match_id': match_id
            })

    print(f"Found {len(all_images)} images")

    # Sort by datetime
    all_images.sort(key=lambda x: x['datetime'])

    # Track last seen time for each match_id
    last_seen = {}  # match_id -> datetime

    to_delete = []

    for img in all_images:
        match_id = img['match_id']
        dt = img['datetime']

        if match_id in last_seen:
            time_diff = (dt - last_seen[match_id]).total_seconds()

            if time_diff < TIME_THRESHOLD_SECONDS:
                # Duplicate - mark for deletion
                to_delete.append(img['path'])
            else:
                # New occurrence - update last seen
                last_seen[match_id] = dt
        else:
            # First occurrence
            last_seen[match_id] = dt

    print(f"Found {len(to_delete)} duplicate images to delete")

    # Confirm before deleting
    if to_delete:
        print("\nSample files to delete:")
        for f in to_delete[:10]:
            print(f"  {f.name}")
        if len(to_delete) > 10:
            print(f"  ... and {len(to_delete) - 10} more")

        confirm = input("\nProceed with deletion? (yes/no): ")
        if confirm.lower() == 'yes':
            deleted = 0
            for f in to_delete:
                try:
                    f.unlink()
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {f}: {e}")

            print(f"\nDeleted {deleted} files")
        else:
            print("Cancelled")
    else:
        print("No duplicates found")


if __name__ == "__main__":
    find_duplicates()