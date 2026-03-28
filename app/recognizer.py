"""
Face recognizer combining detector and gallery
"""
import time
import numpy as np
from collections import deque


class FaceRecognizer:
    """Face recognition pipeline"""

    def __init__(self, detector, gallery, config):
        """
        Initialize recognizer

        Args:
            detector: FaceDetector instance
            gallery: Gallery instance
            config: Config instance
        """
        self.detector = detector
        self.gallery = gallery
        self.config = config

        # Stability tracking
        self.score_hist = deque(maxlen=max(1, config.SMOOTH_SCORE))
        self.vote_hist = deque(maxlen=max(1, config.VOTE_WINDOW))
        self.unknown_id = -1

    def recognize_face(self, face):
        """
        Recognize a single face

        Args:
            face: Face object from detector

        Returns:
            dict: Recognition result with timing
        """
        t0 = time.perf_counter()

        # Get embedding
        embedding = self.detector.get_embedding(face).astype(np.float32)

        # Match against gallery
        result = self.gallery.match(
            embedding,
            threshold=self.config.RECOGNITION_THRESHOLD,
            margin=self.config.RECOGNITION_MARGIN
        )

        # Add to smoothing history
        self.score_hist.append(result['best_score'])
        score_smooth = float(np.mean(self.score_hist))

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return {
            'match': result['match'],
            'person_id': result['person_id'],
            'person_name': result['person_name'],
            'score': result['score'],
            'score_smooth': score_smooth,
            'best_score': result['best_score'],
            'second_score': result['second_score'],
            'elapsed_ms': elapsed_ms
        }

    def update_vote(self, person_id, verdict):
        """
        Update voting history for stability

        Args:
            person_id: Person ID to vote for
            verdict: Current verdict (avoid voting FAKE as stable)

        Returns:
            dict: Voting result
        """
        # Don't vote for FAKE faces
        vote_input = person_id if verdict != "FAKE" else self.unknown_id
        self.vote_hist.append(vote_input)

        from utils import safe_mode_vote
        vote_id, vote_cnt = safe_mode_vote(self.vote_hist, unknown_id=self.unknown_id)

        is_stable = (
            vote_id != self.unknown_id and
            vote_cnt >= self.config.VOTE_MIN_COUNT
        )

        # Get name for stable result
        stable_name = ""
        if is_stable:
            try:
                idx = int(np.where(self.gallery.unique_pids == vote_id)[0][0])
                stable_name = self.gallery.names[idx]
            except Exception:
                stable_name = ""

        return {
            'stable': is_stable,
            'stable_id': vote_id if is_stable else self.unknown_id,
            'stable_name': stable_name,
            'vote_count': vote_cnt,
            'vote_total': len(self.vote_hist)
        }

    def reset_history(self):
        """Reset smoothing and voting history"""
        self.score_hist.clear()
        self.vote_hist.clear()

    def __repr__(self):
        return f"FaceRecognizer(gallery={self.gallery})"
