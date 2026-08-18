"""
Ragento Visual Studio - 3-Step Saree Deconstruction & Generation Pipeline (v2 - Refined Technical Drape)
SKU Target: saree/50631.jpg
Moodboard Reference: moodboard_2/1000221736.jpg

Pipeline Architecture:
- Step 1: 2D Textile De-folding & Flat Swatch Unwrap (step1_flat_swatch_50631.png)
- Step 2: High-Visibility Flat-Lit 3D Geometry Drape Blueprint (step2_3d_draped_cloth_50631.png)
- Step 3: Human Model & Scene Fusion (step3_final_on_model_catalog_50631.png)
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
logger = logging.getLogger("Pipeline_v2_Refined")

SAREE_INPUT = ROOT_DIR / "saree" / "50631.jpg"
MOODBOARD_REF = ROOT_DIR / "moodboard_2" / "1000221736.jpg"
OUTPUT_DIR = ROOT_DIR / "output" / "pipeline_v2"

STEP1_OUTPUT = OUTPUT_DIR / "step1_flat_swatch_50631.png"
STEP2_OUTPUT = OUTPUT_DIR / "step2_3d_draped_cloth_50631.png"
STEP3_OUTPUT = OUTPUT_DIR / "step3_final_on_model_catalog_50631.png"

def call_with_retry(client, contents, max_attempts=5):
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Sending generate_content request (Attempt {attempt}/{max_attempts})...")
            res = client.models.generate_content(
                model=settings.GENERATION_MODEL,
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
                backoff = 45 * attempt
                logger.info(f"Quota 429 encountered. Sleeping {backoff}s before retry...")
                time.sleep(backoff)
            else:
                time.sleep(10)
    return None

def run_step_1_flattening(client) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 1: TEXTILE DE-FOLDING & FLAT SWATCH UNWRAP")
    logger.info("==========================================================================")

    if STEP1_OUTPUT.exists():
        logger.info(f"Step 1 output exists at {STEP1_OUTPUT}. Using existing swatch.")
        return STEP1_OUTPUT

    system_instruction = (
        "You are an expert AI Textile Pattern Engineer and Orthographic Illustrator.\n\n"
        "TASK - 2D SAREE TEXTURE DE-FOLDING & FLATTENING:\n"
        "1. De-fold, unroll, and orthographically flatten the saree cloth in the input image into a clean 2D flat pattern map.\n"
        "2. Segment and display three flat panels:\n"
        "   - panel_main_body: Base ground with micro-motifs/stripes.\n"
        "   - panel_zari_border: Horizontal golden zari border edge.\n"
        "   - panel_pallu: Main decorative pallu panel with diamond arrays and tassels.\n"
        "3. Remove all cloth folds, shadows, and perspective. Render a 2D flat textile swatch matrix on a clean white background."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_bytes(data=SAREE_INPUT.read_bytes(), mime_type="image/jpeg")
    ]

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        STEP1_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        STEP1_OUTPUT.write_bytes(bytes_data)
        logger.info(f"✓ STEP 1 SUCCESS: Saved {STEP1_OUTPUT.name} ({len(bytes_data)} bytes)")
        return STEP1_OUTPUT
    raise RuntimeError("Step 1 failed.")

def run_step_2_flat_diffuse_3d_drape(client, step1_swatch_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 2: HIGH-VISIBILITY FLAT-LIT 3D GEOMETRY DRAPE (TECHNICAL BLUEPRINT)")
    logger.info("==========================================================================")

    system_instruction = (
        "You are an expert AI Technical 3D Garment CAD Engineer rendering a High-Visibility Drape Blueprint.\n\n"
        "CRITICAL LIGHTING & PATTERN VISIBILITY DIRECTIVES:\n"
        "1. FLAT DIFFUSE LIGHTING ONLY: STRICTLY FORBIDDEN to add harsh shadows, specular reflections, glossy fabric glare, or dramatic studio lighting. The lighting MUST be completely flat, even, and diffuse (like a 3D CAD UV texture preview).\n"
        "2. MAXIMUM PATTERN CLARITY: Every zari motif, pallu diamond array, and pleat fold MUST remain 100% crisp, sharp, un-shadowed, and fully visible across the entire surface.\n"
        "3. 3D GHOST DRAPE WARP:\n"
        "   - Take the 2D flat pattern map from Image 1.\n"
        "   - Bend the main body into 6-8 sharp vertical waist pleats at the bottom center.\n"
        "   - Wrap the zari border smoothly along the waist edge.\n"
        "   - Drape the decorative pallu diagonally over the left shoulder curve of a neutral ghost mannequin so it hangs downwards naturally.\n"
        "4. NEUTRAL BACKGROUND: Pure matte white studio backdrop with zero floor shadows, zero human skin, zero faces, and zero ambient reflections."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== STEP 1 FLAT 2D TEXTILE SWATCH ==="),
        types.Part.from_bytes(data=step1_swatch_path.read_bytes(), mime_type="image/png")
    ]

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        STEP2_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        STEP2_OUTPUT.write_bytes(bytes_data)
        logger.info(f"✓ STEP 2 SUCCESS: Saved refined flat-lit 3D drape to {STEP2_OUTPUT.name} ({len(bytes_data)} bytes)")
        return STEP2_OUTPUT
    raise RuntimeError("Step 2 failed.")

def run_step_3_model_fusion(client, step2_drape_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 3: HUMAN MODEL & ENVIRONMENT FUSION")
    logger.info("==========================================================================")

    system_instruction = (
        "You are an expert AI Luxury Fashion Photographer rendering final catalog masters.\n\n"
        "TASK - ON-MODEL CATALOG FUSION:\n"
        "1. Take the high-visibility pre-draped 3D saree cloth structure from Image 1 (Step 2 3D Technical Drape).\n"
        "2. Fuse this exact pre-draped saree onto an elegant female fashion model.\n"
        "3. Replicate the model pose, body posture, facial expression, camera framing, studio lighting, and background atmosphere from Image 2 (Moodboard Reference).\n"
        "4. Render a fitted saree blouse matching the zari border. Ensure razor-sharp 4K catalog resolution, realistic fabric drape physics, natural lighting shadows, and photorealistic human model features."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== IMAGE 1: HIGH-VISIBILITY 3D DRAPED SAREE CLOTH STRUCTURE ==="),
        types.Part.from_bytes(data=step2_drape_path.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="=== IMAGE 2: MOODBOARD REFERENCE (POSE, LIGHTING & ENVIRONMENT SOURCE - IGNORE CLOTHING) ==="),
        types.Part.from_bytes(data=MOODBOARD_REF.read_bytes(), mime_type="image/jpeg")
    ]

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        STEP3_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        STEP3_OUTPUT.write_bytes(bytes_data)
        logger.info(f"✓ STEP 3 SUCCESS: Saved final catalog image to {STEP3_OUTPUT.name} ({len(bytes_data)} bytes)")
        return STEP3_OUTPUT
    raise RuntimeError("Step 3 failed.")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = get_genai_client()
    inspector = VisualQCInspector()

    logger.info("Starting Refined Technical 3-Step Saree Pipeline...")

    # Step 1: 2D Swatch
    step1_path = run_step_1_flattening(client)

    logger.info("Pausing 35s to cool down API quota...")
    time.sleep(35)

    # Step 2: High-Visibility Flat-Lit 3D Drape Blueprint
    step2_path = run_step_2_flat_diffuse_3d_drape(client, step1_path)

    logger.info("Pausing 35s to cool down API quota...")
    time.sleep(35)

    # Step 3: Human Model Fusion & Scene Composition
    step3_path = run_step_3_model_fusion(client, step2_path)

    # QC Inspection
    logger.info("\nExecuting Gemini 3.6 Flash Visual QC on Step 3 output...")
    report = inspector.inspect(product_image_paths=[SAREE_INPUT], generated_image_path=step3_path)
    
    report_file = OUTPUT_DIR / "pipeline_v2_qc_report.json"
    report_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    logger.info("\n==========================================================================")
    logger.info(f" PIPELINE V2 REFINED EXECUTION COMPLETE!")
    logger.info(f" Step 1 Swatch  : {step1_path}")
    logger.info(f" Step 2 3D Drape: {step2_path}")
    logger.info(f" Step 3 Final   : {step3_path}")
    logger.info(f" QC Status      : Passed={report.pass_quality_gate}, Score={report.composite_quality_score:.2f}")
    logger.info("==========================================================================")

if __name__ == "__main__":
    main()
