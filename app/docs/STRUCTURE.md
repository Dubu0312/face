# Code Structure Documentation

## 📦 Module Breakdown

### 1. **config.py** - Configuration Management
**Purpose**: Centralized configuration with sensible defaults

**Key Features**:
- All configurable parameters in one place
- Your preferred settings as defaults
- Easy to override via command line

**Main Class**:
```python
class Config:
    # Stream
    RTSP_URL = "rtsp://192.168.192.70:8554/live.sdp"

    # Device
    DEVICE = "cuda"
    GPU_ID = 0

    # Detection
    DET_SIZE = 320
    LARGEST_ONLY = True

    # Recognition
    RECOGNITION_THRESHOLD = 0.42
    RECOGNITION_MARGIN = 0.03

    # Anti-Spoofing
    ENABLE_ANTI_SPOOF = True
    SPOOF_THRESHOLD = 0.80

    # ... and more
```

---

### 2. **utils.py** - Utility Functions
**Purpose**: Reusable helper functions

**Functions**:
- `draw_label_box()` - Draw text with black background for visibility
- `variance_of_laplacian()` - Calculate blur score
- `pick_largest_face()` - Select largest face from detections
- `safe_mode_vote()` - Voting mechanism for stable results
- `check_blur_quality()` - Quality gate for blur
- `resize_frame()` - Resize frame for performance

---

### 3. **gallery.py** - Database & Face Gallery
**Purpose**: Manage face database and matching

**Main Class**: `Gallery`

**Responsibilities**:
- Load face templates from SQLite database
- Store normalized embeddings
- Match query embedding against gallery
- Return match results with scores

**Key Methods**:
```python
gallery = Gallery("faces.db")
# Loads: persons, templates, embeddings, names

result = gallery.match(embedding, threshold=0.42, margin=0.03)
# Returns: {'match': bool, 'person_id': int, 'person_name': str, 'score': float}
```

**Data Structure**:
- `templates`: (M, D) array of normalized embeddings
- `unique_pids`: (P,) array of unique person IDs
- `names`: List of person names
- `template_owner_index`: Mapping from template to person

---

### 4. **detector.py** - Face Detection
**Purpose**: Face detection using InsightFace

**Main Class**: `FaceDetector`

**Responsibilities**:
- Initialize InsightFace model (buffalo_l/m/s)
- Detect faces in frame
- Extract face embeddings
- Handle GPU/CPU execution

**Key Methods**:
```python
detector = FaceDetector(
    model_name="buffalo_l",
    device="cuda",
    det_size=320
)

faces = detector.detect(frame)
# Returns: List of face objects with bbox, landmarks, embedding

embedding = detector.get_embedding(face)
# Returns: Normalized embedding (512-dim)
```

---

### 5. **anti_spoofing.py** - Anti-Spoofing Detection
**Purpose**: Liveness detection using Silent-Face-Anti-Spoofing

**Main Class**: `AntiSpoofing`

**Responsibilities**:
- Load MiniFASNet models (.pth files)
- Crop and preprocess face patches
- Run inference on multiple models
- Average predictions for robustness

**Key Methods**:
```python
anti_spoof = AntiSpoofing(
    model_dir="./Silent-Face-Anti-Spoofing/resources/anti_spoof_models",
    device="cuda"
)

real_prob, pred_avg, elapsed_ms = anti_spoof.predict(frame, bbox)
# Returns: (real_prob, prediction_array, time_ms)

result = anti_spoof.is_real(frame, bbox, threshold=0.8)
# Returns: {'is_real': bool, 'real_prob': float, 'elapsed_ms': float}
```

**Model Ensemble**:
- Loads all .pth models from directory
- Each model: different input size, scale, crop strategy
- Averages softmax outputs
- Class 1 = Real, Class 0/2 = Fake

---

### 6. **recognizer.py** - Face Recognition
**Purpose**: Combine detector + gallery for recognition

**Main Class**: `FaceRecognizer`

**Responsibilities**:
- Extract embedding from detected face
- Match against gallery
- Smooth scores with moving average
- Maintain voting history for stability

**Key Methods**:
```python
recognizer = FaceRecognizer(detector, gallery, config)

result = recognizer.recognize_face(face)
# Returns: {
#   'match': bool,
#   'person_id': int,
#   'person_name': str,
#   'score': float,
#   'score_smooth': float,  # Moving average
#   'elapsed_ms': float
# }

vote_result = recognizer.update_vote(person_id, verdict)
# Returns: {
#   'stable': bool,
#   'stable_id': int,
#   'stable_name': str,
#   'vote_count': int,
#   'vote_total': int
# }
```

