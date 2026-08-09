"""
Pass 2 Automated Visual QC Inspector: Compares source product shots with generated output image using Gemini 3.6 Flash in JSON Schema Mode.
"""

import json
import logging
from typing import List
from pathlib import Path
from PIL import Image

from config import settings
from models import VisualQCReport
from src.vertex_client import get_genai_client

logger = logging.getLogger(__name__)


class VisualQCInspector:
    """Automated visual inspector powered by Gemini 3.6 Flash with Layer 1 Binary Sanity & Layer 2 Granular Guardrails."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.INSPECTOR_MODEL
        self.client = get_genai_client()

    def inspect(
        self,
        product_image_paths: List[Path],
        generated_image_path: Path,
        fabric_anchor_path: Path = None
    ) -> VisualQCReport:
        """Inspects generated image against source product images using Gemini 3.6 Flash model."""

        logger.info(f"Inspecting generated asset {generated_image_path.name} with '{self.model_name}' (Layer 1 Binary + Layer 2 Guardrails)...")

        pil_product = [Image.open(p) for p in product_image_paths if p.exists()]
        pil_generated = Image.open(generated_image_path) if generated_image_path.exists() else None

        if not pil_generated:
            raise RuntimeError(f"Visual QC Inspector Error: Generated image file at {generated_image_path} does not exist.")

        qc_prompt = (
            "You are an expert Quality Control (QC) Inspector for D2C fashion apparel catalog images.\n"
            "INPUTS:\n"
            "- Images 1 to N: Original product shots (original garment category, base fabric color, weave, and print motifs).\n"
            "- Final Image: AI-Generated Output Image.\n\n"
            "EVALUATION PROTOCOL:\n\n"
            "1. LAYER 1: BINARY IDENTITY & PIECE SANITY CHECK (is_same_garment_or_valid_piece):\n"
            "   - Disregarding model pose and studio background, does the final image depict the EXACT SAME garment SKU, OR a valid individual piece/styling of the SKU (e.g. wearing full saree set, or wearing single kurta/dupata piece from product shots)?\n"
            "   - Set is_same_garment_or_valid_piece = TRUE if the product identity is preserved (full set or individual piece).\n"
            "   - Set is_same_garment_or_valid_piece = FALSE ONLY IF the garment rendered is a completely wrong unrelated outfit from another category/color.\n\n"
            "2. LAYER 2: GRANULAR FEATURE QUALITY CHECKS (0.0 to 1.0):\n"
            "   - garment_type_match: Category match score (1.0 = exact matching category/ensemble).\n"
            "   - base_color_fidelity: Base fabric color palette score (1.0 = identical base color tone).\n"
            "   - pattern_match_confidence: Pattern, weave, embroidery motif score (0.0 to 1.0).\n"
            "   - anatomical_correctness: Model anatomy, limbs, skin realism score (0.0 to 1.0).\n"
            "   - garment_drape_realism: Realistic cloth draping physics score (0.0 to 1.0).\n"
            "   - transformation_verification: Studio model transformation score (0.8-1.0 = model studio shot, 0.0 = raw copy).\n\n"
            "QUALITY GATE DECISION RULES:\n"
            "- If is_same_garment_or_valid_piece is FALSE -> pass_quality_gate = FALSE, detected_defects append 'LAYER_1_IDENTITY_MISMATCH'.\n"
            "- If garment_type_match < 0.80 -> pass_quality_gate = FALSE, detected_defects append 'CATEGORY_MISMATCH'.\n"
            "- If base_color_fidelity < 0.80 -> pass_quality_gate = FALSE, detected_defects append 'COLOR_PALETTE_MISMATCH'.\n"
            "- If pattern_match_confidence < 0.80 -> pass_quality_gate = FALSE, detected_defects append 'PATTERN_DEVIATION'.\n"
            "- If transformation_verification < 0.70 -> pass_quality_gate = FALSE, detected_defects append 'UNTRANSFORMED_COPY'.\n\n"
            "Return JSON matching VisualQCReport schema."
        )

        contents = [qc_prompt] + pil_product[:3] + [pil_generated]

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=dict(
                    response_mime_type="application/json",
                    response_schema=VisualQCReport,
                )
            )

            report_data = json.loads(response.text)
            logger.info(
                f"Gemini 3.6 Flash Visual QC Result: BinarySanity={report_data.get('is_same_garment_or_valid_piece')}, "
                f"CategoryMatch={report_data.get('garment_type_match')}, "
                f"ColorMatch={report_data.get('base_color_fidelity')}, "
                f"PassGate={report_data.get('pass_quality_gate')}"
            )
            return VisualQCReport(**report_data)

        except Exception as e:
            raise RuntimeError(f"Visual QC Inspector Error: Failed to perform visual evaluation call: {e}")
