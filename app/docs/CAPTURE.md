# Face Capture Feature

Tính năng tự động capture và lưu ảnh khuôn mặt khi phát hiện.

## 📸 Tính năng

- ✅ Tự động capture khi phát hiện khuôn mặt
- ✅ Lưu theo từng loại verdict (MATCH, UNKNOWN, FAKE, BLUR, LOW_QUALITY)
- ✅ Tên file chứa đầy đủ metadata (thời gian, verdict, ID, scores)
- ✅ Cooldown để tránh spam (mặc định 1s)
- ✅ Lựa chọn lưu full frame hoặc chỉ face crop
- ✅ Configurable - bật/tắt từng loại verdict

## 📁 Cấu trúc thư mục

```
captures/
├── match/           # Khuôn mặt nhận diện thành công
├── unknown/         # Khuôn mặt không nhận diện được
├── fake/            # Khuôn mặt giả (anti-spoofing failed)
├── blur/            # Khuôn mặt mờ
└── low_quality/     # Khuôn mặt chất lượng thấp
```

## 📋 Tên file

Format: `{timestamp}_{verdict}_{person}_{scores}_{vote}.jpg`

### Ví dụ:

#### 1. MATCH - Nhận diện thành công
```
20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723_stable7-7.jpg
```
- Timestamp: 2026-01-09 10:55:23.456
- Verdict: MATCH
- Person: ID 1 (John)
- Detection score: 0.98
- Blur score: 85.2
- Anti-spoofing: REAL 0.95
- Recognition score: 0.723
- Voting: Stable 7/7

#### 2. FAKE - Anti-spoofing failed
```
20260109_105530_123_fake_unknown_det0.95_blur78.3_fake0.35.jpg
```
- Timestamp: 2026-01-09 10:55:30.123
- Verdict: FAKE
- Person: unknown (không có ID)
- Detection score: 0.95
- Blur score: 78.3
- Anti-spoofing: FAKE 0.35 (< threshold)

#### 3. UNKNOWN - Không nhận diện được
```
20260109_105545_789_unknown_unknown_det0.88_blur65.1_real0.92_rec0.35.jpg
```
- Timestamp: 2026-01-09 10:55:45.789
- Verdict: UNKNOWN
- Person: unknown
- Detection: 0.88
- Blur: 65.1
- Anti-spoofing: REAL 0.92
- Recognition: 0.35 (< threshold)

## ⚙️ Cấu hình

### Trong config.py

```python
# Capture & Save
ENABLE_CAPTURE = True              # Bật/tắt capture
CAPTURE_DIR = "./captures"         # Thư mục lưu
CAPTURE_ON_MATCH = True            # Lưu khi MATCH
CAPTURE_ON_UNKNOWN = True          # Lưu khi UNKNOWN
CAPTURE_ON_FAKE = True             # Lưu khi FAKE
CAPTURE_ON_BLUR = False            # Lưu khi BLUR (thường không cần)
CAPTURE_ON_LOW_QUALITY = False     # Lưu khi LOW_QUALITY (thường không cần)
CAPTURE_COOLDOWN = 1.0             # Thời gian chờ giữa 2 lần capture (giây)
CAPTURE_FULL_FRAME = False         # False = chỉ crop mặt, True = full frame
```

### Command Line

```bash
# Bật capture với defaults
python run.py --enable-capture

# Tắt capture
python run.py  # (không có --enable-capture)

# Custom directory
python run.py --enable-capture --capture-dir "./my_captures"

# Capture full frame thay vì crop
python run.py --enable-capture --capture-full-frame

# Tăng cooldown để giảm số ảnh
python run.py --enable-capture --capture-cooldown 5.0
```

## 🎯 Use Cases

### 1. Security - Chỉ lưu người lạ và giả mạo
```python
CAPTURE_ON_MATCH = False      # Không lưu người đã biết
CAPTURE_ON_UNKNOWN = True     # Lưu người lạ
CAPTURE_ON_FAKE = True        # Lưu giả mạo
CAPTURE_COOLDOWN = 2.0        # Chờ 2s để tránh spam
```

### 2. Audit Trail - Lưu tất cả
```python
CAPTURE_ON_MATCH = True       # Lưu tất cả
CAPTURE_ON_UNKNOWN = True
CAPTURE_ON_FAKE = True
CAPTURE_COOLDOWN = 0.5        # Capture thường xuyên hơn
```

### 3. Training Data - Chỉ lưu ảnh chất lượng tốt
```python
CAPTURE_ON_MATCH = True
CAPTURE_ON_UNKNOWN = True
CAPTURE_ON_FAKE = False       # Bỏ ảnh giả
CAPTURE_ON_BLUR = False       # Bỏ ảnh mờ
CAPTURE_ON_LOW_QUALITY = False
MIN_BLUR = 60.0               # Tăng threshold blur
```

## 📊 Statistics

Xem thống kê số ảnh đã capture:

```python
from capture import FaceCapture

capture = FaceCapture(config)
stats = capture.get_stats()
print(stats)
# {'match': 150, 'unknown': 25, 'fake': 8, 'blur': 0, 'low_quality': 0, 'total': 183}
```

## 🧹 Cleanup

Xóa ảnh cũ hơn N ngày:

```python
capture.cleanup_old_captures(days=7)  # Xóa ảnh > 7 ngày
```

Hoặc thêm vào main loop của run.py:

```python
# Cleanup mỗi giờ
if time.time() % 3600 < 1:
    face_capture.cleanup_old_captures(days=7)
```

## 🔍 Phân tích ảnh đã capture

### Parse filename để extract metadata

