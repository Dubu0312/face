#!/usr/bin/env python3
# test_full_verbose.py - Detection + Anti-spoofing + Recognition (verbose overlay/log + event log)

import argparse
import sqlite3
import time
import os
import sys
from collections import deque, Counter

import cv2
import numpy as np
from insightface.app import FaceAnalysis

# ---- Add Silent-Face-Anti-Spoofing to sys.path ----
SILENT_FACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Silent-Face-Anti-Spoofing")
sys.path.insert(0, SILENT_FACE_DIR)

import torch
import torch.nn.functional as F
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


# ---------------------------
# Helpers: drawing text box
# ---------------------------
def draw_label_box(img, x, y, text, color=(255, 255, 255), bg=(0, 0, 0), scale=0.55, thickness=2):
    """Draw text with background box. (x,y) is baseline-left."""
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
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def pick_largest_face(faces):
    if not faces:
        return None
    areas = []
    for f in faces:
        x1, y1, x2, y2 = f.bbox
        areas.append(float((x2 - x1) * (y2 - y1)))
    return faces[int(np.argmax(areas))]


def safe_mode_vote(vote_hist: deque, unknown_id: int = -1):
    if not vote_hist:
        return unknown_id, 0
    c = Counter(vote_hist)
    best_id, best_cnt = c.most_common(1)[0]
    return best_id, best_cnt


# ---------------------------
# Gallery loader
# ---------------------------
def load_gallery(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT person_id, COALESCE(display_name,'') FROM persons")
    person_rows = cur.fetchall()
    id_to_name = {int(pid): name for pid, name in person_rows}

    cur.execute("SELECT person_id, emb_dim, embedding FROM face_templates")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    person_ids = np.array([int(r[0]) for r in rows], dtype=np.int32)
    emb_dim = int(rows[0][1])

    embs = []
    for pid, dim, blob in rows:
        if int(dim) != emb_dim:
            raise ValueError("Inconsistent embedding dimensions in DB.")
        e = np.frombuffer(blob, dtype=np.float32)
        e = e / (np.linalg.norm(e) + 1e-12)
        embs.append(e)

    templates = np.stack(embs, axis=0).astype(np.float32)  # (M, D)

    unique_pids = np.unique(person_ids)  # (P,)
    pid_to_index = {pid: i for i, pid in enumerate(unique_pids)}
    template_owner_index = np.array([pid_to_index[pid] for pid in person_ids], dtype=np.int32)
    names = [id_to_name.get(int(pid), "") for pid in unique_pids]

    return {
        "templates": templates,
        "unique_pids": unique_pids,
        "names": names,
        "template_owner_index": template_owner_index,
    }


# ---------------------------
# InsightFace init
# ---------------------------
def init_face_app(device: str, gpu_id: int, det_size: int, verbose: bool):
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]

    try:
        app = FaceAnalysis(
            name="buffalo_l",
            allowed_modules=["detection", "recognition"],
            providers=providers,
        )
        ctx_id = gpu_id if device == "cuda" else -1
        app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))
    except TypeError:
        app = FaceAnalysis(name="buffalo_l")
        ctx_id = gpu_id if device == "cuda" else -1
        app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))

    if verbose:
        try:
            import onnxruntime as ort
            print("ORT get_device():", ort.get_device())
        except Exception:
            pass

        print("Loaded models:", list(app.models.keys()))
        for k, m in app.models.items():
            sess = getattr(m, "session", None)
            if sess is not None:
                print(f" - {k} providers:", sess.get_providers())

    return app


