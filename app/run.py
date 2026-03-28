#!/usr/bin/env python3
"""
Face Recognition System - Main Entry Point
Combines detection, anti-spoofing, and recognition
"""
import argparse
import cv2
import sys

from config import Config
from detector import FaceDetector
from gallery import Gallery
from recognizer import FaceRecognizer
from anti_spoofing import AntiSpoofing
from capture import FaceCapture
from pipeline import RecognitionPipeline


def parse_arguments():
    """Parse command line arguments"""
    ap = argparse.ArgumentParser(description="Face Recognition with Anti-Spoofing")

    # Stream
    ap.add_argument("--rtsp", type=str, default=Config.RTSP_URL, help="RTSP stream URL")
    ap.add_argument("--db", type=str, default=Config.DB_PATH, help="Database path")

    # Device
    ap.add_argument("--device", choices=["cpu", "cuda"], default=Config.DEVICE)
    ap.add_argument("--gpu-id", type=int, default=Config.GPU_ID)

    # Detection
    ap.add_argument("--det-size", type=int, default=Config.DET_SIZE)
    ap.add_argument("--min-det-score", type=float, default=Config.MIN_DET_SCORE)
    ap.add_argument("--min-face-size", type=int, default=Config.MIN_FACE_SIZE)
    ap.add_argument("--largest-only", action="store_true", default=Config.LARGEST_ONLY)

    # Recognition
    ap.add_argument("--threshold", type=float, default=Config.RECOGNITION_THRESHOLD)
    ap.add_argument("--margin", type=float, default=Config.RECOGNITION_MARGIN)

    # Anti-spoofing
    ap.add_argument("--enable-anti-spoof", action="store_true", default=Config.ENABLE_ANTI_SPOOF)
    ap.add_argument("--anti-spoof-dir", type=str, default=Config.ANTI_SPOOF_DIR)
    ap.add_argument("--spoof-threshold", type=float, default=Config.SPOOF_THRESHOLD)
    ap.add_argument("--spoof-every", type=int, default=Config.SPOOF_EVERY)

    # Quality
    ap.add_argument("--min-blur", type=float, default=Config.MIN_BLUR)

    # Performance
    ap.add_argument("--max-width", type=int, default=Config.MAX_WIDTH)
    ap.add_argument("--skip", type=int, default=Config.SKIP_FRAMES)
    ap.add_argument("--buffersize", type=int, default=Config.RTSP_BUFFER_SIZE)

    # Stability
    ap.add_argument("--smooth-score", type=int, default=Config.SMOOTH_SCORE)
    ap.add_argument("--vote-window", type=int, default=Config.VOTE_WINDOW)
    ap.add_argument("--vote-min-count", type=int, default=Config.VOTE_MIN_COUNT)

    # Logging
    ap.add_argument("--verbose", action="store_true", default=Config.VERBOSE)
    ap.add_argument("--event-log", action="store_true", default=Config.EVENT_LOG)
    ap.add_argument("--event-log-cooldown", type=float, default=Config.EVENT_LOG_COOLDOWN)
    ap.add_argument("--event-log-on-change", action="store_true", default=Config.EVENT_LOG_ON_CHANGE)
    ap.add_argument("--log-every-sec", type=float, default=Config.LOG_EVERY_SEC)

    # UI
    ap.add_argument("--enable-display", action="store_true", default=Config.ENABLE_DISPLAY)
    ap.add_argument("--no-display", dest="enable_display", action="store_false",
                    help="Disable video display (headless mode)")

    # Capture
    ap.add_argument("--enable-capture", action="store_true", default=Config.ENABLE_CAPTURE)
    ap.add_argument("--capture-dir", type=str, default=Config.CAPTURE_DIR)
    ap.add_argument("--camera-id", type=str, default=Config.CAMERA_ID)
    ap.add_argument("--capture-cooldown", type=float, default=Config.CAPTURE_COOLDOWN)
    ap.add_argument("--capture-full-frame", action="store_true", default=Config.CAPTURE_FULL_FRAME)

    # API Event
    ap.add_argument("--enable-api-event", action="store_true", default=Config.ENABLE_API_EVENT)
    ap.add_argument("--no-api-event", dest="enable_api_event", action="store_false",
                    help="Disable API event sending")
    ap.add_argument("--api-url", type=str, default=Config.API_URL)
    ap.add_argument("--api-bearer-token", type=str, default=Config.API_BEARER_TOKEN)
    ap.add_argument("--enable-api-event-2", action="store_true", default=Config.ENABLE_API_EVENT_2)
    ap.add_argument("--no-api-event-2", dest="enable_api_event_2", action="store_false",
                    help="Disable second API event sending")
    ap.add_argument("--api2-url", type=str, default=Config.API2_URL)
    ap.add_argument("--api2-bearer-token", type=str, default=Config.API2_BEARER_TOKEN)
    ap.add_argument("--api2-photo-prefix", type=str, default=Config.API2_PHOTO_PREFIX)

    return ap.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    # Update config with args
    config = Config()
    for key, value in vars(args).items():
        if hasattr(config, key.upper()):
            setattr(config, key.upper(), value)

    print("=" * 60)
    print("Face Recognition System")
    print("=" * 60)

    # Load gallery
    print(f"\n[1/4] Loading gallery from: {config.DB_PATH}")
    try:
        gallery = Gallery(config.DB_PATH)
        print(f"      ✓ {gallery}")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        sys.exit(1)

    # Initialize detector
    print(f"\n[2/4] Initializing detector: {config.RECOGNITION_MODEL}")
    try:
        detector = FaceDetector(
            model_name=config.RECOGNITION_MODEL,
            device=config.DEVICE,
            gpu_id=config.GPU_ID,
            det_size=config.DET_SIZE,
            verbose=config.VERBOSE
        )
        print(f"      ✓ {detector}")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        sys.exit(1)

    # Initialize anti-spoofing
    anti_spoof = None
    if config.ENABLE_ANTI_SPOOF:
        print(f"\n[3/4] Initializing anti-spoofing")
        try:
            anti_spoof = AntiSpoofing(
                model_dir=config.ANTI_SPOOF_DIR,
                device=config.DEVICE,
                device_id=config.GPU_ID,
                verbose=config.VERBOSE
            )
            print(f"      ✓ {anti_spoof}")
            print(f"      ✓ Threshold: {config.SPOOF_THRESHOLD:.2f}")
        except Exception as e:
            print(f"      ✗ Error: {e}")
            print(f"      ℹ Continuing without anti-spoofing")
            anti_spoof = None
    else:
        print(f"\n[3/4] Anti-spoofing: DISABLED")

    # Initialize recognizer
    print(f"\n[4/5] Initializing recognizer")
    try:
        recognizer = FaceRecognizer(detector, gallery, config)
        print(f"      ✓ {recognizer}")
        print(f"      ✓ Threshold: {config.RECOGNITION_THRESHOLD:.3f}")
        print(f"      ✓ Margin: {config.RECOGNITION_MARGIN:.3f}")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        sys.exit(1)

    # Initialize face capture
    face_capture = None
    if config.ENABLE_CAPTURE:
        print(f"\n[5/5] Initializing face capture")
        try:
            face_capture = FaceCapture(config, id_server_map=gallery.id_server_map)
            print(f"      ✓ {face_capture}")
            print(f"      ✓ Directory: {config.CAPTURE_DIR}")
            print(f"      ✓ Camera ID: {config.CAMERA_ID}")
            print(f"      ✓ Cooldown: {config.CAPTURE_COOLDOWN}s")
            print(f"      ✓ Capture MATCH: {config.CAPTURE_ON_MATCH}")
            print(f"      ✓ Capture UNKNOWN: {config.CAPTURE_ON_UNKNOWN}")
            print(f"      ✓ Capture FAKE: {config.CAPTURE_ON_FAKE}")
            if config.ENABLE_API_EVENT:
                print(f"      ✓ API Event: ENABLED")
                print(f"      ✓ API URL: {config.API_URL}")
            else:
                print(f"      ✓ API Event: DISABLED")
            if config.ENABLE_API_EVENT_2:
                print(f"      ✓ API Event 2: ENABLED")
                print(f"      ✓ API 2 URL: {config.API2_URL}")
            else:
                print(f"      ✓ API Event 2: DISABLED")
            if config.ENABLE_API_EVENT or config.ENABLE_API_EVENT_2:
                print(f"      ✓ ID server mappings: {len(gallery.id_server_map)}")
        except Exception as e:
            print(f"      ✗ Error: {e}")
            print(f"      ℹ Continuing without capture")
            face_capture = None
    else:
        print(f"\n[5/5] Face capture: DISABLED")

    # Initialize pipeline
    print(f"\n[*] Creating pipeline")
    pipeline = RecognitionPipeline(config, detector, recognizer, anti_spoof, face_capture)

    # Open video stream
    print(f"\n[*] Opening stream: {config.RTSP_URL}")
    cap = cv2.VideoCapture(config.RTSP_URL, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, config.RTSP_BUFFER_SIZE)
    except Exception:
        pass

    if not cap.isOpened():
        print("      ✗ Cannot open RTSP stream")
        sys.exit(1)

    print("      ✓ Stream opened")
    print("\n" + "=" * 60)
    if config.ENABLE_DISPLAY:
        print("System ready! Press 'q' to quit")
    else:
        print("System ready! Running in headless mode (no display)")
        print("Press Ctrl+C to quit")
    print("=" * 60 + "\n")

    frame_idx = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("[WARN] Read failed. Reconnecting...")
                cap.release()
                cap = cv2.VideoCapture(config.RTSP_URL, cv2.CAP_FFMPEG)
                continue

            frame_idx += 1

            # Process frame
            result = pipeline.process_frame(frame, frame_idx)

            if result['skip']:
                if config.ENABLE_DISPLAY:
                    cv2.imshow(config.WINDOW_NAME, result['frame'])
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                continue

            # Update voting
            vote_result = recognizer.update_vote(
                result.get('person_id', recognizer.unknown_id),
                result.get('verdict', 'UNKNOWN')
            )

            # Capture face BEFORE drawing (get clean frame)
            if face_capture:
                # Create a copy of frame before drawing for capture
                frame_clean = frame.copy()
                captured_path = pipeline.capture_face(frame_clean, result, vote_result)

            # Draw results (now on the annotated frame)
            pipeline.draw_result(result['frame'], result)
            pipeline.draw_stable_result(result['frame'], vote_result)

            # Logging
            pipeline.log_stats()
            pipeline.log_event(result, vote_result)

            # Display (only if enabled)
            if config.ENABLE_DISPLAY:
                cv2.imshow(config.WINDOW_NAME, result['frame'])
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # Sleep a bit in headless mode to prevent CPU spinning
                import time
                time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n[*] Interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[*] Shutdown complete")


if __name__ == "__main__":
    main()
