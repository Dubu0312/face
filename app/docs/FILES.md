# File Structure

Complete overview of all files in the app directory.

## 📁 Core Modules

### 1. config.py
**Purpose**: Centralized configuration
**Lines**: ~75
**Key Classes**: `Config`
**What it does**:
- Stores all default settings
- RTSP, detection, recognition, anti-spoofing configs
- **NEW**: Capture settings
- CLI argument mapping

**Key Settings**:
```python
RTSP_URL = "rtsp://192.168.192.70:8554/live.sdp"
DEVICE = "cuda"
ENABLE_ANTI_SPOOF = True
ENABLE_CAPTURE = True  # NEW
```

---

### 2. utils.py
**Purpose**: Helper utilities
**Lines**: ~120
**Key Functions**:
- `draw_label_box()` - Draw text with background
- `variance_of_laplacian()` - Blur detection
- `pick_largest_face()` - Select largest face
- `safe_mode_vote()` - Voting for stability
- `check_blur_quality()` - Quality check
- `resize_frame()` - Frame resizing

---

### 3. gallery.py
**Purpose**: Face database & matching
**Lines**: ~150
**Key Classes**: `Gallery`
**What it does**:
- Loads face templates from SQLite
- Normalizes embeddings
- Matches query embedding against gallery
- Returns match results with scores

**Key Methods**:
```python
gallery = Gallery("faces.db")
result = gallery.match(embedding, threshold=0.42)
```

---

### 4. detector.py
**Purpose**: Face detection
**Lines**: ~90
**Key Classes**: `FaceDetector`
**What it does**:
- Initializes InsightFace (buffalo_l/m/s)
- Detects faces in frame
- Extracts embeddings

**Key Methods**:
```python
detector = FaceDetector(model_name="buffalo_l")
faces = detector.detect(frame)
embedding = detector.get_embedding(face)
```

---

### 5. anti_spoofing.py
**Purpose**: Liveness detection
**Lines**: ~210
**Key Classes**: `AntiSpoofing`
**What it does**:
- Loads MiniFASNet models
- Runs multi-model ensemble
- Returns real probability

**Key Methods**:
```python
anti_spoof = AntiSpoofing(model_dir="...")
result = anti_spoof.is_real(frame, bbox, threshold=0.8)
```

---

### 6. recognizer.py
**Purpose**: Face recognition
**Lines**: ~120
**Key Classes**: `FaceRecognizer`
**What it does**:
- Combines detector + gallery
- Smooths scores with moving average
- Manages voting for stability

**Key Methods**:
```python
recognizer = FaceRecognizer(detector, gallery, config)
result = recognizer.recognize_face(face)
vote = recognizer.update_vote(person_id, verdict)
```

---

### 7. capture.py ⭐ NEW
**Purpose**: Face image capture
**Lines**: ~250
**Key Classes**: `FaceCapture`
**What it does**:
- Captures face images on detection
- Organizes by verdict (match/unknown/fake/blur/low_quality)
- Generates metadata-rich filenames
- Manages cooldown to prevent spam
- Provides statistics and cleanup

**Key Methods**:
```python
capture = FaceCapture(config)
filepath = capture.capture(frame, result, vote_result)
stats = capture.get_stats()
capture.cleanup_old_captures(days=7)
```

**Filename Format**:
```
{timestamp}_{verdict}_{person}_{scores}_{vote}.jpg
20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723_stable7-7.jpg
```

---

### 8. pipeline.py
**Purpose**: Main processing pipeline
**Lines**: ~360
**Key Classes**: `RecognitionPipeline`
**What it does**:
- Orchestrates entire workflow
- Runs quality gates
- Draws results on frame
- Logs statistics and events
- **NEW**: Calls capture module

**Processing Flow**:
```
Frame → Resize → Detect → Quality → Anti-Spoof → Recognition → Vote → Capture → Display
```

**Key Methods**:
```python
pipeline = RecognitionPipeline(config, detector, recognizer, anti_spoof, face_capture)
result = pipeline.process_frame(frame, frame_idx)
pipeline.draw_result(frame, result)
pipeline.capture_face(frame, result, vote_result)  # NEW
```

---

### 9. run.py
**Purpose**: Main entry point
**Lines**: ~240
**What it does**:
- Parses CLI arguments
- Initializes all modules
- Opens RTSP stream
- Runs main loop
- **NEW**: Initializes and uses capture

**Main Flow**:
```python
1. Parse arguments
2. Load gallery
3. Initialize detector
4. Initialize anti-spoofing
5. Initialize recognizer
6. Initialize capture  # NEW
7. Create pipeline
8. Open stream
9. Main loop
```

---

### 10. __init__.py
**Purpose**: Package initialization
**Lines**: ~25
**What it does**:
- Exports all public classes
- Defines package version

**Exports**:
```python
Config, FaceDetector, Gallery, FaceRecognizer,
AntiSpoofing, FaceCapture, RecognitionPipeline
```

---

## 📚 Documentation Files

### README.md
**Purpose**: User guide
**Lines**: ~400
**Contents**:
- Quick start
- Configuration guide
- Parameter reference
- Performance tuning
- Examples
- Troubleshooting

---

### STRUCTURE.md
**Purpose**: Architecture documentation
**Lines**: ~600
**Contents**:
- Module breakdown
- Data flow diagram
- Design principles
- Extension guide
- Performance considerations
- Testing strategy
- Learning path

---

