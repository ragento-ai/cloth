"""
Pass 2 Multi-Reference Image Generation Engine using Vertex AI Gemini 3 Pro Image model with explicit role tagging.
"""

import logging
from pathlib import Path
from typing import List
from PIL import Image

from google.genai import types
from config import settings
from src.vertex_client import get_genai_client

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Multi-reference visual generation engine leveraging Gemini 3 Pro Image on Vertex AI."""

    def __init__(self, model_name: str = None, location: str = None):
        self.model_name = model_name or settings.GENERATION_MODEL
        self.location = location or settings.VERTEX_LOCATION
        self.client = get_genai_client(location=self.location)

    def generate(
        self,
        json_prompt_str: str,
        product_image_paths: List[Path],
        moodboard_image_paths: List[Path],
        output_path: Path
    ) -> Path:
        """Generates catalog model image using explicit role-tagged image inputs to prevent moodboard cloth bleeding."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Preparing generation payload for model '{self.model_name}' on location '{self.location}'...")

        contents = []

        # System Instruction for Image Role Disambiguation
        system_instruction = (
            "You are an expert AI Fashion Model Image Generator.\n"
            "INPUT IMAGE ROLE DISAMBIGUATION:\n"
            "1. TARGET GARMENT PRODUCT SHOTS: Use these images as the EXCLUSIVE SOURCE OF TRUTH for the garment's fabric, pattern, print motifs, weave, color palette, and piece category.\n"
            "2. MOODBOARD REFERENCE SHOTS: Use these images EXCLUSIVELY for model pose, body gesture, lighting, framing, and studio environment. IGNORE ALL CLOTHING WORN BY THE MOODBOARD MODELS!\n\n"
            "EXPLICIT PROMPT SPECIFICATION:\n"
            f"{json_prompt_str}\n\n"
            "OUTPUT INSTRUCTION:\n"
            "Render a photorealistic D2C e-commerce catalog image showing a model wearing the TARGET GARMENT in the exact pose and lighting of the moodboard."
        )

        contents.append(types.Part.from_text(text=system_instruction))

        # Attach Product Shots with explicit role tags
        contents.append(types.Part.from_text(text="=== TARGET GARMENT PRODUCT SHOTS (SOURCE OF TRUTH FOR CLOTHING) ==="))
        for p in product_image_paths[:3]:
            if p.exists():
                img = Image.open(p)
                mime = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime))

        # Attach Moodboard References with explicit role tags
        contents.append(types.Part.from_text(text="=== MOODBOARD REFERENCE SHOTS (SOURCE OF TRUTH FOR MODEL POSE & STUDIO ENVIRONMENT ONLY - IGNORE MOODBOARD CLOTHING!) ==="))
        for m in moodboard_image_paths[:2]:
            if m.exists():
                mime = "image/jpeg" if m.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append(types.Part.from_bytes(data=m.read_bytes(), mime_type=mime))

        try:
            config = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            # Extract generated image bytes from response
            generated_bytes = None
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                generated_bytes = part.inline_data.data
                                break

            if not generated_bytes:
                raise RuntimeError(
                    f"Generation Engine Error: Model '{self.model_name}' did not return image bytes in response modalities."
                )

            output_path.write_bytes(generated_bytes)
            logger.info(f"Successfully generated image via model '{self.model_name}' and saved to {output_path}")
            return output_path

        except Exception as e:
            raise RuntimeError(f"Generation Engine Error: Image generation failed via model '{self.model_name}': {e}")