**Stability Mechanism**:
- `score_hist`: Moving average of recognition scores (deque)
- `vote_hist`: Voting window for temporal stability (deque)
- Only accept ID if it gets enough votes in window

---

### 7. **pipeline.py** - Main Processing Pipeline
**Purpose**: Orchestrate the entire detection → anti-spoofing → recognition flow

**Main Class**: `RecognitionPipeline`

**Responsibilities**:
- Process video frames
- Run detection, quality checks, anti-spoofing, recognition
- Draw results on frame
- Log statistics and events

**Processing Flow**:
```
Frame → Resize → Detect → Quality Check → Anti-Spoofing → Recognition → Vote → Display
```

**Key Methods**:
```python
pipeline = RecognitionPipeline(config, detector, recognizer, anti_spoof)

result = pipeline.process_frame(frame, frame_idx)
# Returns: {
#   'skip': bool,
#   'frame': np.array,
#   'has_face': bool,
#   'verdict': str,  # MATCH/FAKE/UNKNOWN/BLUR/LOW_QUALITY
#   'person_id': int,
#   'person_name': str,
#   'bbox': tuple,
#   'det_score': float,
#   'blur': float,
#   'fas_real': float,
#   'fas_pass': bool,
#   'rec_score': float,
#   'det_ms': float,
#   'fas_ms': float,
#   'rec_ms': float
# }

pipeline.draw_result(frame, result)
pipeline.draw_stable_result(frame, vote_result)
pipeline.log_stats()
pipeline.log_event(result, vote_result)
```

**Quality Gates** (in order):
1. **Detection Score**: `det_score >= MIN_DET_SCORE`
2. **Face Size**: `min(w,h) >= MIN_FACE_SIZE`
3. **Blur**: `variance_of_laplacian >= MIN_BLUR`
4. **Anti-Spoofing**: `real_prob >= SPOOF_THRESHOLD` (if enabled)
5. **Recognition**: `score >= RECOGNITION_THRESHOLD`

**Verdicts**:
- `LOW_QUALITY`: Failed detection/size check
- `BLUR`: Failed blur check
- `FAKE`: Failed anti-spoofing check
- `UNKNOWN`: Failed recognition threshold
- `MATCH`: Passed all checks and recognized

---

### 8. **run.py** - Main Entry Point
**Purpose**: CLI interface and application entry point

**Responsibilities**:
- Parse command line arguments
- Initialize all components
- Open RTSP stream
- Run main loop
- Handle errors and cleanup

**Flow**:
```
1. Parse args
2. Load config
3. Load gallery from DB
4. Initialize detector (InsightFace)
5. Initialize anti-spoofing (optional)
6. Initialize recognizer
7. Create pipeline
8. Open RTSP stream
9. Main loop:
   - Read frame
   - Process frame (pipeline)
   - Update voting
   - Draw results
   - Log stats/events
   - Display
10. Cleanup on exit
```

---

## 🔄 Data Flow

```
┌─────────────┐
│ RTSP Stream │
└──────┬──────┘
       │
       v
┌─────────────┐
│ Read Frame  │
└──────┬──────┘
       │
       v
┌─────────────────┐
│ Resize Frame    │  (utils.resize_frame)
└──────┬──────────┘
       │
       v
┌─────────────────┐
│ Detect Faces    │  (detector.detect)
└──────┬──────────┘
       │
       v
┌─────────────────┐
│ Pick Largest    │  (utils.pick_largest_face) [if LARGEST_ONLY]
└──────┬──────────┘
       │
       v
┌─────────────────┐
│ Quality Check   │  (utils.check_blur_quality)
│ - Det Score     │
│ - Face Size     │
│ - Blur          │
└──────┬──────────┘
       │
       v (if pass)
┌─────────────────┐
│ Anti-Spoofing   │  (anti_spoof.is_real) [if enabled]
│ - Crop patches  │
│ - Run models    │
│ - Check threshold│
└──────┬──────────┘
       │
       v (if REAL)
┌─────────────────┐
│ Recognition     │  (recognizer.recognize_face)
│ - Get embedding │  (detector.get_embedding)
│ - Match gallery │  (gallery.match)
│ - Smooth score  │
└──────┬──────────┘
       │
       v
┌─────────────────┐
│ Update Vote     │  (recognizer.update_vote)
│ - Vote history  │  (utils.safe_mode_vote)
│ - Check stability│
└──────┬──────────┘
       │
       v
┌─────────────────┐
│ Draw Results    │  (pipeline.draw_result)
│ - Bbox          │
│ - Detection info│
│ - Quality info  │
│ - FAS info      │
│ - Rec info      │
│ - Stable result │
└──────┬──────────┘
       │
       v
┌─────────────────┐
│ Log & Display   │
│ - Event log     │
│ - Stats log     │
│ - cv2.imshow    │
└─────────────────┘
```

