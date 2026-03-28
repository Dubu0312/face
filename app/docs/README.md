# Face Recognition System with Anti-Spoofing

Complete face recognition system with anti-spoofing detection and automatic face capture.

## ✨ Features

- ✅ **Face Detection** - InsightFace buffalo_l model
- ✅ **Anti-Spoofing** - Silent-Face-Anti-Spoofing (MiniFASNet)
- ✅ **Face Recognition** - Gallery matching with voting
- ✅ **Auto Capture** - Save detected faces with metadata
- ✅ **Headless Mode** - Run without display for production
- ✅ **Quality Gates** - Detection score, blur, face size checks
- ✅ **Stability** - Temporal smoothing and voting
- ✅ **Full Logging** - Events and statistics

## 🚀 Quick Start

```bash
cd /home/dubu/manh/face/app
python run.py
```

**That's it!** All settings are configured in `config.py`.

## 📸 Output

### Display (Default)
- Real-time video with annotations
- Detection, quality, anti-spoofing, recognition info
- Press `q` to quit

### Captures (Auto-saved)
```
captures/
├── match/      # Recognized faces
├── unknown/    # Unknown faces
├── fake/       # Anti-spoofing failed
└── ...
```

Filename example:
```
20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723.jpg
│               │     │        └─ Metadata: scores, person info
│               │     └────────── Verdict: match/unknown/fake
│               └──────────────── Person: id1 (John)
└──────────────────────────────── Timestamp: 2026-01-09 10:55:23.456
```

## ⚙️ Configuration

### config.py (Defaults)

```python
# Stream
RTSP_URL = "rtsp://192.168.192.70:8554/live.sdp"
DB_PATH = "faces.db"

# Device
DEVICE = "cuda"
GPU_ID = 0

# Display
ENABLE_DISPLAY = True  # Set False for headless mode

# Capture
ENABLE_CAPTURE = True
CAPTURE_DIR = "./captures"
CAPTURE_ON_MATCH = True
CAPTURE_ON_UNKNOWN = True
CAPTURE_ON_FAKE = True
CAPTURE_COOLDOWN = 1.0  # seconds

# Anti-Spoofing
ENABLE_ANTI_SPOOF = True
SPOOF_THRESHOLD = 0.80

# Recognition
RECOGNITION_THRESHOLD = 0.42
```

### Command Line

```bash
# Headless mode (no display)
python run.py --no-display

# Custom settings
python run.py --spoof-threshold 0.9 --det-size 640

# High performance
python run.py --skip 3 --det-size 320 --no-display
```

## 🎯 Use Cases

### 1. Development (With Display)
```bash
python run.py
```

### 2. Production Server (Headless + Capture)
```bash
python run.py --no-display --enable-capture
```

### 3. Security (Only save unknown/fake)
```python
# Edit config.py
CAPTURE_ON_MATCH = False
CAPTURE_ON_UNKNOWN = True
CAPTURE_ON_FAKE = True
```

### 4. Docker/Systemd Service
```bash
# See HEADLESS.md for complete examples
python run.py --no-display
```

## 📚 Documentation

- **[USAGE.md](USAGE.md)** - Quick usage guide
- **[HEADLESS.md](HEADLESS.md)** - Headless mode / production deployment
- **[config.py](config.py)** - All configuration options

## 🔧 Modules

```
app/
├── config.py           # Configuration
├── detector.py         # Face detection
├── anti_spoofing.py    # Anti-spoofing
├── recognizer.py       # Face recognition
├── gallery.py          # Database matching
├── capture.py          # Face capture
├── pipeline.py         # Main pipeline
├── run.py              # Entry point
└── utils.py            # Utilities
```

## 📊 Performance

- **FPS**: 25-35 (with display), 30-40 (headless)
- **Detection**: ~10-20ms (GPU, det_size=320)
- **Anti-Spoofing**: ~5-10ms (GPU)
- **Recognition**: ~2-5ms
- **Capture**: ~1-2ms (face crop), ~3-5ms (full frame)

## 🐳 Docker Example

```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "run.py", "--no-display"]
```

## 🔧 Systemd Service

```ini
[Unit]
Description=Face Recognition System

[Service]
ExecStart=/usr/bin/python3 /path/to/app/run.py --no-display
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📝 Logs

```bash
# Console output
[STAT] fps=15.23 | det_avg=12.1ms | fas_avg=8.3ms | rec_avg=3.2ms
[EVENT] verdict=MATCH id=1 label='1 (John)' FAS=LIVE real=0.95 REC=score=0.723
[CAPTURE] Saved: 20260109_105523_456_match_id1_John_...jpg
```

## 🛑 Stopping

- **With display**: Press `q`
- **Headless**: Press `Ctrl+C`

## 🎉 Summary

**One command to run:**
```bash
python run.py
```

**Headless mode:**
```bash
python run.py --no-display
```

**Customize in:** `config.py`

That's all you need! 🚀
