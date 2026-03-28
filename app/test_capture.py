#!/usr/bin/env python3
"""
Test script for capture feature
Creates dummy results and tests capture functionality
"""
import os
import sys
import cv2
import numpy as np

from config import Config
from capture import FaceCapture


def create_dummy_frame():
    """Create a dummy frame for testing"""
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    # Draw a fake face box
    cv2.rectangle(frame, (200, 100), (400, 300), (0, 255, 0), 2)
    cv2.putText(frame, "TEST FACE", (220, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return frame


def test_capture():
    """Test capture functionality"""
    print("=" * 60)
    print("Face Capture Feature Test")
    print("=" * 60)

    # Create config
    config = Config()
    config.ENABLE_CAPTURE = True
    config.CAPTURE_DIR = "./test_captures"
    config.CAPTURE_COOLDOWN = 0.1  # Short cooldown for testing

    # Initialize capture
    print("\n[1/3] Initializing capture...")
    capture = FaceCapture(config)
    print(f"      ✓ {capture}")

    # Test different verdicts
    frame = create_dummy_frame()

    test_cases = [
        {
            'name': 'MATCH - Recognized person',
            'result': {
                'verdict': 'MATCH',
                'person_id': 1,
                'person_name': 'John',
                'bbox': (200, 100, 400, 300),
                'bbox_wh': (200, 200),
                'det_score': 0.98,
                'blur': 85.2,
                'fas_real': 0.95,
                'fas_pass': True,
                'rec_score': 0.723
            },
            'vote_result': {
                'stable': True,
                'stable_id': 1,
                'vote_count': 7,
                'vote_total': 7
            }
        },
        {
            'name': 'FAKE - Anti-spoofing failed',
            'result': {
                'verdict': 'FAKE',
                'person_id': -1,
                'person_name': '',
                'bbox': (200, 100, 400, 300),
                'bbox_wh': (200, 200),
                'det_score': 0.95,
                'blur': 78.3,
                'fas_real': 0.35,
                'fas_pass': False,
                'rec_score': None
            },
            'vote_result': None
        },
        {
            'name': 'UNKNOWN - Not recognized',
            'result': {
                'verdict': 'UNKNOWN',
                'person_id': -1,
                'person_name': '',
                'bbox': (200, 100, 400, 300),
                'bbox_wh': (200, 200),
                'det_score': 0.88,
                'blur': 65.1,
                'fas_real': 0.92,
                'fas_pass': True,
                'rec_score': 0.35
            },
            'vote_result': None
        },
        {
            'name': 'BLUR - Blurry face',
            'result': {
                'verdict': 'BLUR',
                'person_id': -1,
                'person_name': '',
                'bbox': (200, 100, 400, 300),
                'bbox_wh': (200, 200),
                'det_score': 0.82,
                'blur': 25.5,
                'fas_real': None,
                'fas_pass': None,
                'rec_score': None
            },
            'vote_result': None
        }
    ]

    print("\n[2/3] Testing capture for different verdicts...")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {test_case['name']}")

        filepath = capture.capture(frame, test_case['result'], test_case['vote_result'])

        if filepath:
            filename = os.path.basename(filepath)
            print(f"    ✓ Captured: {filename}")
        else:
            print(f"    ✗ Not captured (disabled or cooldown)")

    # Get statistics
    print("\n[3/3] Capture statistics:")
    stats = capture.get_stats()
    print(f"      Total: {stats.get('total', 0)} captures")
    for verdict, count in stats.items():
        if verdict != 'total':
            print(f"        - {verdict}: {count}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print(f"Check captures in: {config.CAPTURE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_capture()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
