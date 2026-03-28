"""
Anti-spoofing module using Silent-Face-Anti-Spoofing
"""
import os
import sys
import time
import numpy as np
import torch
import torch.nn.functional as F

# Add Silent-Face-Anti-Spoofing to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SILENT_FACE_DIR = os.path.join(SCRIPT_DIR, "Silent-Face-Anti-Spoofing")
sys.path.insert(0, SILENT_FACE_DIR)

from src.model_lib.MiniFASNet import MiniFASNetV1, MiniFASNetV2, MiniFASNetV1SE, MiniFASNetV2SE
from src.data_io import transform as trans
from src.generate_patches import CropImage
from src.utility import parse_model_name, get_kernel


MODEL_MAPPING = {
    "MiniFASNetV1": MiniFASNetV1,
    "MiniFASNetV2": MiniFASNetV2,
    "MiniFASNetV1SE": MiniFASNetV1SE,
    "MiniFASNetV2SE": MiniFASNetV2SE,
}


class AntiSpoofing:
    """
    Anti-spoofing detector using Silent-Face-Anti-Spoofing
    Returns real_prob = P(class==1) using average over models
    """

    def __init__(self, model_dir: str, device: str = "cuda", device_id: int = 0, verbose: bool = False):
        """
        Initialize anti-spoofing detector

        Args:
            model_dir: Directory containing .pth model files
            device: Device to use (cuda or cpu)
            device_id: GPU ID
            verbose: Print debug info
        """
        if device == "cuda" and torch.cuda.is_available():
            self.device = torch.device(f"cuda:{device_id}")
        else:
            self.device = torch.device("cpu")

        self.model_dir = model_dir
        self.cropper = CropImage()
        self.tensorize = trans.Compose([trans.ToTensor()])
        self.models = []  # list of dict: {net, h, w, scale, crop, name}
        self._load_all(verbose=verbose)

    def _load_one(self, model_path: str):
        """Load a single model"""
        model_name = os.path.basename(model_path)
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        kernel = get_kernel(h_input, w_input)

        net = MODEL_MAPPING[model_type](conv6_kernel=kernel).to(self.device)
        sd = torch.load(model_path, map_location=self.device)

        # Strip "module." prefix if needed
        first_key = next(iter(sd.keys()))
        if "module." in first_key:
            from collections import OrderedDict
            sd = OrderedDict((k[7:], v) for k, v in sd.items())

        net.load_state_dict(sd)
        net.eval()

        crop_flag = False if scale is None else True
        use_scale = 1.0 if scale is None else float(scale)

        self.models.append({
            "name": model_name,
            "net": net,
            "h": int(h_input),
            "w": int(w_input),
            "scale": use_scale,
            "crop": crop_flag,
        })

    def _load_all(self, verbose=False):
        """Load all models from directory"""
        if not os.path.isdir(self.model_dir):
            raise FileNotFoundError(f"FAS model_dir not found: {self.model_dir}")

        pths = [
            os.path.join(self.model_dir, f)
            for f in os.listdir(self.model_dir)
            if f.endswith(".pth")
        ]
        pths.sort()

        if not pths:
            raise FileNotFoundError(f"No .pth found in: {self.model_dir}")

        for p in pths:
            self._load_one(p)

        if verbose:
            print(f"[FAS] Loaded {len(self.models)} models on {self.device}:")
            for m in self.models:
                print(f"  - {m['name']} (in={m['h']}x{m['w']}, scale={m['scale']}, crop={m['crop']})")

    @torch.no_grad()
    def predict(self, frame_bgr, bbox_xyxy):
        """
        Predict if face is real or fake

        Args:
            frame_bgr: BGR frame
            bbox_xyxy: Face bounding box (x1, y1, x2, y2)

        Returns:
            tuple: (real_prob, pred_avg, elapsed_ms)
                - real_prob: Probability of being real (0-1)
                - pred_avg: Average prediction over all models (1, 3)
                - elapsed_ms: Inference time in milliseconds
        """
        t0 = time.perf_counter()

        x1, y1, x2, y2 = [int(v) for v in bbox_xyxy]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame_bgr.shape[1] - 1, x2)
        y2 = min(frame_bgr.shape[0] - 1, y2)

        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        bbox_xywh = [x1, y1, w, h]

        pred_sum = np.zeros((1, 3), dtype=np.float32)

        for m in self.models:
            patch = self.cropper.crop(
                org_img=frame_bgr,
                bbox=bbox_xywh,
                scale=m["scale"],
                out_w=m["w"],
                out_h=m["h"],
                crop=m["crop"],
            )
            x = self.tensorize(patch).unsqueeze(0).to(self.device)
            logits = m["net"](x)
            prob = F.softmax(logits, dim=1).detach().cpu().numpy().astype(np.float32)
            pred_sum += prob

        pred_avg = pred_sum / float(len(self.models))
        real_prob = float(pred_avg[0, 1])  # class 1 == Real
        ms = (time.perf_counter() - t0) * 1000.0

        return real_prob, pred_avg, ms

    def is_real(self, frame_bgr, bbox_xyxy, threshold=0.5):
        """
        Check if face is real

        Args:
            frame_bgr: BGR frame
            bbox_xyxy: Face bounding box (x1, y1, x2, y2)
            threshold: Real probability threshold

        Returns:
            dict: {
                'is_real': bool,
                'real_prob': float,
                'elapsed_ms': float
            }
        """
        real_prob, _, elapsed_ms = self.predict(frame_bgr, bbox_xyxy)
        return {
            'is_real': real_prob >= threshold,
            'real_prob': real_prob,
            'elapsed_ms': elapsed_ms
        }

    def __repr__(self):
        return f"AntiSpoofing(models={len(self.models)}, device={self.device})"
