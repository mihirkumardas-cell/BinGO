"""
CleanTrack AI — YOLOv8 Waste Classifier

Dataset sources:
  Primary: Kaggle "Garbage Classification" by Mostafa Mohamed
  URL: https://www.kaggle.com/datasets/asdasdasasdas/garbage-classification
  Classes: cardboard, glass, metal, paper, plastic, trash (6 classes, ~2,527 images)

  Secondary: TACO (Trash Annotations in Context)
  URL: http://tacoDataset.org/
  Classes: 60 categories, COCO format, ~1,500 images with bounding boxes

Model:
  Base: YOLOv8n (nano) — smallest YOLO variant for low-resource cloud deployment
  Fine-tuned on: TACO (detection) + Kaggle GC (classification head)
  Weights: /app/weights/cleantrack_yolov8n.pt
  Fallback: yolov8n.pt (COCO pretrained) with class remapping

Class mapping from YOLO output → CleanTrack WasteType:
  bottle → plastic | can → metal | cardboard_box → cardboard
  glass_bottle → glass | plastic_bag → plastic | food_waste → organic
  etc.
"""
import os
import time
from pathlib import Path
from typing import Optional, Tuple

import structlog

logger = structlog.get_logger()

# Map YOLO class names → CleanTrack waste types
# Source: TACO 60-class taxonomy + Kaggle GC labels
YOLO_TO_WASTE_TYPE = {
    # Non-waste / Human / Environment
    "person": "clean", "hand": "clean", "human": "clean",
    # Plastic
    "plastic_bag": "plastic", "plastic_bottle": "plastic", "plastic_cup": "plastic",
    "plastic_straw": "plastic", "plastic_utensil": "plastic", "plastic": "plastic",
    # Metal
    "aluminium_can": "metal", "tin_can": "metal", "metal": "metal",
    # Glass
    "glass_bottle": "glass", "glass": "glass",
    # Paper / Cardboard
    "cardboard": "cardboard", "cardboard_box": "cardboard", "paper": "paper",
    "newspaper": "paper", "paper_cup": "paper",
    # Organic
    "food_waste": "organic", "organic": "organic",
    # Hazardous
    "battery": "hazardous", "light_bulb": "hazardous", "hazardous": "hazardous",
    # Kaggle GC direct labels
    "trash": "mixed",
    # COCO fallback remapping
    "bottle": "plastic", "cup": "paper", "bowl": "mixed",
    "book": "paper", "scissors": "metal", "cell phone": "hazardous",
}

DEFAULT_WASTE_TYPE = "clean"


class WasteClassifier:
    """YOLOv8-based waste detector and classifier."""

    def __init__(self, model_path: str = "./weights/cleantrack_yolov8n.pt"):
        self.model_path = model_path
        self.model = None
        self.model_version = "unloaded"
        self._load_model()

    def _load_model(self) -> None:
        """Load YOLOv8 model. Falls back to COCO pretrained if custom weights missing."""
        from ultralytics import YOLO

        custom_path = Path(self.model_path)
        if custom_path.exists():
            logger.info("loading_custom_yolo_weights", path=str(custom_path))
            self.model = YOLO(str(custom_path))
            self.model_version = f"cleantrack-yolov8n:{custom_path.stat().st_mtime:.0f}"
        else:
            logger.warning(
                "custom_weights_not_found",
                path=str(custom_path),
                fallback="yolov8n.pt (COCO pretrained)",
            )
            self.model = YOLO("yolov8n.pt")
            self.model_version = "yolov8n-coco-pretrained"

        logger.info("model_loaded", version=self.model_version)

    def detect(
        self,
        image_bytes: bytes,
        confidence_threshold: float = 0.45,
    ) -> Tuple[str, float, Optional[dict]]:
        """
        Run YOLOv8 inference on image bytes.
        Returns: (waste_type, confidence, bounding_box_dict)
        """
        import numpy as np
        import cv2

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        h, w = img.shape[:2]

        results = self.model(img, conf=confidence_threshold, verbose=False)

        if not results or not results[0].boxes:
            logger.warning("no_detections_found")
            return DEFAULT_WASTE_TYPE, 0.0, None

        # Pick highest confidence detection
        boxes = results[0].boxes
        best_idx = int(boxes.conf.argmax())
        best_conf = float(boxes.conf[best_idx])
        best_cls_id = int(boxes.cls[best_idx])
        best_cls_name = self.model.names.get(best_cls_id, "trash")

        # Map to CleanTrack waste type
        waste_type = YOLO_TO_WASTE_TYPE.get(best_cls_name.lower(), DEFAULT_WASTE_TYPE)

        # Bounding box (normalised)
        xyxy = boxes.xyxyn[best_idx].tolist()
        bbox = {
            "x": xyxy[0],
            "y": xyxy[1],
            "width": xyxy[2] - xyxy[0],
            "height": xyxy[3] - xyxy[1],
            "confidence": best_conf,
        }

        return waste_type, best_conf, bbox

    @property
    def is_loaded(self) -> bool:
        return self.model is not None
