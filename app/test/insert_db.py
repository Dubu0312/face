#!/usr/bin/env python3
"""
Script to insert face recognition events to API.
API endpoint: http://localhost:3000/api/face/insertEvent

For each image in match folder, extract info and call API.
"""

import os
import re
import sqlite3
import requests
from pathlib import Path

# Configuration
MATCH_DIR = Path("/home/danglt/manh/face/app/captures/match")
CAMERA_ID = 3
DB_PATH = "/home/danglt/manh/face/app/faces.db"
API_URL = "http://192.168.100.243:3000/api/face/insertEvent"


def load_person_mapping():
    """Load person_id -> id_server mapping from database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT person_id, id_server FROM persons")
    mapping = {}
    for person_id, id_server in cursor.fetchall():
        if id_server is not None:
            mapping[person_id] = id_server
    conn.close()
    print(f"Loaded {len(mapping)} person mappings")
    return mapping


def parse_filename(filename):
    """
    Parse filename to extract time and match_id.
    Filename: 20260109_073526_819_match_id97_det0.84_blur970.6_rec0.325.jpg
    Returns: (time_str, match_id) or (None, None)
    """
    try:
        # Extract datetime: 20260109_073526 -> 2026-01-09 07:35:26
        date_part = filename[:8]        # 20260109
        time_part = filename[9:15]      # 073526

        year = date_part[:4]
        month = date_part[4:6]
        day = date_part[6:8]
        hour = time_part[:2]
        minute = time_part[2:4]
        second = time_part[4:6]

        time_str = f"{year}-{month}-{day} {hour}:{minute}:{second}"

        # Extract match_id
        match = re.search(r'match_id(\d+)', filename)
        if match:
            match_id = int(match.group(1))
            return time_str, match_id

    except Exception as e:
        print(f"Error parsing {filename}: {e}")

    return None, None


def insert_events():
    """Scan images and insert events to API."""

    # Load person mapping
    person_mapping = load_person_mapping()

    # Scan directory: match/3/year/month/day/
    base_dir = MATCH_DIR / str(CAMERA_ID)

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        return

    # Collect all images
    all_images = list(base_dir.rglob("*.jpg"))
    print(f"Found {len(all_images)} images")

    success_count = 0
    skip_count = 0
    error_count = 0

    for img_path in all_images:
        filename = img_path.name

        # Parse filename
        time_str, match_id = parse_filename(filename)
        if not time_str or not match_id:
            print(f"Skip (parse error): {filename}")
            skip_count += 1
            continue

        # Get employee_id from mapping
        employee_id = person_mapping.get(match_id)
        if employee_id is None:
            print(f"Skip (no id_server for person_id={match_id}): {filename}")
            skip_count += 1
            continue

        # Extract path components for normal_image
        # Path: match/3/2026/01/09/filename.jpg
        parts = img_path.parts
        # Find index of camera_id
        try:
            cam_idx = parts.index(str(CAMERA_ID))
            year = parts[cam_idx + 1]
            month = parts[cam_idx + 2]
            day = parts[cam_idx + 3]
        except (ValueError, IndexError):
            print(f"Skip (path error): {img_path}")
            skip_count += 1
            continue

        normal_image = f"/images/human_face/original/{CAMERA_ID}/{year}/{month}/{day}/{filename}"

        # Build request body
        body = {
            "time": time_str,
            "camera_id": CAMERA_ID,
            "description": "Face Recognition",
            "normal_image": normal_image,
            "yolo_image": "",
            "employee_id": employee_id
        }

        # Call API
        try:
            response = requests.post(API_URL, json=body, timeout=10)
            if response.status_code == 200 or response.status_code == 201:
                success_count += 1
                if success_count % 50 == 0:
                    print(f"Inserted {success_count} events...")
            else:
                print(f"API error ({response.status_code}): {filename} - {response.text}")
                error_count += 1
        except Exception as e:
            print(f"Request error: {filename} - {e}")
            error_count += 1

    print(f"\nDone!")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    insert_events()