```python
import re
from datetime import datetime

def parse_capture_filename(filename):
    """
    Parse capture filename to extract metadata

    Example: 20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723.jpg
    """
    # Remove extension
    name = filename.replace('.jpg', '')
    parts = name.split('_')

    # Timestamp
    ts_str = f"{parts[0]}_{parts[1]}_{parts[2]}"
    timestamp = datetime.strptime(ts_str, "%Y%m%d_%H%M%S_%f")

    # Verdict
    verdict = parts[3]

    # Person ID/name
    person = '_'.join([p for p in parts[4:] if p.startswith('id') or p.isalpha()])

    # Scores
    scores = {}
    for part in parts:
        if part.startswith('det'):
            scores['det'] = float(part[3:])
        elif part.startswith('blur'):
            scores['blur'] = float(part[4:])
        elif part.startswith('real') or part.startswith('fake'):
            key = 'fas_real' if part.startswith('real') else 'fas_fake'
            scores[key] = float(part[4:])
        elif part.startswith('rec'):
            scores['rec'] = float(part[3:])

    return {
        'timestamp': timestamp,
        'verdict': verdict,
        'person': person,
        'scores': scores
    }

# Usage
info = parse_capture_filename("20260109_105523_456_match_id1_John_det0.98_blur85.2_real0.95_rec0.723.jpg")
print(info)
```

### Tìm tất cả ảnh của một người

```bash
# Tìm tất cả ảnh của ID 1
find captures/ -name "*_id1_*"

# Tìm tất cả ảnh FAKE
find captures/fake/ -name "*.jpg"

# Đếm số ảnh MATCH trong ngày hôm nay
find captures/match/ -name "20260109_*.jpg" | wc -l
```

## 🚀 Performance Impact

### Ảnh hưởng đến FPS:

- **Face crop** (default): ~1-2ms overhead
- **Full frame**: ~3-5ms overhead (tùy resolution)

### Disk space:

- Face crop: ~50-100KB/ảnh
- Full frame (960x540): ~200-400KB/ảnh

### Ước tính:

```
Nếu capture 1 ảnh/giây:
- Face crop: ~86MB/ngày, ~2.5GB/tháng
- Full frame: ~260MB/ngày, ~7.8GB/tháng
```

## 💡 Tips

### 1. Giảm disk usage
```python
CAPTURE_COOLDOWN = 5.0          # Capture ít hơn
CAPTURE_FULL_FRAME = False      # Chỉ crop mặt
```

### 2. Tăng quality
```python
MIN_BLUR = 60.0                 # Chỉ lưu ảnh sharp
MIN_DET_SCORE = 0.7             # Detection confidence cao
```

### 3. Auto cleanup
Thêm cronjob để xóa ảnh cũ:
```bash
# Xóa ảnh > 30 ngày mỗi đêm 2am
0 2 * * * find /path/to/captures -name "*.jpg" -mtime +30 -delete
```

### 4. Backup captures
```bash
# Sync to remote server
rsync -avz ./captures/ user@server:/backup/captures/

# Archive by month
tar -czf captures_2026-01.tar.gz captures/
```

## 🎨 Visualize captures

### Tạo timelapse video từ captures

```bash
# Tạo video từ MATCH captures
ffmpeg -framerate 2 -pattern_type glob -i 'captures/match/*.jpg' \
  -c:v libx264 -pix_fmt yuv420p timelapse_match.mp4

# Tạo video từ FAKE captures
ffmpeg -framerate 2 -pattern_type glob -i 'captures/fake/*.jpg' \
  -c:v libx264 -pix_fmt yuv420p timelapse_fake.mp4
```

### Generate report

```python
import os
from collections import Counter
from datetime import datetime

def generate_capture_report(capture_dir):
    stats = {
        'by_verdict': Counter(),
        'by_person': Counter(),
        'by_hour': Counter(),
        'total': 0
    }

    for subdir in ['match', 'unknown', 'fake', 'blur', 'low_quality']:
        path = os.path.join(capture_dir, subdir)
        if not os.path.exists(path):
            continue

        for filename in os.listdir(path):
            if not filename.endswith('.jpg'):
                continue

            stats['total'] += 1
            stats['by_verdict'][subdir] += 1

            # Parse filename
            parts = filename.split('_')

            # Hour
            hour = parts[1][:2]
            stats['by_hour'][hour] += 1

            # Person
            if 'id' in filename:
                person_parts = [p for p in parts if p.startswith('id')]
                if person_parts:
                    stats['by_person'][person_parts[0]] += 1

    return stats

# Usage
stats = generate_capture_report('./captures')
print(f"Total captures: {stats['total']}")
print(f"\nBy verdict:")
for verdict, count in stats['by_verdict'].most_common():
    print(f"  {verdict}: {count}")
print(f"\nBy person:")
for person, count in stats['by_person'].most_common(10):
    print(f"  {person}: {count}")
print(f"\nBy hour:")
for hour in sorted(stats['by_hour'].keys()):
    print(f"  {hour}:00 - {stats['by_hour'][hour]} captures")
```

## 📝 Examples

### Example 1: Security Camera

```bash
python run.py \
  --enable-capture \
  --capture-dir "/mnt/storage/security/captures" \
  --capture-on-match False \
  --capture-on-unknown True \
  --capture-on-fake True \
  --capture-cooldown 3.0
```

### Example 2: Attendance System

```bash
python run.py \
  --enable-capture \
  --capture-dir "./attendance/$(date +%Y-%m-%d)" \
  --capture-on-match True \
  --capture-on-unknown False \
  --capture-on-fake False \
  --capture-cooldown 10.0 \
  --capture-full-frame
```

### Example 3: Data Collection

```bash
python run.py \
  --enable-capture \
  --capture-dir "./dataset/raw" \
  --capture-on-match True \
  --capture-on-unknown True \
  --capture-on-fake True \
  --capture-cooldown 0.5 \
  --min-blur 70.0
```
