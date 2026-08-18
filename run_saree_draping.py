"""
Robust saree draping generation runner with automatic 429 backoff retry.
Generates model-draped sarees from flat un-draped saree images in 'saree/' and moodboard references in 'moodboard_2/'.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from config import settings
from src.vertex_client import get_genai_client
from src.inspector import VisualQCInspector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Saree_Draping_Runner")

SAREE_DIR = ROOT_DIR / "saree"
MOODBOARD_2_DIR = ROOT_DIR / "moodboard_2"
OUTPUT_DIR = ROOT_DIR / "output" / "saree_draped_catalog"

def generate_draped_saree(client, saree_path: Path, moodboard_path: Path, output_path: Path):
    system_instruction = (
        "You are an expert AI Luxury Fashion Photographer and Master Stylist rendering ultra-high-definition catalog masters.\n\n"
        "CRITICAL TASK - SAREE DRAPING FROM UN-DRAPED / FLAT GARMENT PHOTO:\n"
        "1. TARGET GARMENT (UN-DRAPED SAREE PHOTO):\n"
        "   - The input product shot depicts an un-draped / flat / folded Indian saree cloth piece.\n"
        "   - You MUST extract the exact base fabric color palette, textile weave, pattern motifs, zari/printed borders, and pallu design from this image.\n"
        "   - You MUST render an elegant female fashion model DRAPING and WEARING this exact saree as a complete traditional Indian saree ensemble (6-yard draped silk saree with waist pleats, shoulder pallu drape, tucked border, and matching/fitted blouse).\n"
        "   - STRICTLY FORBIDDEN: Do not leave the garment flat or folded. Do not render a kurta, salwar suit, pants, or dupatta. It MUST be a draped saree.\n\n"
        "2. MOODBOARD REFERENCE SHOTS (POSE, MODEL & ENVIRONMENT SOURCE):\n"
        "   - Extract the model pose, body posture, facial expression, camera framing, studio lighting, and background ambience from the moodboard reference image.\n"
        "   - IGNORE ALL CLOTHING WORN IN THE MOODBOARD REFERENCE! ONLY USE MOODBOARD FOR MODEL POSE AND ENVIRONMENT.\n\n"
        "OUTPUT SPECIFICATION:\n"
        "Render a luxury fashion D2C e-commerce catalog master in high-definition 4K resolution with razor-sharp textile texture, crisp saree pleating, and realistic fabric drape physics."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== TARGET GARMENT SOURCE OF TRUTH (UN-DRAPED SAREE CLOTH) ==="),
        types.Part.from_bytes(data=saree_path.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== MOODBOARD REFERENCE (SOURCE FOR MODEL POSE & ENVIRONMENT ONLY - IGNORE CLOTHING) ==="),
        types.Part.from_bytes(data=moodboard_path.read_bytes(), mime_type="image/jpeg")
    ]

    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Generating content (Attempt {attempt}/{max_attempts})...")
            response = client.models.generate_content(
                model=settings.GENERATION_MODEL,
                contents=contents,
                config=config
            )

            image_bytes = None
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.inline_data and part.inline_data.data:
                                image_bytes = part.inline_data.data
                                break

            if image_bytes:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image_bytes)
                logger.info(f"SUCCESS: Saved {output_path} ({len(image_bytes)} bytes)")
                return True
            else:
                logger.warning(f"No image bytes returned on attempt {attempt}")

        except Exception as e:
            logger.warning(f"API Call failed on attempt {attempt}: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                backoff = 35 * attempt
                logger.info(f"Quota 429 detected. Waiting {backoff} seconds before retry...")
                time.sleep(backoff)
            else:
                time.sleep(10)

    return False

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = get_genai_client()
    inspector = VisualQCInspector()

    saree_files = sorted([p for p in SAREE_DIR.glob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png"]])
    moodboard_files = sorted([p for p in MOODBOARD_2_DIR.glob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png"]])

    logger.info(f"Starting Saree Draping Generation for {len(saree_files)} saree inputs...")

    summary = []

    for saree_file in saree_files:
        sku_id = saree_file.stem
        # Pick moodboard 1000221736.jpg or fallback to first moodboard
        mb_file = moodboard_files[0]
        out_file = OUTPUT_DIR / f"{sku_id}_draped_model_catalog.png"

        logger.info(f"\n==========================================================================")
        logger.info(f" Processing Saree: {saree_file.name} -> {out_file.name}")
        logger.info(f" Moodboard Pose Reference: {mb_file.name}")
        logger.info(f"==========================================================================")

        success = generate_draped_saree(client, saree_file, mb_file, out_file)

        if success and out_file.exists():
            try:
                logger.info(f"Inspecting generated asset {out_file.name} with Gemini 3.6 Flash...")
                qc_report = inspector.inspect(product_image_paths=[saree_file], generated_image_path=out_file)
                
                report_path = OUTPUT_DIR / f"{sku_id}_qc_report.json"
                report_path.write_text(qc_report.model_dump_json(indent=2), encoding="utf-8")
                
                summary.append({
                    "sku_id": sku_id,
                    "saree_input": saree_file.name,
                    "moodboard_reference": mb_file.name,
                    "output_image": str(out_file),
                    "qc_passed": qc_report.pass_quality_gate,
                    "composite_score": qc_report.composite_quality_score,
                    "category_match": qc_report.garment_type_match,
                    "color_match": qc_report.base_color_fidelity
                })
                logger.info(f"QC Completed for {sku_id}: Passed={qc_report.pass_quality_gate}, Score={qc_report.composite_quality_score:.2f}")
            except Exception as e:
                logger.warning(f"QC Inspection failed: {e}")
        else:
            logger.error(f"Failed to generate draped saree for {sku_id}")

        # Sleep between sarees to maintain healthy API quota
        logger.info("Sleeping 25s between SKU generations...")
        time.sleep(25)

    summary_path = OUTPUT_DIR / "saree_draping_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info(f"\nPipeline Finished! Summary report saved to {summary_path}")

if __name__ == "__main__":
    main()
