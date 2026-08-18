"""
Ragento Visual Studio - Direct Unfolded-to-Catalog Saree Pipeline (v4_direct)
Executes 1-Step direct commercial catalog generation bypassing intermediate 2D flat-lays:
- Inputs: Unfolded Warehouse Saree Photos (Ground Truth for Garment, Borders, Weave & Pallu) + Moodboard Reference (Pose, Lighting & Environment).
- Engine: Gemini 3.1 Flash Image in Native 4K.
- Pass 2: Automated Visual QC Inspector.
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from src.vertex_client import get_genai_client
from src.inspector import VisualQCInspector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Saree_Pipeline_v4_Direct")

def call_flash_image(client, contents, max_attempts=5):
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Sending generate_content request to gemini-3.1-flash-image (Attempt {attempt}/{max_attempts})...")
            res = client.models.generate_content(
                model="gemini-3.1-flash-image",
                contents=contents,
                config=config
            )
            if res.candidates:
                for part in res.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        return part.inline_data.data
            logger.warning(f"Attempt {attempt}: No image bytes in response.")
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                backoff = 30 * attempt
                logger.info(f"Quota 429 encountered. Sleeping {backoff}s before retry...")
                time.sleep(backoff)
            else:
                time.sleep(10)
    return None

def process_saree_v4_direct(saree_folder_name: str, moodboard_file: str = "1000221736.jpg"):
    saree_dir = ROOT_DIR / "saree_unfolded" / saree_folder_name
    if not saree_dir.exists():
        raise ValueError(f"Saree directory not found: {saree_dir}")

    input_images = sorted([
        f for f in saree_dir.iterdir()
        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ])
    if not input_images:
        raise ValueError(f"No valid images found in {saree_dir}")

    moodboard_path = ROOT_DIR / "moodboard_2" / moodboard_file
    if not moodboard_path.exists():
        raise ValueError(f"Moodboard file not found: {moodboard_path}")

    # Output directory structured as output_sari/<saree_folder_name>/v4
    output_dir = ROOT_DIR / "output_sari" / saree_folder_name / "v4"
    output_dir.mkdir(parents=True, exist_ok=True)

    final_out = output_dir / f"final_on_model_v4_{saree_folder_name}.png"
    qc_report_out = output_dir / f"qc_report_v4_{saree_folder_name}.json"

    client = get_genai_client()
    inspector = VisualQCInspector()

    logger.info(f"\n==========================================================================")
    logger.info(f" SAREE {saree_folder_name} (DIRECT V4 PIPELINE - GEMINI 3.1 FLASH 4K)")
    logger.info(f"==========================================================================")
    logger.info(f"Input images: {[img.name for img in input_images]}")
    logger.info(f"Moodboard ref: {moodboard_path.name}")
    logger.info(f"Output directory: {output_dir}")

    system_instruction = (
        "You are an expert AI Luxury Fashion Photographer creating a master commercial catalog image for Indian Ethnic Wear.\n\n"
        "TASK - DIRECT HIGH-FIDELITY SAREE DRAPING & MODEL FUSION:\n"
        "1. GARMENT GROUND TRUTH (Reference Images 1 & 2):\n"
        "   - Drape the exact authentic saree shown fully unfolded in Reference Images 1 & 2 onto the female fashion model in classic Nivi saree style (crisp center waist pleats, fitted waist wrap, diagonal shoulder pallu fall).\n"
        "   - Replicate the exact colors, weave textures, motifs, borders, and pallu decorations exactly as seen in the unfolded photos.\n"
        "   - DO NOT hallucinate any extra borders, patterns, or trims that are not physically present in the product photos (e.g. if the body has edge-to-edge stripes with no side borders, keep it edge-to-edge with no side borders).\n"
        "2. MODEL POSE, LIGHTING & STUDIO ENVIRONMENT (Reference Image 3 - Moodboard):\n"
        "   - Replicate the female fashion model pose, posture, body angle, facial expression, camera perspective, lighting, and aesthetic studio/outdoor architecture from Reference Image 3.\n"
        "   - STRICTLY IGNORE any clothing, dress, or garments worn by the person in Reference Image 3.\n"
        "3. STYLING & REALISM:\n"
        "   - Render an elegant, well-fitted blouse complementary in color and fabric to the saree.\n"
        "   - Render hyper-realistic skin texture, natural fabric draping physics, and studio-grade 4K e-commerce fidelity."
    )

    contents = [types.Part.from_text(text=system_instruction)]
    for idx, img_path in enumerate(input_images, 1):
        contents.append(types.Part.from_text(text=f"=== REFERENCE IMAGE {idx}: UNFOLDED PRODUCT PHOTO {idx} (ABSOLUTE GROUND TRUTH FOR GARMENT WEAVE, BORDERS & MOTIFS) ==="))
        contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg"))

    contents.append(types.Part.from_text(text=f"=== REFERENCE IMAGE {len(input_images)+1}: MOODBOARD REFERENCE PHOTO (SOURCE FOR POSE, LIGHTING, CAMERA ANGLE & ENVIRONMENT ONLY - IGNORE CLOTHING) ==="))
    contents.append(types.Part.from_bytes(data=moodboard_path.read_bytes(), mime_type="image/jpeg"))

    bytes_data = call_flash_image(client, contents)
    if not bytes_data:
        raise RuntimeError(f"Generation failed for Saree {saree_folder_name}")

    final_out.write_bytes(bytes_data)
    logger.info(f"✓ GENERATION SUCCESS: Saved {final_out.name} ({len(bytes_data)} bytes)")

    # Pass 2: QC
    logger.info(f"Executing Visual QC Inspector on generated image...")
    report = inspector.inspect(product_image_paths=input_images, generated_image_path=final_out)
    qc_report_out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    logger.info("\n==========================================================================")
    logger.info(f" SAREE {saree_folder_name} (DIRECT V4) COMPLETE!")
    logger.info(f" Final Catalog Output: {final_out}")
    logger.info(f" QC Report           : {qc_report_out}")
    logger.info(f" QC Result           : Pass={report.pass_quality_gate}, Score={report.composite_quality_score:.2f}")
    logger.info("==========================================================================")
    return final_out, report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Direct 1-Step Saree Pipeline (v4)")
    parser.add_argument("--saree", type=str, default="1", help="Folder name (1, 3, etc.) or 'all'")
    parser.add_argument("--moodboard", type=str, default="1000221736.jpg", help="Moodboard filename")
    args = parser.parse_args()

    if args.saree.lower() == "all":
        for s in ["1", "3"]:
            try:
                process_saree_v4_direct(s, args.moodboard)
                time.sleep(20)
            except Exception as e:
                logger.error(f"Error on Saree {s}: {e}")
    else:
        process_saree_v4_direct(args.saree, args.moodboard)
