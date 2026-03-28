"""
Face detector using InsightFace
"""
from insightface.app import FaceAnalysis


class FaceDetector:
    """Face detection and recognition using InsightFace"""

    def __init__(self, model_name="buffalo_l", device="cuda", gpu_id=0, det_size=320, verbose=False):
        """
        Initialize face detector

        Args:
            model_name: Model name (buffalo_l, buffalo_m, buffalo_s)
            device: Device to use (cuda or cpu)
            gpu_id: GPU ID
            det_size: Detection size
            verbose: Print debug info
        """
        self.model_name = model_name
        self.device = device
        self.gpu_id = gpu_id
        self.det_size = det_size
        self.verbose = verbose

        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if device == "cuda"
            else ["CPUExecutionProvider"]
        )

        try:
            self.app = FaceAnalysis(
                name=model_name,
                allowed_modules=["detection", "recognition"],
                providers=providers,
            )
            ctx_id = gpu_id if device == "cuda" else -1
            self.app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))
        except TypeError:
            # Fallback for older InsightFace versions
            self.app = FaceAnalysis(name=model_name)
            ctx_id = gpu_id if device == "cuda" else -1
            self.app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))

        if verbose:
            self._print_debug_info()

    def _print_debug_info(self):
        """Print model and provider information"""
        try:
            import onnxruntime as ort
            print("ORT get_device():", ort.get_device())
        except Exception:
            pass

        print("Loaded models:", list(self.app.models.keys()))
        for k, m in self.app.models.items():
            sess = getattr(m, "session", None)
            if sess is not None:
                print(f" - {k} providers:", sess.get_providers())

    def detect(self, frame):
        """
        Detect faces in frame

        Args:
            frame: BGR image

        Returns:
            list: List of face objects
        """
        return self.app.get(frame)

    def get_embedding(self, face):
        """
        Get normalized embedding from face object

        Args:
            face: Face object from detection

        Returns:
            np.ndarray: Normalized embedding
        """
        return face.normed_embedding

    def __repr__(self):
        return f"FaceDetector(model={self.model_name}, device={self.device}, det_size={self.det_size})"
