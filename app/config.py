"""
Configuration file for face recognition pipeline
"""
import os


class Config:
    """Default configuration for face recognition app"""

    # ===== RTSP Stream =====
    # RTSP_URL = "rtsp://192.168.192.70:8554/live.sdp"
    # RTSP_URL = "rtsp://admin:Admin12345@192.168.100.200:554/Streaming/Channels/101"
    # RTSP_URL = "rtsp://192.168.193.99:8554/cam102"
    RTSP_URL = "rtsp://192.168.100.120:8554/cam12500"
    RTSP_BUFFER_SIZE = 1

    # ===== Database =====
    DB_PATH = "faces.db"

    # ===== Device =====
    DEVICE = "cuda"  # or "cpu"
    GPU_ID = 0

    # ===== Detection =====
    DET_SIZE = 320  # Detector input size (320/480/640)
    MIN_DET_SCORE = 0.5
    MIN_FACE_SIZE = 80
    LARGEST_ONLY = True  # Only process largest face

    # ===== Recognition =====
    RECOGNITION_MODEL = "buffalo_l"  # buffalo_l, buffalo_m, buffalo_s
    RECOGNITION_THRESHOLD = 0.42
    RECOGNITION_MARGIN = 0.03

    # ===== Anti-Spoofing =====
    ENABLE_ANTI_SPOOF = True
    ANTI_SPOOF_DIR = "./Silent-Face-Anti-Spoofing/resources/anti_spoof_models"
    SPOOF_THRESHOLD = 0.80  # real_prob threshold
    SPOOF_EVERY = 5  # Run FAS every N frames

    # ===== Quality Checks =====
    MIN_BLUR = 40.0  # Laplacian variance threshold

    # ===== Performance =====
    MAX_WIDTH = 960  # Resize frame before processing
    SKIP_FRAMES = 5  # Process every (skip+1) frames

    # ===== Stability =====
    SMOOTH_SCORE = 5  # Moving average window
    VOTE_WINDOW = 7  # Voting window size
    VOTE_MIN_COUNT = 4  # Min votes to accept ID

    # ===== Logging =====
    VERBOSE = True
    EVENT_LOG = True
    EVENT_LOG_COOLDOWN = 0.5  # seconds
    EVENT_LOG_ON_CHANGE = False
    LOG_EVERY_SEC = 1.0

    # ===== UI =====
    ENABLE_DISPLAY = False  # Show video window (disable for headless/production)
    WINDOW_NAME = "Face Recognition System"

    # ===== Capture & Save =====
    ENABLE_CAPTURE = True  # Enable face capture
    CAPTURE_DIR = "/home/danglt/media_vms/human_face/original"  # Directory to save captures
    CAMERA_ID = "125"  # Camera identifier for folder structure
    CAPTURE_ON_MATCH = True  # Save on MATCH verdict
    CAPTURE_ON_UNKNOWN = False  # Save on UNKNOWN verdict
    CAPTURE_ON_FAKE = False  # Save on FAKE verdict
    CAPTURE_ON_BLUR = False  # Save on BLUR verdict
    CAPTURE_ON_LOW_QUALITY = False  # Save on LOW_QUALITY verdict
    CAPTURE_COOLDOWN = 3.0  # Min seconds between captures for same person (anti-spam)
    CAPTURE_FULL_FRAME = True  # Save full frame or just face crop

    # ===== API Event =====
    ENABLE_API_EVENT = True  # Send events to API on capture
    API_URL = "http://localhost:3000/api/face/insertEvent"
    API_BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50X2lkIjoxLCJyb2xlIjoiRWRnZSBkZXZpY2UiLCJpYXQiOjE3Njc4NDI3OTYsImV4cCI6MTc4MzM5NDc5Niwic3ViIjoic3BlY2lhbF9hY2Nlc3MifQ.KMu4ge46E5x7Kf6ramo2vBhAU6IXaM4VAxicoqz6f20"
    API_IMAGE_PREFIX = "/images/human_face/original"  # URL prefix for normal_image
    API_TIMEOUT = 5  # seconds
    ENABLE_API_EVENT_2 = True  # Send events to second API on capture
    API2_URL = "http://localhost:3000/api/time_attendance/insertEvent"
    API2_BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50X2lkIjoxLCJyb2xlIjoiRWRnZSBkZXZpY2UiLCJpYXQiOjE3Njc4NDI3OTYsImV4cCI6MTc4MzM5NDc5Niwic3ViIjoic3BlY2lhbF9hY2Nlc3MifQ.KMu4ge46E5x7Kf6ramo2vBhAU6IXaM4VAxicoqz6f20"
    API2_PHOTO_PREFIX = "/images/human_face/original"  # URL prefix for photo_url
    API2_TIMEOUT = 5  # seconds

    @classmethod
    def from_args(cls, args):
        """Create config from argparse arguments"""
        config = cls()
        for key, value in vars(args).items():
            if hasattr(config, key.upper()):
                setattr(config, key.upper(), value)
        return config

    def __repr__(self):
        attrs = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        return f"Config({attrs})"