---

## 🎯 Design Principles

### 1. **Separation of Concerns**
Each module has a single responsibility:
- `config.py` → Configuration
- `detector.py` → Face detection
- `anti_spoofing.py` → Liveness detection
- `gallery.py` → Database & matching
- `recognizer.py` → Recognition logic
- `pipeline.py` → Orchestration
- `utils.py` → Helpers
- `run.py` → Entry point

### 2. **Dependency Injection**
Components receive dependencies via constructor:
```python
recognizer = FaceRecognizer(detector, gallery, config)
pipeline = RecognitionPipeline(config, detector, recognizer, anti_spoof)
```

### 3. **Configuration Over Code**
All parameters in `config.py`, overridable via CLI:
```python
python run.py --spoof-threshold 0.9  # Override default 0.8
```

### 4. **Return Dictionaries**
Methods return dictionaries with all relevant info:
```python
{'match': True, 'person_id': 1, 'score': 0.85, 'elapsed_ms': 3.2}
```

### 5. **Optional Components**
Anti-spoofing is optional:
```python
anti_spoof = AntiSpoofing(...) if config.ENABLE_ANTI_SPOOF else None
pipeline = RecognitionPipeline(..., anti_spoof)  # Can be None
```

---

## 🔧 Extending the System

### Add New Quality Check
Edit `pipeline.py` → `_process_face()`:
```python
# After blur check
if some_new_check_fails:
    result['verdict'] = 'NEW_FAILURE_REASON'
    return result
```

### Add New Model
Edit `detector.py`:
```python
class FaceDetector:
    def __init__(self, model_name="buffalo_l", ...):
        # model_name can be: buffalo_l, buffalo_m, buffalo_s, antelopev2
```

### Add New Logging
Edit `pipeline.py` → `log_event()`:
```python
print(f"[CUSTOM] {custom_metric}")
```

### Add New Visualization
Edit `pipeline.py` → `draw_result()`:
```python
draw_label_box(frame, x, y, "New Info", color, bg)
```

---

## 📊 Performance Considerations

### Memory
- Gallery: O(M × D) where M=templates, D=512
- History: O(window_size) - small deques

### Computation
- Detection: ~10-20ms (GPU, det_size=320)
- Anti-Spoofing: ~5-10ms (GPU, 3 models)
- Recognition: ~2-5ms (matrix multiplication)
- **Total**: ~20-35ms per frame → ~30-50 FPS possible

### Optimization Points
1. **Frame skipping**: Process every Nth frame
2. **Resize**: Reduce resolution before processing
3. **FAS frequency**: Run anti-spoof every Nth processed frame
4. **Batch processing**: Process multiple faces in batch (not implemented)

---

## 🐛 Error Handling

### Graceful Degradation
- No anti-spoofing models → Continue without FAS
- Stream failure → Auto-reconnect
- No faces → Continue processing next frame

### Error Locations
- `gallery.py`: Database errors → Exit (critical)
- `detector.py`: Model load errors → Exit (critical)
- `anti_spoof.py`: Model load errors → Warning + disable FAS
- `pipeline.py`: Frame processing errors → Log + skip frame

---

## 📝 Testing Strategy

### Unit Tests (to be added)
```python
# test_gallery.py
def test_gallery_load():
    gallery = Gallery("test.db")
    assert gallery.P > 0

# test_detector.py
def test_face_detection():
    detector = FaceDetector()
    faces = detector.detect(test_image)
    assert len(faces) > 0

# test_utils.py
def test_blur_check():
    is_good, score = check_blur_quality(sharp_image, 40.0)
    assert is_good == True
```

### Integration Test
```bash
python run.py --rtsp "test_video.mp4" --verbose
```

---

## 📚 Dependencies

- **InsightFace**: Face detection & recognition
- **OpenCV**: Video I/O, image processing
- **PyTorch**: Anti-spoofing models
- **NumPy**: Array operations
- **SQLite3**: Database (built-in)

---

## 🎓 Learning Path

**For beginners**, read in this order:
1. `config.py` - Understand settings
2. `utils.py` - Learn helper functions
3. `gallery.py` - Understand face matching
4. `detector.py` - Learn face detection
5. `anti_spoofing.py` - Learn liveness detection
6. `recognizer.py` - Combine detection + matching
7. `pipeline.py` - See full workflow
8. `run.py` - Entry point

**For advanced users**:
- Modify `pipeline.py` for custom logic
- Extend `config.py` for new parameters
- Add custom quality checks
- Implement custom visualizations
