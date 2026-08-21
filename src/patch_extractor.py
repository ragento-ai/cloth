"""
Autonomous Semantic Micro-Patch Extractor for V-Transfer Garments.
Uses Gemini 3.6 Flash to detect key garment embellishment regions (embroidery, lace, prints, trims)
and extracts high-zoom ROI cropped patches for multi-reference generation and critique.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image

from google.genai import types
from src.vertex_client import get_genai_client

logger = logging.getLogger(__name__)


def clean_filename(text: str) -> str:
    """Sanitizes label for filesystem naming."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:50]


class SemanticPatchExtractor:
    """Extracts high-zoom ROI patches for critical garment embellishments."""

    def __init__(self, model_name: str = "gemini-3.6-flash"):
        self.model_name = model_name
        self.client = get_genai_client()

    def extract_patches(
        self,
        image_path: Path,
        output_dir: Path,
        max_patches: int = 6
    ) -> List[Dict[str, Any]]:
        """Detects 4-6 semantic embellishment boxes and crops them into output_dir."""
        output_dir.mkdir(parents=True, exist_ok=True)
        img = Image.open(image_path)
        img_width, img_height = img.size

        prompt = (
            f"You are an expert fashion detail analyzer.\n"
            f"Detect the 4 to {max_patches} most visually intricate micro-detail regions of this apparel "
            f"(e.g., embroidery, lace cutwork, hem borders, neckline bib, tassels, prints, sleeve trims).\n\n"
            f"Return ONLY a JSON list of objects matching this exact schema:\n"
            f"[\n"
            f"  {{\n"
            f"    \"box_2d\": [ymin, xmin, ymax, xmax],\n"
            f"    \"label\": \"descriptive_label_of_garment_detail\"\n"
            f"  }}\n"
            f"]\n"
            f"Coordinates must be normalized integers between 0 and 1000."
        )

        candidates = [self.model_name, "gemini-3.7-flash", "gemini-2.5-flash"]
        res = None

        for m in candidates:
            try:
                res = self.client.models.generate_content(
                    model=m,
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if res and res.text:
                    break
            except Exception as e:
                logger.warning(f"Patch detection failed on model '{m}': {e}")

        if not res or not res.text:
            logger.error("Failed to extract patches from image.")
            return []

        try:
            detections = json.loads(res.text)
        except Exception as e:
            logger.error(f"Failed to parse detection JSON: {e}")
            return []

        patch_records = []
        for idx, item in enumerate(detections[:max_patches], 1):
            box = item.get("box_2d", [0, 0, 1000, 1000])
            ymin, xmin, ymax, xmax = box
            label = item.get("label", f"patch_{idx}")
            safe_name = clean_filename(label)
            filename = f"{idx:02d}_{safe_name}.png"
            crop_path = output_dir / filename

            left = max(0, min(int(xmin * img_width / 1000), img_width - 1))
            upper = max(0, min(int(ymin * img_height / 1000), img_height - 1))
            right = max(left + 10, min(int(xmax * img_width / 1000), img_width))
            lower = max(upper + 10, min(int(ymax * img_height / 1000), img_height))

            cropped_img = img.crop((left, upper, right, lower))
            cropped_img.save(crop_path, "PNG")

            patch_records.append({
                "index": idx,
                "label": label,
                "box_2d_normalized": [ymin, xmin, ymax, xmax],
                "file_path": str(crop_path),
                "width": cropped_img.width,
                "height": cropped_img.height
            })
            logger.info(f"Extracted Patch {idx}: '{label}' ({cropped_img.width}x{cropped_img.height}px) -> {crop_path.name}")

        return patch_records