### CAPTURE.md ⭐ NEW
**Purpose**: Capture feature documentation
**Lines**: ~450
**Contents**:
- Feature overview
- Configuration guide
- Filename format explanation
- Use cases (security, attendance, data collection)
- Statistics and reporting
- Performance impact
- Cleanup utilities
- Examples and tips

---

### QUICK_START.md ⭐ NEW
**Purpose**: Quick reference
**Lines**: ~200
**Contents**:
- One-command start
- Current defaults
- Common commands
- Output structure
- Quick tweaks
- Troubleshooting

---

### CHANGELOG.md ⭐ NEW
**Purpose**: Version history
**Lines**: ~150
**Contents**:
- Version 1.1.0: Capture feature
- Version 1.0.0: Initial modular architecture
- Feature lists
- Breaking changes

---

### FILES.md (This file)
**Purpose**: File structure overview
**Lines**: ~300
**Contents**:
- Complete file list with descriptions
- Line counts
- Key features per file

---

## 🧪 Test Files

### test_capture.py ⭐ NEW
**Purpose**: Test capture functionality
**Lines**: ~150
**What it does**:
- Creates dummy frames
- Tests all verdict types
- Shows capture statistics
- Validates filename generation

**Usage**:
```bash
python test_capture.py
```

---

### test_full.py (Legacy)
**Purpose**: Original monolithic script
**Lines**: ~625
**Status**: Kept for reference, not used
**Note**: Replaced by modular architecture

---

## 📊 File Statistics

```
Core Modules:
  config.py           ~75 lines
  utils.py           ~120 lines
  gallery.py         ~150 lines
  detector.py         ~90 lines
  anti_spoofing.py   ~210 lines
  recognizer.py      ~120 lines
  capture.py         ~250 lines  ⭐ NEW
  pipeline.py        ~360 lines
  run.py             ~240 lines
  __init__.py         ~25 lines
  ─────────────────────────────
  TOTAL            ~1,640 lines

Documentation:
  README.md          ~400 lines
  STRUCTURE.md       ~600 lines
  CAPTURE.md         ~450 lines  ⭐ NEW
  QUICK_START.md     ~200 lines  ⭐ NEW
  CHANGELOG.md       ~150 lines  ⭐ NEW
  FILES.md           ~300 lines  ⭐ NEW
  ─────────────────────────────
  TOTAL            ~2,100 lines

Test Files:
  test_capture.py    ~150 lines  ⭐ NEW
  test_full.py       ~625 lines  (legacy)
```

## 🎯 File Dependencies

```
run.py
├── config.py
├── gallery.py
├── detector.py
├── anti_spoofing.py
│   └── Silent-Face-Anti-Spoofing (external)
├── recognizer.py
│   ├── detector.py
│   ├── gallery.py
│   └── config.py
├── capture.py  ⭐ NEW
│   └── config.py
└── pipeline.py
    ├── detector.py
    ├── recognizer.py
    ├── anti_spoofing.py
    ├── capture.py  ⭐ NEW
    ├── utils.py
    └── config.py
```

## 🔄 Data Flow

```
run.py (main)
  ↓
  ├─→ Config
  ├─→ Gallery (loads from DB)
  ├─→ Detector (InsightFace)
  ├─→ AntiSpoofing (MiniFASNet)
  ├─→ Recognizer (Detector + Gallery)
  ├─→ Capture (saves images)  ⭐ NEW
  └─→ Pipeline (orchestrates all)
      ↓
      Main Loop:
        1. Read frame
        2. Detect faces (Detector)
        3. Check quality (Utils)
        4. Check liveness (AntiSpoofing)
        5. Recognize (Recognizer)
        6. Vote for stability (Recognizer)
        7. Capture image (Capture)  ⭐ NEW
        8. Draw results (Pipeline)
        9. Log stats (Pipeline)
        10. Display (OpenCV)
```

## 🆕 Version 1.1.0 Changes

**Added**:
- ✅ capture.py (250 lines)
- ✅ CAPTURE.md (450 lines)
- ✅ QUICK_START.md (200 lines)
- ✅ CHANGELOG.md (150 lines)
- ✅ FILES.md (300 lines - this file)
- ✅ test_capture.py (150 lines)

**Modified**:
- ✏️ config.py (+8 capture settings)
- ✏️ pipeline.py (+capture_face method)
- ✏️ run.py (+capture initialization)
- ✏️ __init__.py (+FaceCapture export)

**Total New Code**: ~1,500 lines (code + docs)

## 📦 Complete File List

```
app/
├── __init__.py                 # Package init
├── config.py                   # Configuration
├── utils.py                    # Utilities
├── gallery.py                  # Database & matching
├── detector.py                 # Face detection
├── anti_spoofing.py           # Liveness detection
├── recognizer.py              # Face recognition
├── capture.py                 # Face capture ⭐ NEW
├── pipeline.py                # Main pipeline
├── run.py                     # Entry point
├── test_capture.py            # Capture test ⭐ NEW
├── test_full.py               # Legacy (unused)
├── README.md                  # User guide
├── STRUCTURE.md               # Architecture docs
├── CAPTURE.md                 # Capture guide ⭐ NEW
├── QUICK_START.md             # Quick reference ⭐ NEW
├── CHANGELOG.md               # Version history ⭐ NEW
└── FILES.md                   # This file ⭐ NEW
```

**Total**: 17 files (10 Python, 7 Markdown)
