"""
Face Recognition System
A modular face recognition system with anti-spoofing
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .config import Config
from .detector import FaceDetector
from .gallery import Gallery
from .recognizer import FaceRecognizer
from .anti_spoofing import AntiSpoofing
from .capture import FaceCapture
from .pipeline import RecognitionPipeline

__all__ = [
    "Config",
    "FaceDetector",
    "Gallery",
    "FaceRecognizer",
    "AntiSpoofing",
    "FaceCapture",
    "RecognitionPipeline",
]
