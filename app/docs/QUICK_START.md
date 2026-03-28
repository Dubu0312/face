# Quick Start Guide

## 🚀 Chạy ngay với defaults

```bash
cd /home/dubu/manh/face/app
python run.py
```

Tất cả settings đã được cấu hình sẵn trong [config.py](config.py)!

---

## ⚙️ Settings hiện tại (Defaults)

### 📹 Stream
- RTSP: `rtsp://192.168.192.70:8554/live.sdp`
- Database: `faces.db`

### 🖥️ Device
- Device: **CUDA**
- GPU ID: **0**

### 🔍 Detection
- Size: **320** (fast)
- Largest only: **True** (terminal mode)

### 🎭 Recognition
- Model: **buffalo_l** (best accuracy)
- Threshold: **0.42**
- Margin: **0.03**

### 🛡️ Anti-Spoofing
- **ENABLED**
- Threshold: **0.80**
- Every frame: **1**

### 📸 Capture
- **ENABLED**
- Directory: `./captures`
- Capture MATCH: **True**
- Capture UNKNOWN: **True**
- Capture FAKE: **True**
- Cooldown: **1.0s**

### 📊 Logging
- Verbose: **True**
- Event log: **True**

---

## 🎯 Common Commands

### 1. Chạy mặc định (như command cũ của bạn)
```bash
python run.py
```

### 2. Tắt capture
```bash
python run.py --capture-dir "/path/to/captures"
```

### 3. Tăng độ chính xác anti-spoofing
```bash
python run.py --spoof-threshold 0.9
```

### 4. Giảm FPS để tăng tốc độ
```bash
python run.py --skip 3 --det-size 320
```

### 5. Chạy không có anti-spoofing
```bash
# Edit config.py:
ENABLE_ANTI_SPOOF = False
```

### 6. Capture full frame thay vì crop
```bash
python run.py --capture-full-frame
```

---

## 📁 Output Structure

```
app/
├── captures/               # 📸 Captured faces
│   ├── match/             # Recognized faces
│   ├── unknown/           # Unknown faces
│   ├── fake/              # Spoofing attempts
│   ├── blur/              # Blurry faces
│   └── low_quality/       # Low quality detections
├── faces.db               # Face database
└── run.py                 # Main script
```

---

## 🎨 What You'll See

### On Screen:
```
┌─────────────────────────────────────────────┐
│ STABLE: 1 (John) votes=7/7                  │ ← Top: Stable result
├─────────────────────────────────────────────┤
│                                             │
│   ┌──────────────────┐                      │
│   │                  │                      │
│   │   👤 Face         │  ← Bounding box     │
│   │                  │                      │
│   └──────────────────┘                      │
│   DET: score=0.98 size=150x180 det_ms=12.1 │ ← Detection
│   Q: blur=85.2 min_blur=40.0                │ ← Quality
│   FAS: LIVE real_prob=0.95 thr=0.80 ...    │ ← Anti-spoof
│   REC: 1 (John) | MATCH score=0.723 ...    │ ← Recognition
│                                             │
└─────────────────────────────────────────────┘
```

### In Terminal:
```
[STAT] fps=15.23 | det_avg=12.1ms | fas_avg=8.3ms | rec_avg=3.2ms
[EVENT] t=2026-01-09 10:55:23 ... verdict=MATCH id=1 label='1 (John)' ...
[CAPTURE] Saved: 20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723.jpg
```

---

## 🔧 Quick Tweaks

### Faster (sacrifice accuracy)
```python
# In config.py
DET_SIZE = 320
SKIP_FRAMES = 3
SPOOF_EVERY = 2
```

### More Accurate (slower)
```python
# In config.py
DET_SIZE = 640
SKIP_FRAMES = 0
SPOOF_THRESHOLD = 0.9
RECOGNITION_THRESHOLD = 0.5
```

### Less Disk Usage
```python
# In config.py
CAPTURE_COOLDOWN = 5.0
CAPTURE_ON_BLUR = False
CAPTURE_ON_LOW_QUALITY = False
```

---

## 🐛 Troubleshooting

### "Cannot open RTSP stream"
- Check RTSP URL: `rtsp://192.168.192.70:8554/live.sdp`
- Test with VLC first
- Check network connectivity

### "No module named 'src.model_lib'"
```bash
# Make sure you're in the right directory
cd /home/dubu/manh/face/app

# Check Silent-Face-Anti-Spoofing exists
ls ../Silent-Face-Anti-Spoofing/
```

### Low FPS
```bash
# Reduce processing load
python run.py --skip 2 --det-size 320 --spoof-every 2
```

### Too many captures
```bash
# Increase cooldown or disable some verdicts
python run.py --capture-cooldown 3.0

# Or edit config.py:
CAPTURE_ON_BLUR = False
CAPTURE_ON_LOW_QUALITY = False
```

---

## 📚 More Info

- [README.md](README.md) - Full documentation
- [CAPTURE.md](CAPTURE.md) - Capture feature guide
- [STRUCTURE.md](STRUCTURE.md) - Code architecture
- [CHANGELOG.md](CHANGELOG.md) - Version history

---

## 🎯 Your Original Command

```bash
python test_full.py \
  --rtsp "rtsp://192.168.192.70:8554/live.sdp" \
  --db faces.db \
  --largest-only \
  --device cuda \
  --gpu-id 0 \
  --det-size 320 \
  --max-width 960 \
  --enable-anti-spoof \
  --anti-spoof-dir "./Silent-Face-Anti-Spoofing/resources/anti_spoof_models" \
  --spoof-threshold 0.8 \
  --verbose \
  --event-log
```

### Now becomes:
```bash
python run.py
```

All those settings are now defaults in `config.py` + bonus capture feature! 🎉
