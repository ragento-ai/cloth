"""
Pass 2 Multi-Reference Image Generation & Refinement Engine using Gemini 3.1 Flash Image.
Enforces Native 4K Resolution on ALL generations and captures exact usage tokens and cost metrics.
"""

import time
import socket
import logging
from pathlib import Path

# Set global default socket timeout to 180 seconds to prevent unhandled API socket hanging
socket.setdefaulttimeout(180)
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image

from google.genai import types
from config import settings
from prompts import format_image_generation_prompt
from src.vertex_client import get_genai_client
from src.cost_tracker import calculate_step_cost

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Multi-reference visual generation & refinement engine leveraging Gemini 3.1 Flash Image (Native 4K)."""

    def __init__(self, model_name: str = None, location: str = None):
        self.model_name = model_name or settings.GENERATION_MODEL
        self.location = location or settings.VERTEX_LOCATION
        self.client = get_genai_client(location=self.location)

    def _call_model_with_retry(self, contents: list, max_attempts: int = 4) -> Tuple[bytes, Dict[str, Any]]:
        """Invokes Gemini 3.1 Flash Image with 4K Native config and tracks usage/cost metrics."""
        image_config = types.ImageConfig(
            image_size="4K",
            aspect_ratio="3:4"
        )
        config = types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=image_config
        )

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Generating 4K image with '{self.model_name}' (Attempt {attempt}/{max_attempts})...")
                res = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )
                generated_bytes = None
                if res.candidates:
                    for candidate in res.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if part.inline_data and part.inline_data.data:
                                    generated_bytes = part.inline_data.data
                                    break

                if generated_bytes:
                    cost_info = calculate_step_cost(self.model_name, res.usage_metadata, is_image_gen=True)
                    logger.info(f"Image Generator '{self.model_name}' produced 4K asset ({len(generated_bytes)} bytes, {cost_info['formatted_cost']}).")
                    return generated_bytes, cost_info

                logger.warning(f"Attempt {attempt}: No inline image bytes returned by {self.model_name}.")
            except Exception as e:
                logger.warning(f"Attempt {attempt} generation call failed: {e}")
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    backoff = 20 * attempt
                    logger.info(f"Quota 429 encountered. Sleeping {backoff}s before retry...")
                    time.sleep(backoff)
                else:
                    time.sleep(5)

        raise RuntimeError(f"Generation Engine Error: Model '{self.model_name}' failed to produce image bytes after {max_attempts} attempts.")

    def generate(
        self,
        json_prompt_str: str,
        product_image_paths: List[Path],
        moodboard_image_paths: List[Path],
        output_path: Path,
        patch_image_paths: Optional[List[Path]] = None
    ) -> Tuple[Path, Dict[str, Any]]:
        """Generates catalog model image in native 4K using explicit role-tagged image inputs with 1 assigned moodboard."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Preparing 4K generation payload for model '{self.model_name}'...")

        contents = []

        # System Instruction for Role Disambiguation & 3-Way Toggle Support in Native 4K
        system_instruction = format_image_generation_prompt(json_prompt_str)

        contents.append(types.Part.from_text(text=system_instruction))

        # 1. Attach ONLY the assigned Moodboard Reference FIRST (Master Canvas, Camera, Pose & Studio Anchor)
        contents.append(types.Part.from_text(text="=== MASTER CANVAS, CAMERA, POSE & STUDIO ENVIRONMENT (MOODBOARD REFERENCE SHOT - MASTER TEMPLATE) ==="))
        for m in moodboard_image_paths[:1]:
            if m.exists():
                mime = "image/jpeg" if m.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append(types.Part.from_bytes(data=m.read_bytes(), mime_type=mime))

        # 2. Attach Product Shots with explicit role tags (Ground Truth Apparel Swatches - Uncompressed ULTRA_HIGH)
        contents.append(types.Part.from_text(text="=== TARGET APPAREL PRODUCT PHOTOS (CLOTHING SWATCHES ONLY - UNCOMPRESSED ULTRA_HIGH RESOLUTION - IGNORE MODEL & POSE) ==="))
        ultra_high_res_config = types.PartMediaResolution(
            level=types.PartMediaResolutionLevel.MEDIA_RESOLUTION_ULTRA_HIGH
        )
        for p in product_image_paths[:3]:
            if p.exists():
                mime = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append(types.Part.from_bytes(
                    data=p.read_bytes(),
                    mime_type=mime,
                    media_resolution=ultra_high_res_config
                ))

        # 3. Attach High-Zoom Detail Patches if provided (Lace, embroidery, prints with uncompressed ULTRA_HIGH resolution)
        if patch_image_paths:
            contents.append(types.Part.from_text(text="=== HIGH-ZOOM GROUND TRUTH DETAIL PATCHES (UNCOMPRESSED ULTRA_HIGH ANCHORS - 100% REPLICATION REQUIRED) ==="))
            for p in patch_image_paths:
                if p.exists():
                    label = p.stem.replace('_', ' ').upper()
                    contents.append(types.Part.from_text(text=f"--- DETAIL PATCH: {label} ---"))
                    mime = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                    contents.append(types.Part.from_bytes(
                        data=p.read_bytes(),
                        mime_type=mime,
                        media_resolution=ultra_high_res_config
                    ))

        generated_bytes, cost_info = self._call_model_with_retry(contents)
        output_path.write_bytes(generated_bytes)
        logger.info(f"Successfully generated 4K image via model '{self.model_name}' and saved to {output_path}")
        return output_path, cost_info

    def refine(
        self,
        product_image_paths: List[Path],
        moodboard_image_path: Optional[Path],
        previous_image_bytes: bytes,
        critic_instructions: str,
        user_feedback: Optional[str],
        output_path: Path,
        patch_image_paths: Optional[List[Path]] = None
    ) -> Tuple[Path, Dict[str, Any]]:
        """Refines an existing draft image in native 4K incorporating visual critic feedback and user directives."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Preparing 4K refinement payload for model '{self.model_name}'...")

        system_instruction = (
            "You are an expert AI Luxury Fashion Photographer and Master Stylist.\n"
            "Your task is to refine and correct defects in the PREVIOUS DRAFT IMAGE according to the CRITIC CORRECTION DIRECTIVES.\n"
            "Preserve exact authentic textile weave, embroidery, lace openwork cutouts, and base colors from the ground truth product shots."
        )

        contents = [types.Part.from_text(text=system_instruction)]

        # Attach Ground Truth Product Shots (with ULTRA_HIGH input resolution)
        contents.append(types.Part.from_text(text="=== TARGET GARMENT PRODUCT SHOTS (UNCOMPRESSED ULTRA_HIGH INPUT RESOLUTION) ==="))
        ultra_high_res_config = types.PartMediaResolution(
            level=types.PartMediaResolutionLevel.MEDIA_RESOLUTION_ULTRA_HIGH
        )
        for p in product_image_paths[:3]:
            if p.exists():
                mime = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append(types.Part.from_bytes(
                    data=p.read_bytes(),
                    mime_type=mime,
                    media_resolution=ultra_high_res_config
                ))

        # Attach High-Zoom Detail Patches if available (with uncompressed ULTRA_HIGH resolution)
        if patch_image_paths:
            contents.append(types.Part.from_text(text="=== HIGH-ZOOM GROUND TRUTH DETAIL PATCHES (UNCOMPRESSED ULTRA_HIGH ANCHORS - 100% REPLICATION REQUIRED) ==="))
            for p in patch_image_paths:
                if p.exists():
                    label = p.stem.replace('_', ' ').upper()
                    contents.append(types.Part.from_text(text=f"--- DETAIL PATCH: {label} ---"))
                    mime = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                    contents.append(types.Part.from_bytes(
                        data=p.read_bytes(),
                        mime_type=mime,
                        media_resolution=ultra_high_res_config
                    ))

        # Attach Moodboard Reference if available
        if moodboard_image_path and moodboard_image_path.exists():
            mime = "image/jpeg" if moodboard_image_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
            contents.append(types.Part.from_text(text="=== MOODBOARD REFERENCE (POSE & STUDIO ONLY) ==="))
            contents.append(types.Part.from_bytes(data=moodboard_image_path.read_bytes(), mime_type=mime))

        # Attach Previous Draft Image
        contents.append(types.Part.from_text(text="=== PREVIOUS DRAFT IMAGE (CONTAINING DEFECTS TO FIX) ==="))
        contents.append(types.Part.from_bytes(data=previous_image_bytes, mime_type="image/png"))

        # Attach Correction Directives
        correction_text = f"CRITIC CORRECTION DIRECTIVES:\n{critic_instructions}"
        if user_feedback and user_feedback.strip():
            correction_text += f"\n\nHIGH-PRIORITY USER REQUEST:\n{user_feedback.strip()}"

        contents.append(types.Part.from_text(text=f"=== REFINEMENT & CORRECTION SPECIFICATION ===\n{correction_text}"))

        generated_bytes, cost_info = self._call_model_with_retry(contents)
        output_path.write_bytes(generated_bytes)
        logger.info(f"Successfully refined 4K image via model '{self.model_name}' and saved to {output_path}")
        return output_path, cost_info
