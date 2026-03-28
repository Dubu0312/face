"""
Face capture module - Save face images on detection
"""
import os
import cv2
import time
import requests
import threading
from datetime import datetime


class FaceCapture:
    """Capture and save face images with metadata in filename"""

    def _api_events_enabled(self):
        return self.config.ENABLE_API_EVENT or getattr(self.config, "ENABLE_API_EVENT_2", False)

    def __init__(self, config, id_server_map=None):
        """
        Initialize face capture

        Args:
            config: Config instance
            id_server_map: dict mapping person_id -> id_server (for API events)
        """
        self.config = config
        self.capture_dir = config.CAPTURE_DIR
        self.enabled = config.ENABLE_CAPTURE
        self.id_server_map = id_server_map or {}

        # Track last capture time per person to avoid spam
        self.last_capture_time = {}  # {person_id: timestamp}

        # Create capture directory if enabled
        if self.enabled:
            self._setup_directories()

    def _setup_directories(self):
        """Create capture base directory"""
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir)
            print(f"[CAPTURE] Created directory: {self.capture_dir}")

    def should_capture(self, verdict, person_id):
        """
        Check if should capture based on verdict and cooldown

        Args:
            verdict: Current verdict (MATCH, UNKNOWN, FAKE, etc.)
            person_id: Person ID (-1 for unknown)

        Returns:
            bool: True if should capture
        """
        if not self.enabled:
            return False

        # Check verdict filter
        if verdict == "MATCH" and not self.config.CAPTURE_ON_MATCH:
            return False
        if verdict == "UNKNOWN" and not self.config.CAPTURE_ON_UNKNOWN:
            return False
        if verdict == "FAKE" and not self.config.CAPTURE_ON_FAKE:
            return False
        if verdict == "BLUR" and not self.config.CAPTURE_ON_BLUR:
            return False
        if verdict == "LOW_QUALITY" and not self.config.CAPTURE_ON_LOW_QUALITY:
            return False

        # Check cooldown
        now = time.time()
        key = f"{verdict}_{person_id}"

        if key in self.last_capture_time:
            elapsed = now - self.last_capture_time[key]
            if elapsed < self.config.CAPTURE_COOLDOWN:
                return False

        return True

    def capture(self, frame, result, vote_result=None):
        """
        Capture and save face image

        Args:
            frame: BGR frame
            result: Processing result dict
            vote_result: Voting result dict (optional)

        Returns:
            str: Path to saved file, or None if not saved
        """
        verdict = result.get('verdict', 'UNKNOWN')
        person_id = result.get('person_id', -1)

        if not self.should_capture(verdict, person_id):
            return None

        # Build filename with metadata
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds

        # Verdict
        verdict_str = verdict.lower()

        # Person info
        if person_id != -1:
            person_name = result.get('person_name', '')
            if person_name:
                person_str = f"id{person_id}_{person_name}"
            else:
                person_str = f"id{person_id}"
        else:
            person_str = "unknown"

        # Scores
        scores = []
        if result.get('det_score') is not None:
            scores.append(f"det{result['det_score']:.2f}")
        if result.get('blur') is not None:
            scores.append(f"blur{result['blur']:.1f}")
        if result.get('fas_real') is not None:
            fas_state = "real" if result.get('fas_pass') else "fake"
            scores.append(f"{fas_state}{result['fas_real']:.2f}")
        if result.get('rec_score') is not None:
            scores.append(f"rec{result['rec_score']:.3f}")

        score_str = "_".join(scores)

        # Vote info (if available)
        vote_str = ""
        if vote_result and vote_result.get('stable'):
            vote_str = f"_stable{vote_result['vote_count']}-{vote_result['vote_total']}"

        # Final filename
        filename = f"{timestamp}_{verdict_str}_{person_str}_{score_str}{vote_str}.jpg"

        # Build date-based directory: <capture_dir>/<camera_id>/<year>/<month>/<day>/
        now = datetime.now()
        camera_id = self.config.CAMERA_ID
        save_dir = os.path.join(
            self.capture_dir, camera_id,
            now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
        )
        os.makedirs(save_dir, exist_ok=True)

        # Full path
        filepath = os.path.join(save_dir, filename)

        # Get image to save
        if self.config.CAPTURE_FULL_FRAME:
            # Save full frame with annotations
            img_to_save = frame.copy()
        else:
            # Save face crop only
            if 'bbox' in result:
                x1, y1, x2, y2 = result['bbox']
                # Add padding
                pad = 20
                x1 = max(0, x1 - pad)
                y1 = max(0, y1 - pad)
                x2 = min(frame.shape[1], x2 + pad)
                y2 = min(frame.shape[0], y2 + pad)
                img_to_save = frame[y1:y2, x1:x2].copy()
            else:
                # No bbox, save full frame
                img_to_save = frame.copy()

        # Save image
        try:
            cv2.imwrite(filepath, img_to_save)

            # Update last capture time
            key = f"{verdict}_{person_id}"
            self.last_capture_time[key] = time.time()

            if self.config.VERBOSE:
                print(f"[CAPTURE] Saved: {filename}")

            # Send API event in background thread (MATCH only)
            if verdict == "MATCH" and self._api_events_enabled():
                threading.Thread(
                    target=self._send_api_events,
                    args=(now, camera_id, filename, person_id),
                    daemon=True
                ).start()

            return filepath

        except Exception as e:
            print(f"[CAPTURE] Error saving {filename}: {e}")
            return None

    def _post_json(self, label, url, body, bearer_token, timeout):
        if not url:
            if self.config.VERBOSE:
                print(f"[{label}] Skip: empty URL")
            return

        try:
            headers = {}
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"

            resp = requests.post(url, json=body, headers=headers, timeout=timeout)
            if resp.status_code in (200, 201):
                if self.config.VERBOSE:
                    print(f"[{label}] OK")
            else:
                print(f"[{label}] Error ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            print(f"[{label}] Request failed: {e}")

    def _send_api_events(self, now, camera_id, filename, person_id):
        """Send face event requests to configured APIs (runs in background thread)"""
        employee_id = self.id_server_map.get(person_id)
        if employee_id is None:
            if self.config.VERBOSE:
                print(f"[API] Skip: no id_server for person_id={person_id}")
            return

        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        photo_url = (
            f"{self.config.API_IMAGE_PREFIX}/{camera_id}/"
            f"{now.strftime('%Y')}/{now.strftime('%m')}/{now.strftime('%d')}/{filename}"
        )

        if self.config.ENABLE_API_EVENT:
            body = {
                "time": time_str,
                "camera_id": int(camera_id),
                "description": "Face Recognition",
                "normal_image": photo_url,
                "yolo_image": "",
                "employee_id": employee_id
            }
            self._post_json(
                "API",
                self.config.API_URL,
                body,
                self.config.API_BEARER_TOKEN,
                self.config.API_TIMEOUT,
            )

        if getattr(self.config, "ENABLE_API_EVENT_2", False):
            photo_prefix = getattr(self.config, "API2_PHOTO_PREFIX", self.config.API_IMAGE_PREFIX)
            photo_url_v2 = (
                f"{photo_prefix}/{camera_id}/"
                f"{now.strftime('%Y')}/{now.strftime('%m')}/{now.strftime('%d')}/{filename}"
            )
            body2 = {
                "log_time": time_str,
                "employee_id": employee_id,
                "photo_url": photo_url_v2,
                "camera_id": int(camera_id)
            }
            self._post_json(
                "API2",
                getattr(self.config, "API2_URL", ""),
                body2,
                getattr(self.config, "API2_BEARER_TOKEN", ""),
                getattr(self.config, "API2_TIMEOUT", self.config.API_TIMEOUT),
            )

    def get_stats(self):
        """
        Get capture statistics

        Returns:
            dict: Total file count under camera directory
        """
        if not self.enabled or not os.path.exists(self.capture_dir):
            return {}

        camera_dir = os.path.join(self.capture_dir, self.config.CAMERA_ID)
        total = 0
        if os.path.exists(camera_dir):
            for root, _dirs, files in os.walk(camera_dir):
                total += sum(1 for f in files if f.endswith('.jpg'))

        return {'total': total}

    def cleanup_old_captures(self, days=7):
        """
        Delete captures older than specified days

        Args:
            days: Number of days to keep

        Returns:
            int: Number of files deleted
        """
        if not self.enabled or not os.path.exists(self.capture_dir):
            return 0

        deleted = 0
        now = time.time()
        max_age = days * 24 * 3600  # days to seconds

        camera_dir = os.path.join(self.capture_dir, self.config.CAMERA_ID)
        if not os.path.exists(camera_dir):
            return 0

        for root, _dirs, files in os.walk(camera_dir):
            for filename in files:
                if not filename.endswith('.jpg'):
                    continue
                filepath = os.path.join(root, filename)
                file_age = now - os.path.getmtime(filepath)
                if file_age > max_age:
                    try:
                        os.remove(filepath)
                        deleted += 1
                    except Exception as e:
                        print(f"[CAPTURE] Error deleting {filename}: {e}")

        if deleted > 0:
            print(f"[CAPTURE] Deleted {deleted} old captures (>{days} days)")

        return deleted

    def __repr__(self):
        stats = self.get_stats()
        return f"FaceCapture(enabled={self.enabled}, total={stats.get('total', 0)})"
