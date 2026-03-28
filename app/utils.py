"""
Utility functions for face recognition pipeline
"""
import cv2
import numpy as np
from collections import Counter, deque


def draw_label_box(img, x, y, text, color=(255, 255, 255), bg=(0, 0, 0), scale=0.55, thickness=2):
    """
    Draw text with background box for better visibility

    Args:
        img: Image to draw on
        x, y: Baseline-left position
        text: Text to draw
        color: Text color (BGR)
        bg: Background color (BGR)
        scale: Font scale
        thickness: Text thickness
    """
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    pad = 4
    x1, y1 = x, y - th - pad
    x2, y2 = x + tw + pad * 2, y + pad
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img.shape[1] - 1, x2)
    y2 = min(img.shape[0] - 1, y2)
    cv2.rectangle(img, (x1, y1), (x2, y2), bg, -1)
    cv2.putText(img, text, (x + pad, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def variance_of_laplacian(gray):
    """
    Calculate blur score using Laplacian variance
    Higher value = sharper image

    Args:
        gray: Grayscale image

    Returns:
        float: Blur score
    """
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def pick_largest_face(faces):
    """
    Select the largest face from detection results

    Args:
        faces: List of face objects with bbox attribute

    Returns:
        Face object with largest area, or None if empty
    """
    if not faces:
        return None
    areas = []
    for f in faces:
        x1, y1, x2, y2 = f.bbox
        areas.append(float((x2 - x1) * (y2 - y1)))
    return faces[int(np.argmax(areas))]


def safe_mode_vote(vote_hist: deque, unknown_id: int = -1):
    """
    Get most common ID from voting history

    Args:
        vote_hist: Deque of voted IDs
        unknown_id: ID to return if no votes

    Returns:
        tuple: (best_id, count)
    """
    if not vote_hist:
        return unknown_id, 0
    c = Counter(vote_hist)
    best_id, best_cnt = c.most_common(1)[0]
    return best_id, best_cnt


def check_blur_quality(image_crop, min_blur=40.0):
    """
    Check if face crop is blurry

    Args:
        image_crop: BGR image crop
        min_blur: Minimum acceptable blur score

    Returns:
        tuple: (is_good, blur_score)
    """
    if image_crop.size == 0:
        return False, 0.0

    gray = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
    blur = float(variance_of_laplacian(gray))
    return blur >= min_blur, blur


def resize_frame(frame, max_width):
    """
    Resize frame to max width while maintaining aspect ratio

    Args:
        frame: Input frame
        max_width: Maximum width

    Returns:
        Resized frame
    """
    if max_width and frame.shape[1] > max_width:
        scale = max_width / float(frame.shape[1])
        new_h = int(frame.shape[0] * scale)
        return cv2.resize(frame, (max_width, new_h), interpolation=cv2.INTER_AREA)
    return frame
