"""
Visual Critic Module: Uses Gemini 3.7 Flash with automatic fallback to Gemini 3.6 Flash on rate limits (429),
inspects textile, border, and motif fidelity against ground truth photos, and tracks exact token usage and API costs.
"""

import time
import logging
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from PIL import Image

from google.genai import types
from config import settings
from models import VisualCriticFeedback
from src.vertex_client import get_genai_client
from src.cost_tracker import calculate_step_cost

from prompts import VISUAL_CRITIC_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class VisualCritic:
    """Visual Critic using Gemini 3.7 Flash with seamless fallback to Gemini 3.6 Flash on 429 quota rate limits."""

    def __init__(self, model_name: str = None):
        self.primary_model = model_name or settings.CRITIC_MODEL or "gemini-3.7-flash"
        self.fallback_model = "gemini-3.6-flash"
        self.client = get_genai_client()

    def evaluate(
        self,
        product_image_paths: List[Path],
        generated_img_bytes: bytes,
        patch_image_paths: Optional[List[Path]] = None,
        user_feedback: Optional[str] = None
    ) -> Tuple[VisualCriticFeedback, Dict[str, Any]]:
        """Compares generated image against ground truth product photos and high-zoom detail patches."""
        system_instruction = VISUAL_CRITIC_SYSTEM_PROMPT
        contents = [types.Part.from_text(text=system_instruction)]

        for idx, img_path in enumerate(product_image_paths[:4], 1):
            if img_path.exists():
                mime = "image/jpeg" if img_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append(types.Part.from_text(text=f"=== ORIGINAL PRODUCT PHOTO {idx} (GROUND TRUTH) ==="))
                contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type=mime))

        # Attach High-Zoom Ground Truth Detail Patches if available
        if patch_image_paths:
            contents.append(types.Part.from_text(text="=== HIGH-ZOOM GROUND TRUTH DETAIL PATCHES (FORENSIC NEEDLEWORK & LACE ANCHORS) ==="))
            for p in patch_image_paths:
                if p.exists():
                    label = p.stem.replace('_', ' ').upper()
                    contents.append(types.Part.from_text(text=f"--- DETAIL PATCH: {label} ---"))
                    contents.append(types.Part.from_bytes(data=p.read_bytes(), mime_type="image/png"))

        contents.append(types.Part.from_text(text="=== GENERATED 4K CATALOG IMAGE TO CRITIQUE ==="))
        contents.append(types.Part.from_bytes(data=generated_img_bytes, mime_type="image/png"))

        if user_feedback and user_feedback.strip():
            contents.append(types.Part.from_text(text=f"=== PREVIOUS CRITIQUE / REFINEMENT DIRECTIVE ===\n{user_feedback.strip()}"))

        contents.append(types.Part.from_text(text="Analyze the generated catalog image against the ground truth photos and detail patches, and return your structured critique JSON."))

        gen_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisualCriticFeedback,
            temperature=0.1
        )

        # Attempt 1: Primary model (Gemini 3.7 Flash)
        try:
            logger.info(f"Calling Visual Critic on primary model '{self.primary_model}'...")
            res = self.client.models.generate_content(
                model=self.primary_model,
                contents=contents,
                config=gen_config
            )
            feedback = VisualCriticFeedback.model_validate_json(res.text)
            cost_info = calculate_step_cost(self.primary_model, res.usage_metadata, is_image_gen=False)
            logger.info(f"Critic '{self.primary_model}' completed ({feedback.overall_fidelity_score:.2f} score, {cost_info['formatted_cost']}).")
            return feedback, cost_info
        except Exception as e:
            logger.warning(f"Visual Critic call failed on primary model '{self.primary_model}': {e}")
            logger.info(f"Initiating automatic fallback to '{self.fallback_model}'...")
            time.sleep(1)

        # Attempt 2: Fallback model (Gemini 3.6 Flash)
        try:
            res_fb = self.client.models.generate_content(
                model=self.fallback_model,
                contents=contents,
                config=gen_config
            )
            feedback = VisualCriticFeedback.model_validate_json(res_fb.text)
            cost_info = calculate_step_cost(self.fallback_model, res_fb.usage_metadata, is_image_gen=False)
            logger.info(f"Fallback Critic '{self.fallback_model}' completed ({feedback.overall_fidelity_score:.2f} score, {cost_info['formatted_cost']}).")
            return feedback, cost_info
        except Exception as e2:
            logger.error(f"Fallback Visual Critic also failed ({e2}). Returning safe default critique.")
            fallback_feedback = VisualCriticFeedback(
                approved=False,
                overall_fidelity_score=0.75,
                structural_hallucinations=["Potential border or motif deviation"],
                missing_or_misplaced_elements=[],
                refinement_instructions=user_feedback.strip() if user_feedback else "Enforce strict fabric weave, color tone, and border authenticity matching ground truth photos."
            )
            return fallback_feedback, calculate_step_cost(self.fallback_model, None, is_image_gen=False)
