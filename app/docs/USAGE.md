# Quick Usage Guide

## 🚀 Basic Usage

### With Display (Default)
```bash
python run.py
```

### Headless Mode (No Display)
```bash
python run.py --no-display
```

### Disable Capture
```python
# Edit config.py
ENABLE_CAPTURE = False
```

Or:
```bash
python run.py --no-capture  # (if you add this arg to run.py)
```

### Common Configurations

#### 1. Production Server (Headless + Capture)
```bash
python run.py --no-display --enable-capture
```

#### 2. Debug Mode (Display + Verbose)
```bash
python run.py --verbose --event-log
```

#### 3. High Performance (Lower quality, headless)
```bash
python run.py --no-display --skip 3 --det-size 320 --spoof-every 2
```

#### 4. High Accuracy (Higher quality, slower)
```bash
python run.py --det-size 640 --spoof-threshold 0.9 --skip 0
```

## ⚙️ Key Settings in config.py

```python
# Display
ENABLE_DISPLAY = True  # Set False for headless

# Capture
ENABLE_CAPTURE = True  # Auto-save face images
CAPTURE_DIR = "./captures"
CAPTURE_ON_MATCH = True
CAPTURE_ON_UNKNOWN = True
CAPTURE_ON_FAKE = True

# Performance
SKIP_FRAMES = 1  # Process every N+1 frames
DET_SIZE = 320  # Lower = faster
MAX_WIDTH = 960

# Anti-Spoofing
ENABLE_ANTI_SPOOF = True
SPOOF_THRESHOLD = 0.80

# Recognition
RECOGNITION_THRESHOLD = 0.42
```

## 📸 Capture Output

Saved in organized directories:
```
captures/
├── match/      # Recognized faces
├── unknown/    # Unknown faces
├── fake/       # Anti-spoofing failed
├── blur/       # Blurry faces
└── low_quality/
```

Filename format:
```
20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723.jpg
```

## 🔍 Monitoring

### View logs
```bash
python run.py --no-display 2>&1 | tee logs/app.log
```

### Check captures
```bash
ls -lh captures/match/
find captures/ -name "*.jpg" -mmin -5  # Last 5 minutes
```

## 🛑 Stopping

### Interactive Mode
- Press `q` (with display)
- Press `Ctrl+C` (headless)

### Background Process
```bash
kill -TERM <PID>
```

## 📖 More Info

- [HEADLESS.md](HEADLESS.md) - Headless mode guide
- [config.py](config.py) - All configuration options
