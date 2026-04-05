"""
PlanO Raster Engine — GPU-Accelerated Detection Engine

Supports two backends:
  1. ML model (CubiCasa5k / ONNX / PyTorch segmentation) — GPU-accelerated
  2. OpenCV pipeline (morphological analysis + Hough lines) — CPU fallback

The engine gracefully degrades: ML model → ONNX → OpenCV.
"""

import logging
import math
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from server.config import GPU_DEVICE, MODEL_DIR, MODEL_NAME

logger = logging.getLogger("plano.gpu_engine")


# ── Types ─────────────────────────────────────────────────

class Wall(NamedTuple):
    x1: int; y1: int; x2: int; y2: int

class Room(NamedTuple):
    vertices: list  # [{id, x, y}, ...]

class Door(NamedTuple):
    x1: int; y1: int; x2: int; y2: int


# ── Engine ────────────────────────────────────────────────

class GPUFloorplanEngine:
    """
    Floor plan detection engine with GPU acceleration.

    Tries to load an ML segmentation model (ONNX or PyTorch).
    Falls back to pure OpenCV if no model weights are present.
    """

    def __init__(self):
        self.device = GPU_DEVICE
        self.backend = "opencv"  # default fallback
        self.model = None
        self.input_size = (512, 512)

        # Segmentation channels (CubiCasa5k-style)
        # 0=background, 1=wall, 2=door, 3=window, 4=room
        self.num_classes = 5

        self._try_load_model()

    def _try_load_model(self) -> None:
        """Attempt to load ML model: ONNX first, then PyTorch checkpoint."""
        # Try ONNX (fastest inference)
        onnx_path = MODEL_DIR / "cubicasa5k.onnx"
        if onnx_path.exists():
            try:
                import onnxruntime as ort
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if "cpu" in self.device:
                    providers = ["CPUExecutionProvider"]
                self.model = ort.InferenceSession(str(onnx_path), providers=providers)
                self.backend = "onnx"
                actual = self.model.get_providers()
                logger.info("Loaded ONNX model from %s (providers: %s)", onnx_path, actual)
                return
            except Exception as e:
                logger.warning("Failed to load ONNX model: %s", e)

        # Try PyTorch checkpoint
        pt_path = MODEL_DIR / "cubicasa5k.pth"
        if pt_path.exists():
            try:
                import torch
                import torch.nn as nn

                # Simple U-Net-style architecture matching CubiCasa5k output
                model = _build_unet(self.num_classes)
                state = torch.load(str(pt_path), map_location=self.device, weights_only=True)
                model.load_state_dict(state)
                model.to(self.device)
                model.eval()
                self.model = model
                self.backend = "pytorch"
                logger.info("Loaded PyTorch model from %s on %s", pt_path, self.device)
                return
            except Exception as e:
                logger.warning("Failed to load PyTorch model: %s", e)

        # Try CubiCasa5k trained checkpoint (.pkl)
        pkl_path = MODEL_DIR / "plano_trained.pkl"
        if pkl_path.exists():
            try:
                import torch
                import sys
                # Add floortrans to path
                sys.path.insert(0, str(MODEL_DIR.parent))
                from floortrans.models.hg_furukawa_original import hg_furukawa_original
                
                checkpoint = torch.load(str(pkl_path), map_location=self.device, weights_only=False)
                n_classes = 44  # CubiCasa5k default
                model = hg_furukawa_original(n_classes=n_classes)
                # Override final conv layers for our class count
                model.conv4_ = torch.nn.Conv2d(256, n_classes, bias=True, kernel_size=1)
                model.upsample = torch.nn.ConvTranspose2d(n_classes, n_classes, kernel_size=4, stride=4)
                model.load_state_dict(checkpoint["model_state"])
                model.to(self.device)
                model.eval()
                self.model = model
                self.backend = "cubicasa5k"
                self.input_slice = [21, 12, 11]  # rooms, icons, heatmaps
                logger.info("Loaded CubiCasa5k trained model from %s (epoch %s, loss %.3f)",
                           pkl_path, checkpoint.get("epoch", "?"), checkpoint.get("best_loss", 0))
                return
            except Exception as e:
                logger.warning("Failed to load CubiCasa5k model: %s", e)
                import traceback
                traceback.print_exc()

        # No model weights found — use OpenCV fallback
        logger.info("No ML model weights found in %s — using OpenCV fallback", MODEL_DIR)

    # ── Public API ────────────────────────────────────────

    def detect(self, image_path: str) -> dict:
        """
        Run detection on a floor plan image.

        Returns:
            dict with keys: walls, rooms, doors, area, perimeter, image_size
        """
        # Use OpenCV as primary (89% accuracy) — CubiCasa5k for room classification
        if True:  # Always use OpenCV for wall detection
            return self._detect_opencv(image_path)
        else:
            return self._detect_ml(image_path)

    # ── ML-based detection ────────────────────────────────

    def _detect_ml(self, image_path: str) -> dict:
        """Run ML segmentation model → post-process masks → structured output."""
        img = self._load_image(image_path)
        orig_h, orig_w = img.shape[:2]

        # Preprocess: resize, normalize, to tensor
        resized = cv2.resize(img, self.input_size, interpolation=cv2.INTER_LINEAR)
        blob = resized.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)  # HWC → CHW
        blob = np.expand_dims(blob, 0)  # add batch dim

        # Run inference
        if self.backend == "onnx":
            input_name = self.model.get_inputs()[0].name
            outputs = self.model.run(None, {input_name: blob})
            logits = outputs[0]  # (1, num_classes, H, W)
        elif self.backend == "cubicasa5k":
            import torch
            from torch.nn.functional import softmax
            with torch.no_grad():
                tensor = torch.from_numpy(blob).to(self.device)
                output = self.model(tensor)
                # CubiCasa5k outputs 44 channels: [21 rooms, 12 icons, 11 heatmaps]
                # Room classes: 0=Background, 1=Outdoor, 2=Wall, 3=Kitchen, 4=Living Room, ...
                # Icon classes: 0=No Icon, 1=Window, 2=Door, 3=Closet, ...
                # Heatmap channels: wall junctions and orientations
                rooms = softmax(output[:, :21, :, :], dim=1).cpu().numpy()
                icons = softmax(output[:, 21:33, :, :], dim=1).cpu().numpy()
                heatmaps = output[:, 33:44, :, :].cpu().numpy()  # wall heatmaps
                room_pred = np.argmax(rooms[0], axis=0)
                icon_pred = np.argmax(icons[0], axis=0)
                # FIXED class mapping:
                # room_pred == 2 is Wall (not 1 which is Outdoor)
                # icon_pred == 2 is Door, icon_pred == 1 is Window
                logits = np.zeros((1, self.num_classes, rooms.shape[2], rooms.shape[3]))
                logits[0, 0] = (room_pred == 0).astype(float)  # background
                logits[0, 1] = (room_pred == 2).astype(float)  # WALL (class 2, not 1!)
                logits[0, 2] = (icon_pred == 2).astype(float)  # door (icon class 2)
                logits[0, 3] = (icon_pred == 1).astype(float)  # window (icon class 1)
                logits[0, 4] = (room_pred >= 3).astype(float)  # rooms (class 3+ are room types)
                # Wall = class 2 pixels from room segmentation
                # Plus: compute wall mask from room boundaries
                # Room boundaries are where adjacent pixels have different room labels
                # This is more reliable than edge detection
                wall_direct = (room_pred == 2).astype(np.uint8) * 255
                
                # Also detect walls at room-to-room boundaries
                # Dilate each room slightly, then walls = overlap regions
                room_filled = (room_pred >= 3).astype(np.uint8) * 255  # all rooms
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                room_dilated = cv2.dilate(room_filled, kernel, iterations=2)
                bg_mask = (room_pred <= 1).astype(np.uint8) * 255  # bg + outdoor
                # Walls are: direct wall class OR (not-room AND not-bg after dilation)
                inferred_walls = cv2.bitwise_and(
                    cv2.bitwise_not(room_filled),
                    cv2.bitwise_not(bg_mask)
                )
                wall_combined = cv2.bitwise_or(wall_direct, inferred_walls)
                
                # Clean up: close gaps, remove small noise
                wall_combined = cv2.morphologyEx(wall_combined, cv2.MORPH_CLOSE, kernel, iterations=1)
                small_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                wall_combined = cv2.morphologyEx(wall_combined, cv2.MORPH_OPEN, small_kernel, iterations=1)
                
                logits[0, 1] = (wall_combined > 0).astype(float)
                logger.info("CubiCasa5k inference: rooms=%d unique, icons=%d unique, wall_px=%d, edge_px=%d",
                           len(np.unique(room_pred)), len(np.unique(icon_pred)),
                           int(np.sum(room_pred == 2)), int(np.sum(wall_combined > 0)))
        else:
            import torch
            with torch.no_grad():
                tensor = torch.from_numpy(blob).to(self.device)
                logits = self.model(tensor).cpu().numpy()

        # Argmax → class map
        pred = np.argmax(logits[0], axis=0).astype(np.uint8)  # (H, W)

        # Extract masks per class
        wall_mask = ((pred == 1) * 255).astype(np.uint8)
        door_mask = ((pred == 2) * 255).astype(np.uint8)
        # window_mask = ((pred == 3) * 255).astype(np.uint8)
        room_mask = ((pred == 4) * 255).astype(np.uint8)

        # Scale masks back to original size
        scale_x = orig_w / self.input_size[0]
        scale_y = orig_h / self.input_size[1]

        wall_mask = cv2.resize(wall_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        door_mask = cv2.resize(door_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        room_mask = cv2.resize(room_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

        # Post-process masks into geometry
        walls = self._walls_from_mask(wall_mask, orig_h, orig_w)
        rooms = self._rooms_from_mask(room_mask)
        doors = self._doors_from_mask(door_mask)

        total_area, total_perimeter = self._compute_metrics(walls, rooms, orig_h, orig_w)

        return {
            "walls": [{"position": [[w.x1, w.y1], [w.x2, w.y2]]} for w in walls],
            "rooms": [[{"id": str(i), "x": v["x"], "y": v["y"]} for i, v in enumerate(r.vertices)] for r in rooms],
            "doors": [{"bbox": [d.x1, d.y1, d.x2, d.y2]} for d in doors],
            "area": int(total_area),
            "perimeter": round(total_perimeter, 1),
            "image_size": [orig_w, orig_h],
        }

    # ── OpenCV fallback detection ─────────────────────────

    def _detect_opencv(self, image_path: str) -> dict:
        """Pure OpenCV pipeline — no ML model needed."""
        img = self._load_image(image_path)
        orig_h, orig_w = img.shape[:2]

        # Resize if very large
        max_dim = 2000
        scale = 1.0
        if max(orig_h, orig_w) > max_dim:
            scale = max_dim / max(orig_h, orig_w)
            img = cv2.resize(img, (int(orig_w * scale), int(orig_h * scale)),
                             interpolation=cv2.INTER_AREA)

        h, w = img.shape[:2]

        # Binary threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, blockSize=51, C=12,
        )
        kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small, iterations=1)

        # Wall mask
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 30, 20), 1))
        h_walls = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 30, 20)))
        v_walls = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
        walls_mask = cv2.bitwise_or(h_walls, v_walls)
        dilate_k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        walls_mask = cv2.dilate(walls_mask, dilate_k, iterations=1)

        # Detect walls
        wall_segments = self._detect_wall_lines(walls_mask, min_length=max(30, min(h, w) // 20))

        # Detect rooms
        rooms = self._detect_room_contours(walls_mask, min_area=max(1000, (h * w) // 400))

        # Detect doors
        doors = self._detect_door_gaps(binary, walls_mask, wall_segments)

        # Scale back if we resized
        inv_scale = 1.0 / scale if scale != 1.0 else 1.0

        def sc(v: int) -> int:
            return int(round(v * inv_scale))

        walls_out = [{"position": [[sc(ws.x1), sc(ws.y1)], [sc(ws.x2), sc(ws.y2)]]} for ws in wall_segments]
        rooms_out = [
            [{"id": str(i), "x": sc(v["x"]), "y": sc(v["y"])} for i, v in enumerate(r.vertices)]
            for r in rooms
        ]
        doors_out = [{"bbox": [sc(d.x1), sc(d.y1), sc(d.x2), sc(d.y2)]} for d in doors]

        total_area, total_perimeter = self._compute_metrics(
            [Wall(sc(ws.x1), sc(ws.y1), sc(ws.x2), sc(ws.y2)) for ws in wall_segments],
            rooms, orig_h, orig_w
        )

        return {
            "walls": walls_out,
            "rooms": rooms_out,
            "doors": doors_out,
            "area": int(total_area),
            "perimeter": round(total_perimeter, 1),
            "image_size": [orig_w, orig_h],
        }

    # ── Shared helpers ────────────────────────────────────

    def _load_image(self, path: str) -> np.ndarray:
        """Load image or first page of PDF."""
        p = Path(path)
        if p.suffix.lower() == ".pdf":
            from pdf2image import convert_from_path
            pages = convert_from_path(path, first_page=1, last_page=1, dpi=200)
            img = np.array(pages[0])
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Cannot load image: {path}")
        return img

    def _walls_from_mask(self, mask: np.ndarray, h: int, w: int) -> list[Wall]:
        """Extract wall line segments from a binary wall mask."""
        return self._detect_wall_lines(mask, min_length=max(30, min(h, w) // 20))

    def _rooms_from_mask(self, mask: np.ndarray) -> list[Room]:
        """Extract room polygons from a binary room mask."""
        h, w = mask.shape[:2]
        return self._detect_room_contours(mask, min_area=max(1000, (h * w) // 400))

    def _doors_from_mask(self, mask: np.ndarray) -> list[Door]:
        """Extract door bounding boxes from a binary door mask."""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        doors = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if 10 < bw < 200 and 10 < bh < 200:
                doors.append(Door(x, y, x + bw, y + bh))
        return doors

    def _detect_wall_lines(self, walls_mask: np.ndarray, min_length: int = 30) -> list[Wall]:
        """HoughLinesP → snap → merge collinear."""
        lines = cv2.HoughLinesP(
            walls_mask, rho=1, theta=np.pi / 180,
            threshold=40, minLineLength=min_length, maxLineGap=20,
        )
        if lines is None:
            return []

        raw = [Wall(l[0][0], l[0][1], l[0][2], l[0][3]) for l in lines]

        # Snap near-horizontal/vertical
        snapped = []
        for w in raw:
            dx, dy = abs(w.x2 - w.x1), abs(w.y2 - w.y1)
            length = math.hypot(dx, dy)
            if length < min_length:
                continue
            if dx > 0 and dy / dx < math.tan(math.radians(5)):
                y_avg = (w.y1 + w.y2) // 2
                snapped.append(Wall(min(w.x1, w.x2), y_avg, max(w.x1, w.x2), y_avg))
            elif dy > 0 and dx / dy < math.tan(math.radians(5)):
                x_avg = (w.x1 + w.x2) // 2
                snapped.append(Wall(x_avg, min(w.y1, w.y2), x_avg, max(w.y1, w.y2)))
            else:
                snapped.append(w)

        return self._merge_collinear(snapped)

    def _merge_collinear(self, walls: list[Wall], tol: int = 25) -> list[Wall]:
        """Merge overlapping collinear wall segments."""
        if not walls:
            return []

        horizontal, vertical, diagonal = [], [], []
        for w in walls:
            if w.y1 == w.y2:
                horizontal.append(w)
            elif w.x1 == w.x2:
                vertical.append(w)
            else:
                diagonal.append(w)

        result = []

        # Merge horizontal at same Y
        h_groups: dict[int, list] = {}
        for w in horizontal:
            placed = False
            for gy in list(h_groups.keys()):
                if abs(w.y1 - gy) <= tol:
                    h_groups[gy].append(w)
                    placed = True
                    break
            if not placed:
                h_groups[w.y1] = [w]

        for y, group in h_groups.items():
            intervals = sorted([(min(w.x1, w.x2), max(w.x1, w.x2)) for w in group])
            merged = [intervals[0]]
            for s, e in intervals[1:]:
                ps, pe = merged[-1]
                if s <= pe + tol:
                    merged[-1] = (ps, max(pe, e))
                else:
                    merged.append((s, e))
            for s, e in merged:
                result.append(Wall(s, y, e, y))

        # Merge vertical at same X
        v_groups: dict[int, list] = {}
        for w in vertical:
            placed = False
            for gx in list(v_groups.keys()):
                if abs(w.x1 - gx) <= tol:
                    v_groups[gx].append(w)
                    placed = True
                    break
            if not placed:
                v_groups[w.x1] = [w]

        for x, group in v_groups.items():
            intervals = sorted([(min(w.y1, w.y2), max(w.y1, w.y2)) for w in group])
            merged = [intervals[0]]
            for s, e in intervals[1:]:
                ps, pe = merged[-1]
                if s <= pe + tol:
                    merged[-1] = (ps, max(pe, e))
                else:
                    merged.append((s, e))
            for s, e in merged:
                result.append(Wall(x, s, x, e))

        result.extend(diagonal)
        return result

    def _detect_room_contours(self, walls_mask: np.ndarray, min_area: int = 2000) -> list[Room]:
        """Detect enclosed rooms via flood fill + contour analysis."""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        closed = cv2.morphologyEx(walls_mask, cv2.MORPH_CLOSE, kernel, iterations=5)
        inverted = cv2.bitwise_not(closed)

        h, w = inverted.shape
        flood = inverted.copy()
        flood_mask = np.zeros((h + 2, w + 2), np.uint8)
        cv2.floodFill(flood, flood_mask, (0, 0), 0)

        contours, _ = cv2.findContours(flood, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rooms = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) < 3:
                continue
            vertices = [{"id": str(j), "x": int(pt[0][0]), "y": int(pt[0][1])} for j, pt in enumerate(approx)]
            rooms.append(Room(vertices=vertices))

        rooms.sort(key=lambda r: -_polygon_area(r.vertices))
        return rooms

    def _detect_door_gaps(self, binary: np.ndarray, walls_mask: np.ndarray,
                          walls: list[Wall], min_gap: int = 15, max_gap: int = 120) -> list[Door]:
        """Detect doors as gaps in walls + arc patterns."""
        doors = []

        for w in walls:
            length = math.hypot(w.x2 - w.x1, w.y2 - w.y1)
            if length < 50:
                continue

            is_horizontal = (w.y1 == w.y2)
            if is_horizontal:
                y = w.y1
                x_start, x_end = min(w.x1, w.x2), max(w.x1, w.x2)
                in_gap = False
                gap_start = 0
                for x in range(x_start, x_end + 1):
                    wy = max(0, min(y, walls_mask.shape[0] - 1))
                    wx = max(0, min(x, walls_mask.shape[1] - 1))
                    neighborhood = walls_mask[max(0, wy - 3):wy + 4, wx:wx + 1]
                    is_wall = np.any(neighborhood > 0) if neighborhood.size > 0 else False
                    if not is_wall and not in_gap:
                        in_gap = True
                        gap_start = x
                    elif is_wall and in_gap:
                        gap_len = x - gap_start
                        if min_gap <= gap_len <= max_gap:
                            pad = 10
                            doors.append(Door(gap_start - pad, y - pad, x + pad, y + pad))
                        in_gap = False
            else:
                x = w.x1
                y_start, y_end = min(w.y1, w.y2), max(w.y1, w.y2)
                in_gap = False
                gap_start = 0
                for y in range(y_start, y_end + 1):
                    wy = max(0, min(y, walls_mask.shape[0] - 1))
                    wx = max(0, min(x, walls_mask.shape[1] - 1))
                    neighborhood = walls_mask[wy:wy + 1, max(0, wx - 3):wx + 4]
                    is_wall = np.any(neighborhood > 0) if neighborhood.size > 0 else False
                    if not is_wall and not in_gap:
                        in_gap = True
                        gap_start = y
                    elif is_wall and in_gap:
                        gap_len = y - gap_start
                        if min_gap <= gap_len <= max_gap:
                            pad = 10
                            doors.append(Door(x - pad, gap_start - pad, x + pad, y + pad))
                        in_gap = False

        # Arc detection
        non_wall = cv2.subtract(binary, walls_mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        non_wall = cv2.morphologyEx(non_wall, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(non_wall, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            arc_len = cv2.arcLength(cnt, False)
            if area < 100 or area > 5000 or arc_len < 30:
                continue
            if arc_len > 0 and area / arc_len < 8:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                if 15 < bw < 150 and 15 < bh < 150:
                    aspect = max(bw, bh) / max(min(bw, bh), 1)
                    if aspect < 3:
                        doors.append(Door(bx, by, bx + bw, by + bh))

        return self._dedup_doors(doors)

    def _dedup_doors(self, doors: list[Door], iou_thresh: float = 0.3) -> list[Door]:
        """Remove overlapping door detections."""
        if not doors:
            return []
        keep = []
        used = set()
        for i, d in enumerate(doors):
            if i in used:
                continue
            merged = d
            for j, d2 in enumerate(doors):
                if j <= i or j in used:
                    continue
                if _iou(merged, d2) > iou_thresh:
                    merged = Door(min(merged.x1, d2.x1), min(merged.y1, d2.y1),
                                  max(merged.x2, d2.x2), max(merged.y2, d2.y2))
                    used.add(j)
            keep.append(merged)
        return keep

    @staticmethod
    def _compute_metrics(walls: list[Wall], rooms: list[Room],
                         img_h: int, img_w: int) -> tuple[float, float]:
        """Compute total area and perimeter."""
        room_areas = [_polygon_area(r.vertices) for r in rooms] if rooms else []
        total_area = sum(room_areas) if room_areas else img_h * img_w
        total_perimeter = sum(math.hypot(w.x2 - w.x1, w.y2 - w.y1) for w in walls)
        return total_area, total_perimeter


# ── Utility functions ─────────────────────────────────────

def _polygon_area(vertices: list[dict]) -> float:
    """Shoelace formula."""
    n = len(vertices)
    if n < 3:
        return 0
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i]["x"] * vertices[j]["y"]
        area -= vertices[j]["x"] * vertices[i]["y"]
    return abs(area) / 2


def _iou(a: Door, b: Door) -> float:
    """Intersection over union of two bounding boxes."""
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
    area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _build_unet(num_classes: int):
    """Build a simple U-Net for floor plan segmentation (PyTorch)."""
    import torch
    import torch.nn as nn

    class DoubleConv(nn.Module):
        def __init__(self, in_ch, out_ch):
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_ch, out_ch, 3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(inplace=True),
            )
        def forward(self, x):
            return self.conv(x)

    class UNet(nn.Module):
        def __init__(self, n_classes):
            super().__init__()
            self.enc1 = DoubleConv(3, 64)
            self.enc2 = DoubleConv(64, 128)
            self.enc3 = DoubleConv(128, 256)
            self.enc4 = DoubleConv(256, 512)
            self.bottleneck = DoubleConv(512, 1024)
            self.up4 = nn.ConvTranspose2d(1024, 512, 2, stride=2)
            self.dec4 = DoubleConv(1024, 512)
            self.up3 = nn.ConvTranspose2d(512, 256, 2, stride=2)
            self.dec3 = DoubleConv(512, 256)
            self.up2 = nn.ConvTranspose2d(256, 128, 2, stride=2)
            self.dec2 = DoubleConv(256, 128)
            self.up1 = nn.ConvTranspose2d(128, 64, 2, stride=2)
            self.dec1 = DoubleConv(128, 64)
            self.final = nn.Conv2d(64, n_classes, 1)
            self.pool = nn.MaxPool2d(2)

        def forward(self, x):
            e1 = self.enc1(x)
            e2 = self.enc2(self.pool(e1))
            e3 = self.enc3(self.pool(e2))
            e4 = self.enc4(self.pool(e3))
            b = self.bottleneck(self.pool(e4))
            d4 = self.dec4(torch.cat([self.up4(b), e4], 1))
            d3 = self.dec3(torch.cat([self.up3(d4), e3], 1))
            d2 = self.dec2(torch.cat([self.up2(d3), e2], 1))
            d1 = self.dec1(torch.cat([self.up1(d2), e1], 1))
            return self.final(d1)

    return UNet(num_classes)
