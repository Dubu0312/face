# Changelog

## Version 1.1.0 - Face Capture Feature (2026-01-09)

### ✨ New Features

#### Face Capture Module
- **Automatic face capture** when face is detected
- **Smart categorization** by verdict (MATCH, UNKNOWN, FAKE, BLUR, LOW_QUALITY)
- **Rich metadata in filename** including:
  - Timestamp with milliseconds
  - Verdict type
  - Person ID and name
  - Detection score
  - Blur score
  - Anti-spoofing score (real/fake)
  - Recognition score
  - Voting stability
- **Configurable capture rules**:
  - Enable/disable per verdict type
  - Cooldown to prevent spam
  - Full frame or face crop
  - Custom save directory
- **Auto directory structure** creation
- **Statistics tracking** per verdict type
- **Cleanup utility** for old captures

### 📝 New Files

1. **capture.py** - Face capture module
   - `FaceCapture` class with full capture logic
   - Metadata-rich filename generation
   - Cooldown management
   - Statistics and cleanup utilities

2. **CAPTURE.md** - Comprehensive documentation
   - Feature overview
   - Configuration guide
   - Use cases and examples
   - Performance considerations
   - Filename parsing utilities
   - Report generation scripts

### 🔧 Modified Files

1. **config.py**
   - Added capture configuration section
   - 8 new config parameters for capture control

2. **pipeline.py**
   - Integrated `FaceCapture` module
   - Added `capture_face()` method
   - Optional face_capture parameter

3. **run.py**
   - Import `FaceCapture`
   - Initialize face capture (step 5/5)
   - Added capture CLI arguments
   - Call capture before drawing annotations
   - Show capture stats on startup

4. **__init__.py**
   - Export `FaceCapture` class

### 🎯 Configuration Defaults

```python
ENABLE_CAPTURE = True
CAPTURE_DIR = "./captures"
CAPTURE_ON_MATCH = True
CAPTURE_ON_UNKNOWN = True
CAPTURE_ON_FAKE = True
CAPTURE_ON_BLUR = False
CAPTURE_ON_LOW_QUALITY = False
CAPTURE_COOLDOWN = 1.0
CAPTURE_FULL_FRAME = False
```

### 📊 Example Filenames

```
# MATCH (recognized)
20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723_stable7-7.jpg

# FAKE (anti-spoofing failed)
20260109_105530_123_fake_unknown_det0.95_blur78.3_fake0.35.jpg

# UNKNOWN (not recognized)
20260109_105545_789_unknown_unknown_det0.88_blur65.1_real0.92_rec0.35.jpg
```

### 🚀 Usage

```bash
# Enable with defaults
python run.py --enable-capture

# Custom configuration
python run.py \
  --enable-capture \
  --capture-dir "./my_captures" \
  --capture-cooldown 2.0 \
  --capture-full-frame
```

### 📈 Performance Impact

- Face crop: ~1-2ms overhead
- Full frame: ~3-5ms overhead
- Disk usage: ~50-100KB per face crop, ~200-400KB per full frame

---

## Version 1.0.0 - Initial Modular Architecture (2026-01-08)

### ✨ Features

- Modular architecture with 8 specialized modules
- Face detection using InsightFace (buffalo_l)
- Anti-spoofing using Silent-Face-Anti-Spoofing
- Face recognition with gallery matching
- Quality gates (detection score, face size, blur)
- Temporal stability (score smoothing, voting)
- Rich visualization with overlays
- Event logging and statistics
- Configurable via config.py or CLI

### 📝 Modules

1. **config.py** - Centralized configuration
2. **utils.py** - Utility functions
3. **gallery.py** - Database and face matching
4. **detector.py** - Face detection
5. **anti_spoofing.py** - Liveness detection
6. **recognizer.py** - Face recognition
7. **pipeline.py** - Main processing pipeline
8. **run.py** - Entry point

### 📚 Documentation

- **README.md** - User guide
- **STRUCTURE.md** - Architecture documentation
