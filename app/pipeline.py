"""
Main pipeline for face recognition with anti-spoofing
"""
import cv2
import time
from collections import deque

from utils import (
    draw_label_box,
    pick_largest_face,
    check_blur_quality,
    resize_frame
)
from capture import FaceCapture


class RecognitionPipeline:
    """Main pipeline for face detection, anti-spoofing, and recognition"""

    def __init__(self, config, detector, recognizer, anti_spoof=None, face_capture=None):
        """
        Initialize pipeline

        Args:
            config: Config instance
            detector: FaceDetector instance
            recognizer: FaceRecognizer instance
            anti_spoof: AntiSpoofing instance (optional)
            face_capture: FaceCapture instance (optional)
        """
        self.config = config
        self.detector = detector
        self.recognizer = recognizer
        self.anti_spoof = anti_spoof
        self.face_capture = face_capture

        # Stats for logging
        self.processed_frames = 0
        self.processed_idx = 0
        self.sum_det_ms = 0.0
        self.sum_fas_ms = 0.0
        self.sum_rec_ms = 0.0
        self.t_last_log = time.perf_counter()

        # Event logging
        self.last_event_ts = 0.0
        self.last_event_key = None

    def process_frame(self, frame, frame_idx):
        """
        Process a single frame

        Args:
            frame: BGR frame
            frame_idx: Frame index

        Returns:
            dict: Processing result
        """
        # Resize for performance
        vis = resize_frame(frame, self.config.MAX_WIDTH)

        # Skip frames
        if self.config.SKIP_FRAMES > 0 and (frame_idx % (self.config.SKIP_FRAMES + 1) != 0):
            return {'skip': True, 'frame': vis}

        self.processed_idx += 1
        self.processed_frames += 1

        # Detect faces
        t0 = time.perf_counter()
        faces = self.detector.detect(vis)
        det_ms = (time.perf_counter() - t0) * 1000.0
        self.sum_det_ms += det_ms

        if not faces:
            self.recognizer.vote_hist.append(self.recognizer.unknown_id)
            return {
                'skip': False,
                'frame': vis,
                'has_face': False,
                'det_ms': det_ms
            }

        # Pick largest face if configured
        if self.config.LARGEST_ONLY:
            faces = [pick_largest_face(faces)]

        # Process face
        result = self._process_face(faces[0], vis, det_ms)
        result['frame'] = vis
        result['skip'] = False
        result['has_face'] = True

        return result

    def _process_face(self, face, frame, det_ms):
        """Process a single detected face"""
        x1, y1, x2, y2 = face.bbox.astype(int)
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        det_score = float(face.det_score)

        result = {
            'bbox': (x1, y1, x2, y2),
            'bbox_wh': (w, h),
            'det_score': det_score,
            'det_ms': det_ms,
            'verdict': 'UNKNOWN',
            'person_id': self.recognizer.unknown_id,
            'person_name': '',
            'blur': None,
            'fas_real': None,
            'fas_ms': 0.0,
            'fas_pass': None,
            'rec_score': None,
            'rec_ms': 0.0
        }

        # Quality checks
        if det_score < self.config.MIN_DET_SCORE or min(w, h) < self.config.MIN_FACE_SIZE:
            result['verdict'] = 'LOW_QUALITY'
            return result

        # Blur check
        crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
        is_good, blur = check_blur_quality(crop, self.config.MIN_BLUR)
        result['blur'] = blur

        if not is_good:
            result['verdict'] = 'BLUR'
            return result

        # Anti-spoofing check
        if self.anti_spoof and (
            self.config.SPOOF_EVERY <= 1 or
            (self.processed_idx % self.config.SPOOF_EVERY == 0)
        ):
            fas_result = self.anti_spoof.is_real(
                frame, (x1, y1, x2, y2),
                threshold=self.config.SPOOF_THRESHOLD
            )
            result['fas_real'] = fas_result['real_prob']
            result['fas_ms'] = fas_result['elapsed_ms']
            result['fas_pass'] = fas_result['is_real']
            self.sum_fas_ms += fas_result['elapsed_ms']

            if not fas_result['is_real']:
                result['verdict'] = 'FAKE'
                return result

        # Recognition
        rec_result = self.recognizer.recognize_face(face)
        result['rec_score'] = rec_result['score_smooth']
        result['rec_ms'] = rec_result['elapsed_ms']
        result['best_score'] = rec_result['best_score']
        result['second_score'] = rec_result['second_score']
        self.sum_rec_ms += rec_result['elapsed_ms']

        if rec_result['match']:
            result['verdict'] = 'MATCH'
            result['person_id'] = rec_result['person_id']
            result['person_name'] = rec_result['person_name']
        else:
            result['verdict'] = 'UNKNOWN'

        return result

    def draw_result(self, frame, result):
        """Draw result on frame"""
        if not result.get('has_face', False):
            draw_label_box(
                frame, 10, 30,
                f"NO FACE | det_ms={result.get('det_ms', 0):.1f}",
                (0, 0, 255), bg=(0, 0, 0), scale=0.75
            )
            return

        x1, y1, x2, y2 = result['bbox']
        w, h = result['bbox_wh']
        verdict = result['verdict']

        # Box color
        if verdict == "MATCH":
            box_color = (0, 255, 0)
        elif verdict == "FAKE":
            box_color = (0, 0, 255)
        elif verdict in ("LOW_QUALITY", "BLUR"):
            box_color = (0, 0, 255)
        else:
            box_color = (0, 165, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)

        # Text overlay
        ty = y1 - 10
        if ty < 90:
            ty = y2 + 25

        # 1) Detection line
        det_line = f"DET: score={result['det_score']:.2f} size={w}x{h} det_ms={result['det_ms']:.1f}"
        draw_label_box(frame, x1, ty, det_line, (255, 255, 255), (0, 0, 0))
        ty += 22

        # 2) Quality line
        blur_val = result['blur'] if result['blur'] is not None else -1.0
        q_line = f"Q: blur={blur_val:.1f} min_blur={self.config.MIN_BLUR:.1f}"
        draw_label_box(frame, x1, ty, q_line, (255, 255, 255), (0, 0, 0))
        ty += 22

        # 3) FAS line
        if self.anti_spoof:
            if result['fas_real'] is None:
                fas_line = f"FAS: SKIP every={self.config.SPOOF_EVERY}"
                draw_label_box(frame, x1, ty, fas_line, (220, 220, 220), (0, 0, 0))
            else:
                fas_state = "LIVE" if result['fas_pass'] else "FAKE"
                fas_color = (0, 255, 0) if result['fas_pass'] else (0, 0, 255)
                fas_line = f"FAS: {fas_state} real_prob={result['fas_real']:.2f} thr={self.config.SPOOF_THRESHOLD:.2f} fas_ms={result['fas_ms']:.1f}"
                draw_label_box(frame, x1, ty, fas_line, fas_color, (0, 0, 0))
        else:
            draw_label_box(frame, x1, ty, "FAS: OFF", (200, 200, 200), (0, 0, 0))
        ty += 22

        # 4) Recognition line
        if result['rec_score'] is not None:
            label = f"{result['person_id']}"
            if result['person_name']:
                label += f" ({result['person_name']})"

            if self.recognizer.gallery.P == 1:
                rec_line = f"REC: {label} | {verdict} score={result['rec_score']:.3f} thr={self.config.RECOGNITION_THRESHOLD:.3f} rec_ms={result['rec_ms']:.1f}"
            else:
                b = result.get('best_score', float('nan'))
                s = result.get('second_score', float('nan'))
                rec_line = f"REC: {label} | {verdict} best={b:.3f} 2nd={s:.3f} thr={self.config.RECOGNITION_THRESHOLD:.3f} rec_ms={result['rec_ms']:.1f}"
            draw_label_box(frame, x1, ty, rec_line, box_color, (0, 0, 0))
        else:
            draw_label_box(frame, x1, ty, f"REC: {verdict}", box_color, (0, 0, 0))

    def draw_stable_result(self, frame, vote_result):
        """Draw stable voting result"""
        if vote_result['stable']:
            stable_text = f"STABLE: {vote_result['stable_id']}"
            if vote_result['stable_name']:
                stable_text += f" ({vote_result['stable_name']})"
            stable_text += f" votes={vote_result['vote_count']}/{vote_result['vote_total']}"
            stable_color = (0, 255, 0)
        else:
            stable_text = f"STABLE: UNKNOWN votes={vote_result['vote_count']}/{vote_result['vote_total']}"
            stable_color = (0, 0, 255)

        draw_label_box(frame, 10, 30, stable_text, stable_color, (0, 0, 0), scale=0.75)

    def log_stats(self):
        """Log periodic statistics"""
        now = time.perf_counter()
        if now - self.t_last_log >= self.config.LOG_EVERY_SEC:
            dt = now - self.t_last_log
            fps = self.processed_frames / max(1e-6, dt)

            avg_det = self.sum_det_ms / max(1, self.processed_frames)
            avg_fas = (self.sum_fas_ms / max(1, self.processed_frames)) if self.anti_spoof else 0.0
            avg_rec = self.sum_rec_ms / max(1, self.processed_frames)

            print(
                f"[STAT] fps={fps:.2f} | det_avg={avg_det:.1f}ms | "
                f"fas_avg={avg_fas:.1f}ms | rec_avg={avg_rec:.1f}ms"
            )

            # Reset counters
            self.processed_frames = 0
            self.sum_det_ms = 0.0
            self.sum_fas_ms = 0.0
            self.sum_rec_ms = 0.0
            self.t_last_log = now

    def log_event(self, result, vote_result):
        """Log event when face is detected"""
        if not self.config.EVENT_LOG or not result.get('has_face', False):
            return

        now_ts = time.time()

        # Build event key for change detection
        fas_r = None if result['fas_real'] is None else round(float(result['fas_real']), 3)
        rec_r = None if result['rec_score'] is None else round(float(result['rec_score']), 3)
        event_key = (result['verdict'], int(result['person_id']), fas_r, rec_r)

        # Check cooldown
        cooldown_ok = True
        if self.config.EVENT_LOG_COOLDOWN > 0:
            cooldown_ok = (now_ts - self.last_event_ts) >= self.config.EVENT_LOG_COOLDOWN

        # Check change
        change_ok = True
        if self.config.EVENT_LOG_ON_CHANGE:
            change_ok = (event_key != self.last_event_key)

        if not (cooldown_ok and change_ok):
            return

        # Build log message
        w, h = result['bbox_wh']
        det_r = round(result['det_score'], 2) if result['det_score'] else -1
        blur_r = round(result['blur'], 1) if result['blur'] else -1

        label = f"{result['person_id']}"
        if result['person_name']:
            label += f" ({result['person_name']})"

        fas_text = "OFF"
        if self.anti_spoof:
            if result['fas_real'] is None:
                fas_text = f"SKIP(every={self.config.SPOOF_EVERY})"
            else:
                fas_text = f"{'LIVE' if result['fas_pass'] else 'FAKE'} real={result['fas_real']:.2f} thr={self.config.SPOOF_THRESHOLD:.2f} fas_ms={result['fas_ms']:.1f}"

        rec_text = "N/A"
        if result['rec_score'] is not None:
            if self.recognizer.gallery.P == 1:
                rec_text = f"score={result['rec_score']:.3f} thr={self.config.RECOGNITION_THRESHOLD:.3f}"
            else:
                b = result.get('best_score', float('nan'))
                s = result.get('second_score', float('nan'))
                rec_text = f"best={b:.3f} 2nd={s:.3f} thr={self.config.RECOGNITION_THRESHOLD:.3f}"

        print(
            f"[EVENT] t={time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"det_ms={result['det_ms']:.1f} det_score={det_r} size={w}x{h} blur={blur_r} "
            f"verdict={result['verdict']} id={result['person_id']} label='{label}' "
            f"FAS={fas_text} REC={rec_text} "
            f"VOTE={vote_result['stable_id']}({vote_result['vote_count']}/{vote_result['vote_total']})"
        )

        self.last_event_ts = now_ts
        self.last_event_key = event_key

    def capture_face(self, frame, result, vote_result):
        """
        Capture face image if enabled

        Args:
            frame: Original frame (before drawing)
            result: Processing result
            vote_result: Voting result

        Returns:
            str: Path to saved file or None
        """
        if not self.face_capture or not result.get('has_face', False):
            return None

        return self.face_capture.capture(frame, result, vote_result)