# ---------------------------
# Minivision FAS: preload models once
# ---------------------------
class SilentFAS:
    """
    Minivision Silent-Face-Anti-Spoofing runner.
    Returns real_prob = P(class==1) using average over models.
    """

    def __init__(self, model_dir: str, device: str = "cuda", device_id: int = 0, verbose: bool = False):
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
        model_name = os.path.basename(model_path)
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        kernel = get_kernel(h_input, w_input)

        net = MODEL_MAPPING[model_type](conv6_kernel=kernel).to(self.device)
        sd = torch.load(model_path, map_location=self.device)

        # strip "module." if needed
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
        if not os.path.isdir(self.model_dir):
            raise FileNotFoundError(f"FAS model_dir not found: {self.model_dir}")

        pths = [os.path.join(self.model_dir, f) for f in os.listdir(self.model_dir) if f.endswith(".pth")]
        pths.sort()
        if not pths:
            raise FileNotFoundError(f"No .pth found in: {self.model_dir}")

        for p in pths:
            self._load_one(p)

        if verbose:
            print(f"[FAS] Loaded {len(self.models)} models on {self.device}:")
            for m in self.models:
                print("  -", m["name"], f"(in={m['h']}x{m['w']}, scale={m['scale']}, crop={m['crop']})")

    @torch.no_grad()
    def predict(self, frame_bgr, bbox_xyxy):
        """
        bbox_xyxy: (x1,y1,x2,y2)
        return: real_prob(float), pred_avg(np(1,3)), elapsed_ms(float)
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


# ---------------------------
# Main
# ---------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtsp", type=str, required=True)
    ap.add_argument("--db", type=str, default="faces.db")

    # recognition
    ap.add_argument("--threshold", type=float, default=0.42)
    ap.add_argument("--margin", type=float, default=0.03)

    # anti-spoofing
    ap.add_argument("--enable-anti-spoof", action="store_true")
    ap.add_argument("--anti-spoof-dir", type=str, default="./Silent-Face-Anti-Spoofing/resources/anti_spoof_models")
    ap.add_argument("--spoof-threshold", type=float, default=0.80, help="real_prob threshold to pass liveness")
    ap.add_argument("--spoof-every", type=int, default=1, help="run FAS every N processed frames (1=every time)")

    # performance
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    ap.add_argument("--gpu-id", type=int, default=0)
    ap.add_argument("--det-size", type=int, default=320)
    ap.add_argument("--skip", type=int, default=2)
    ap.add_argument("--max-width", type=int, default=960)
    ap.add_argument("--buffersize", type=int, default=1)

    # quality gates
    ap.add_argument("--min-det-score", type=float, default=0.5)
    ap.add_argument("--min-face-size", type=int, default=80)
    ap.add_argument("--min-blur", type=float, default=40.0)

    # stability
    ap.add_argument("--largest-only", action="store_true")
    ap.add_argument("--smooth-score", type=int, default=5)
    ap.add_argument("--vote-window", type=int, default=7)
    ap.add_argument("--vote-min-count", type=int, default=4)

    # periodic stats
    ap.add_argument("--log-every-sec", type=float, default=1.0, help="Periodic STAT log interval (sec)")

    # event logging
    ap.add_argument("--event-log", action="store_true", help="Log a line when face exists (event)")
    ap.add_argument("--event-log-cooldown", type=float, default=0.5,
                    help="Min seconds between event logs (anti-spam). 0=disable")
    ap.add_argument("--event-log-on-change", action="store_true",
                    help="Only log when event state changes (id/verdict/fas/score changes)")

    # debug
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    gallery = load_gallery(args.db)
    if gallery is None:
        raise SystemExit("No templates in DB. Please enroll first.")

    templates = gallery["templates"]
    unique_pids = gallery["unique_pids"]
    names = gallery["names"]
    owner_idx = gallery["template_owner_index"]

    P = unique_pids.shape[0]
    M, D = templates.shape
    print(f"Loaded gallery: persons={P}, templates={M}, dim={D}")

    app = init_face_app(args.device, args.gpu_id, args.det_size, args.verbose)

    fas = None
    if args.enable_anti_spoof:
        fas = SilentFAS(
            model_dir=args.anti_spoof_dir,
            device="cuda" if args.device == "cuda" else "cpu",
            device_id=args.gpu_id,
            verbose=args.verbose,
        )
        print(f"[FAS] enabled | thr={args.spoof_threshold:.2f} | every={args.spoof_every} | device={fas.device}")

    cap = cv2.VideoCapture(args.rtsp, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, args.buffersize)
    except Exception:
        pass
    if not cap.isOpened():
        raise SystemExit("Cannot open RTSP stream.")

    score_hist = deque(maxlen=max(1, args.smooth_score))
    vote_hist = deque(maxlen=max(1, args.vote_window))
    unknown_id = -1

    # stats for periodic logging
    processed_frames = 0
    t_last_log = time.perf_counter()
    sum_det_ms = 0.0
    sum_fas_ms = 0.0
    sum_rec_ms = 0.0

    # event log state
    last_event_ts = 0.0
    last_event_key = None

    frame_idx = 0
    processed_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            print("[WARN] Read failed. Reconnecting...")
            time.sleep(0.3)
            cap.release()
            cap = cv2.VideoCapture(args.rtsp, cv2.CAP_FFMPEG)
            continue

        frame_idx += 1

        # Resize
        vis = frame
        if args.max_width and frame.shape[1] > args.max_width:
            scale = args.max_width / float(frame.shape[1])
            new_h = int(frame.shape[0] * scale)
            vis = cv2.resize(frame, (args.max_width, new_h), interpolation=cv2.INTER_AREA)

        # Skip
        if args.skip > 0 and (frame_idx % (args.skip + 1) != 0):
            cv2.imshow("full_pipeline_verbose", vis)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        processed_idx += 1
        processed_frames += 1

        # ---- DETECTOR timing ----
        t0 = time.perf_counter()
        faces = app.get(vis)
        det_ms = (time.perf_counter() - t0) * 1000.0
        sum_det_ms += det_ms

        if not faces:
            vote_hist.append(unknown_id)
            draw_label_box(vis, 10, 30, f"NO FACE | det_ms={det_ms:.1f}", (0, 0, 255), bg=(0, 0, 0), scale=0.75)
            cv2.imshow("full_pipeline_verbose", vis)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        if args.largest_only:
            faces = [pick_largest_face(faces)]

        # decided state (from ONE face in terminal mode; or last processed face if multi-face)
        decided_id = unknown_id
        decided_label = "UNKNOWN"
        decided_verdict = "UNKNOWN"
        decided_score = None

        decided_best = None
        decided_second = None

        decided_blur = None
        decided_det_score = None
        decided_bbox_wh = None

        decided_fas_real = None
        decided_fas_ms = 0.0
        decided_fas_pass = None

        # per-frame used rec_ms (for UI/log)
        last_rec_ms = 0.0

        for face in faces:
            if face is None:
                continue

            x1, y1, x2, y2 = face.bbox.astype(int)
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            decided_bbox_wh = (w, h)

            det_score = float(face.det_score)
            decided_det_score = det_score

            # default box color
            box_color = (0, 165, 255)
            cv2.rectangle(vis, (x1, y1), (x2, y2), box_color, 2)

            # --- Quality gates ---
            verdict = "UNKNOWN"
            label = "UNKNOWN"

            blur = None
            if det_score < args.min_det_score or min(w, h) < args.min_face_size:
                verdict = "LOW_QUALITY"
            else:
                crop = vis[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
                if crop.size > 0:
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    blur = float(variance_of_laplacian(gray))
                else:
                    blur = 0.0
                decided_blur = blur

                if blur < args.min_blur:
                    verdict = "BLUR"
                else:
                    # --- Anti-spoof gate ---
                    if args.enable_anti_spoof and fas is not None and (args.spoof_every <= 1 or (processed_idx % args.spoof_every == 0)):
                        real_prob, _, fas_ms = fas.predict(vis, (x1, y1, x2, y2))
                        decided_fas_real = real_prob
                        decided_fas_ms = fas_ms
                        sum_fas_ms += fas_ms
                        decided_fas_pass = real_prob >= args.spoof_threshold

                        if not decided_fas_pass:
                            verdict = "FAKE"
                        else:
                            # --- Recognition ---
                            t1 = time.perf_counter()
                            emb = face.normed_embedding.astype(np.float32)
                            sims = templates @ emb  # (M,)

                            best_per_person = np.full((P,), -1e9, dtype=np.float32)
                            np.maximum.at(best_per_person, owner_idx, sims)

                            if P == 1:
                                b_idx = 0
                                b_score = float(best_per_person[0])
                                s_score = -1e9
                            else:
                                top2_idx = np.argpartition(best_per_person, -2)[-2:]
                                top2_idx = top2_idx[np.argsort(best_per_person[top2_idx])[::-1]]
                                b_idx = int(top2_idx[0])
                                s_idx = int(top2_idx[1])
                                b_score = float(best_per_person[b_idx])
                                s_score = float(best_per_person[s_idx])

                            rec_ms = (time.perf_counter() - t1) * 1000.0
                            last_rec_ms = rec_ms
                            sum_rec_ms += rec_ms

                            decided_best = b_score
                            decided_second = s_score

                            score_hist.append(b_score)
                            b_score_smooth = float(np.mean(score_hist))
                            decided_score = b_score_smooth

                            ok_thr = b_score_smooth >= args.threshold
                            ok_margin = True if P == 1 else ((b_score_smooth - s_score) >= args.margin)

                            if ok_thr and ok_margin:
                                pid = int(unique_pids[b_idx])
                                name = names[b_idx]
                                decided_id = pid
                                decided_label = f"{pid}" + (f" ({name})" if name else "")
                                verdict = "MATCH"
                            else:
                                decided_id = unknown_id
                                decided_label = "UNKNOWN"
                                verdict = "UNKNOWN"
                    else:
                        # FAS OFF or skipped -> recognition directly
                        decided_fas_pass = None

                        t1 = time.perf_counter()
                        emb = face.normed_embedding.astype(np.float32)
                        sims = templates @ emb  # (M,)

                        best_per_person = np.full((P,), -1e9, dtype=np.float32)
                        np.maximum.at(best_per_person, owner_idx, sims)

                        if P == 1:
                            b_idx = 0
                            b_score = float(best_per_person[0])
                            s_score = -1e9
                        else:
                            top2_idx = np.argpartition(best_per_person, -2)[-2:]
                            top2_idx = top2_idx[np.argsort(best_per_person[top2_idx])[::-1]]
                            b_idx = int(top2_idx[0])
                            s_idx = int(top2_idx[1])
                            b_score = float(best_per_person[b_idx])
                            s_score = float(best_per_person[s_idx])

                        rec_ms = (time.perf_counter() - t1) * 1000.0
                        last_rec_ms = rec_ms
                        sum_rec_ms += rec_ms

                        decided_best = b_score
                        decided_second = s_score

                        score_hist.append(b_score)
                        b_score_smooth = float(np.mean(score_hist))
                        decided_score = b_score_smooth

                        ok_thr = b_score_smooth >= args.threshold
                        ok_margin = True if P == 1 else ((b_score_smooth - s_score) >= args.margin)

                        if ok_thr and ok_margin:
                            pid = int(unique_pids[b_idx])
                            name = names[b_idx]
                            decided_id = pid
                            decided_label = f"{pid}" + (f" ({name})" if name else "")
                            verdict = "MATCH"
                        else:
                            decided_id = unknown_id
                            decided_label = "UNKNOWN"
                            verdict = "UNKNOWN"

            decided_verdict = verdict

            # box color by verdict
            if verdict == "MATCH":
                box_color = (0, 255, 0)
            elif verdict == "FAKE":
                box_color = (0, 0, 255)
            elif verdict in ("LOW_QUALITY", "BLUR"):
                box_color = (0, 0, 255)
            else:
                box_color = (0, 165, 255)

            cv2.rectangle(vis, (x1, y1), (x2, y2), box_color, 3)

            # ----- Overlay lines near bbox -----
            ty = y1 - 10
            if ty < 90:
                ty = y2 + 25  # move below if not enough space

            # 1) DET line
            det_line = f"DET: score={det_score:.2f} size={w}x{h} det_ms={det_ms:.1f}"
            draw_label_box(vis, x1, ty, det_line, color=(255, 255, 255), bg=(0, 0, 0), scale=0.55, thickness=2)
            ty += 22

            # 2) Quality line
            blur_val = decided_blur if decided_blur is not None else -1.0
            q_line = f"Q: blur={blur_val:.1f} min_blur={args.min_blur:.1f} min_face={args.min_face_size}"
            draw_label_box(vis, x1, ty, q_line, color=(255, 255, 255), bg=(0, 0, 0), scale=0.55, thickness=2)
            ty += 22

            # 3) FAS line
            if args.enable_anti_spoof and fas is not None:
                if decided_fas_real is None:
                    fas_line = f"FAS: SKIP every={args.spoof_every}"
                    draw_label_box(vis, x1, ty, fas_line, color=(220, 220, 220), bg=(0, 0, 0), scale=0.55, thickness=2)
                else:
                    fas_state = "LIVE" if decided_fas_pass else "FAKE"
                    fas_color = (0, 255, 0) if decided_fas_pass else (0, 0, 255)
                    fas_line = f"FAS: {fas_state} real_prob={decided_fas_real:.2f} thr={args.spoof_threshold:.2f} fas_ms={decided_fas_ms:.1f}"
                    draw_label_box(vis, x1, ty, fas_line, color=fas_color, bg=(0, 0, 0), scale=0.55, thickness=2)
            else:
                draw_label_box(vis, x1, ty, "FAS: OFF", color=(200, 200, 200), bg=(0, 0, 0), scale=0.55, thickness=2)
            ty += 22

            # 4) REC line
            if decided_score is not None:
                if P == 1:
                    rec_line = f"REC: {decided_label} | {verdict} score={decided_score:.3f} thr={args.threshold:.3f} rec_ms={last_rec_ms:.1f}"
                else:
                    b = float(decided_best) if decided_best is not None else float("nan")
                    s = float(decided_second) if decided_second is not None else float("nan")
                    rec_line = f"REC: {decided_label} | {verdict} best={b:.3f} 2nd={s:.3f} thr={args.threshold:.3f} m={args.margin:.3f} rec_ms={last_rec_ms:.1f}"
                draw_label_box(vis, x1, ty, rec_line, color=box_color, bg=(0, 0, 0), scale=0.55, thickness=2)
            else:
                draw_label_box(vis, x1, ty, f"REC: {decided_label} | {verdict}", color=box_color, bg=(0, 0, 0), scale=0.55, thickness=2)

            if args.largest_only:
                break

        # ---- Voting (stability) ----
        # If FAKE, keep UNKNOWN (avoid stable accept)
        vote_input = decided_id if decided_verdict != "FAKE" else unknown_id
        vote_hist.append(vote_input)
        vote_id, vote_cnt = safe_mode_vote(vote_hist, unknown_id=unknown_id)

        if vote_id != unknown_id and vote_cnt >= args.vote_min_count:
            stable_name = ""
            try:
                idx = int(np.where(unique_pids == vote_id)[0][0])
                stable_name = names[idx]
            except Exception:
                stable_name = ""
            stable_text = f"STABLE: {vote_id}" + (f" ({stable_name})" if stable_name else "") + f" votes={vote_cnt}/{len(vote_hist)}"
            stable_color = (0, 255, 0)
        else:
            stable_text = f"STABLE: UNKNOWN votes={vote_cnt}/{len(vote_hist)}"
            stable_color = (0, 0, 255)

        draw_label_box(vis, 10, 30, stable_text, color=stable_color, bg=(0, 0, 0), scale=0.75, thickness=2)

        # ---- Event log (when face exists) ----
        if args.event_log:
            now_ts = time.time()

            fas_r = None if decided_fas_real is None else round(float(decided_fas_real), 3)
            rec_r = None if decided_score is None else round(float(decided_score), 3)
            det_r = None if decided_det_score is None else round(float(decided_det_score), 3)
            blur_r = None if decided_blur is None else round(float(decided_blur), 1)

            event_key = (decided_verdict, int(decided_id), fas_r, rec_r)

            cooldown_ok = True
            if args.event_log_cooldown and args.event_log_cooldown > 0:
                cooldown_ok = (now_ts - last_event_ts) >= args.event_log_cooldown

            change_ok = True
            if args.event_log_on_change:
                change_ok = (event_key != last_event_key)

            if cooldown_ok and change_ok:
                w0, h0 = decided_bbox_wh if decided_bbox_wh is not None else (-1, -1)

                fas_text = "OFF"
                if args.enable_anti_spoof:
                    if decided_fas_real is None:
                        fas_text = f"SKIP(every={args.spoof_every})"
                    else:
                        fas_text = f"{'LIVE' if decided_fas_pass else 'FAKE'} real={decided_fas_real:.2f} thr={args.spoof_threshold:.2f} fas_ms={decided_fas_ms:.1f}"

                rec_text = "N/A"
                if decided_score is not None:
                    if P == 1:
                        rec_text = f"score={decided_score:.3f} thr={args.threshold:.3f}"
                    else:
                        b = float(decided_best) if decided_best is not None else float("nan")
                        s = float(decided_second) if decided_second is not None else float("nan")
                        rec_text = f"best={b:.3f} 2nd={s:.3f} thr={args.threshold:.3f} m={args.margin:.3f}"

                print(
                    f"[EVENT] t={time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"det_ms={det_ms:.1f} det_score={det_r} size={w0}x{h0} blur={blur_r} "
                    f"verdict={decided_verdict} id={decided_id} label='{decided_label}' "
                    f"FAS={fas_text} REC={rec_text} "
                    f"VOTE={vote_id}({vote_cnt}/{len(vote_hist)})"
                )

                last_event_ts = now_ts
                last_event_key = event_key

        # ---- Periodic stats log ----
        now = time.perf_counter()
        if now - t_last_log >= args.log_every_sec:
            dt = now - t_last_log
            fps = processed_frames / max(1e-6, dt)

            avg_det = sum_det_ms / max(1, processed_frames)
            avg_fas = (sum_fas_ms / max(1, processed_frames)) if args.enable_anti_spoof else 0.0
            avg_rec = sum_rec_ms / max(1, processed_frames)

            print(
                f"[STAT] fps={fps:.2f} | det_avg={avg_det:.1f}ms | "
                f"fas_avg={avg_fas:.1f}ms | rec_avg={avg_rec:.1f}ms | "
                f"verdict={decided_verdict} | id={decided_id}"
            )

            processed_frames = 0
            sum_det_ms = 0.0
            sum_fas_ms = 0.0
            sum_rec_ms = 0.0
            t_last_log = now

        cv2.imshow("full_pipeline_verbose", vis)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()