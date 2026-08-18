"""
Script to generate draped saree catalog images for un-draped saree images in 'saree' directory
using reference pose and studio aesthetics from 'moodboard_2' directory via Gemini 3 Pro Image.
"""

import sys
import json
import time
import logging
from pathlib import Path
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from config import settings
from src.vertex_client import get_genai_client
from src.inspector import VisualQCInspector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Saree_Moodboard2_Pipeline")

SAREE_DIR = ROOT_DIR / "saree"
MOODBOARD_2_DIR = ROOT_DIR / "moodboard_2"
OUTPUT_DIR = ROOT_DIR / "output" / "saree_moodboard2_outputs"

def run_saree_pipeline():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = get_genai_client()
    inspector = VisualQCInspector()

    saree_images = sorted([
        p for p in SAREE_DIR.glob("*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
    ])
    moodboard_images = sorted([
        p for p in MOODBOARD_2_DIR.glob("*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
    ])

    logger.info(f"Found {len(saree_images)} saree input images in {SAREE_DIR}")
    logger.info(f"Found {len(moodboard_images)} moodboard_2 reference images in {MOODBOARD_2_DIR}")

    results = []

    for saree_img in saree_images:
        sku_name = saree_img.stem
        logger.info(f"\n==========================================================================")
        logger.info(f" Processing Saree: {sku_name} ({saree_img.name})")
        logger.info(f"==========================================================================")

        for idx, mb_img in enumerate(moodboard_images[:1]):  # Process 1 shot per saree
            shot_tag = f"shot_{idx + 1}_mb_{mb_img.stem}"
            output_file = OUTPUT_DIR / f"{sku_name}_{shot_tag}_draped_catalog.png"
            
            logger.info(f"\n--- Generating Output: {output_file.name} ---")
            logger.info(f"Input Saree: {saree_img.name}")
            logger.info(f"Moodboard Reference: {mb_img.name}")

            contents = []

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

            contents.append(types.Part.from_text(text=system_instruction))

            # Add Target Saree Image
            contents.append(types.Part.from_text(text="=== TARGET GARMENT SOURCE OF TRUTH (UN-DRAPED SAREE CLOTH) ==="))
            mime = "image/jpeg" if saree_img.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
            contents.append(types.Part.from_bytes(data=saree_img.read_bytes(), mime_type=mime))

            # Add Moodboard Image
            contents.append(types.Part.from_text(text="=== MOODBOARD REFERENCE (SOURCE FOR MODEL POSE, LIGHTING & ENVIRONMENT ONLY - IGNORE MOODBOARD CLOTHING!) ==="))
            mime_mb = "image/jpeg" if mb_img.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
            contents.append(types.Part.from_bytes(data=mb_img.read_bytes(), mime_type=mime_mb))

            image_config = types.ImageConfig(
                image_size="4K",
                aspect_ratio="3:4"
            )
            config = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=image_config
            )

            print("Sleeping 30s to respect API rate limits...")
            time.sleep(30)

            try:
                response = client.models.generate_content(
                    model=settings.GENERATION_MODEL,
                    contents=contents,
                    config=config
                )

                generated_bytes = None
                if response.candidates:
                    for candidate in response.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if part.inline_data:
                                    generated_bytes = part.inline_data.data
                                    break

                if generated_bytes:
                    output_file.write_bytes(generated_bytes)
                    logger.info(f"Successfully generated and saved {output_file.name} ({len(generated_bytes)} bytes)")
                    
                    # Run Visual QC Inspector
                    qc_report = inspector.inspect(
                        product_image_paths=[saree_img],
                        generated_image_path=output_file
                    )
                    results.append({
                        "saree_input": saree_img.name,
                        "moodboard_ref": mb_img.name,
                        "output_path": str(output_file),
                        "qc_score": qc_report.composite_quality_score,
                        "passed": qc_report.pass_quality_gate,
                        "defects": qc_report.detected_defects
                    })
                    logger.info(f"QC Passed: {qc_report.pass_quality_gate} | Score: {qc_report.composite_quality_score:.2f}")
                else:
                    logger.error(f"Failed generation for {saree_img.name}: No image bytes in response.")

            except Exception as e:
                logger.error(f"Error generating {output_file.name}: {e}")

    summary_file = OUTPUT_DIR / "saree_generation_summary.json"
    summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info(f"\nCompleted saree draping generation pipeline! Summary saved to {summary_file}")

if __name__ == "__main__":
    run_saree_pipeline()
