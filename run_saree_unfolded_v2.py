"""
Ragento Visual Studio - 3-Step Saree Pipeline Runner
Executes 3-Step pipeline on saree_unfolded inputs:
- Step 1: 2D Textile Swatch Flattening (using all input photos in folder)
- Step 2: 3D Flat-Diffuse Geometry Drape Blueprint
- Step 3: Human Model & Scene Fusion (using moodboard reference)
- Automated Visual QC Inspector
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
from config import settings
from src.vertex_client import get_genai_client
from src.inspector import VisualQCInspector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Saree_3Step_Runner")

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

def run_step_1_flattening(client, input_images: list[Path], output_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 1: TEXTILE DE-FOLDING & FLAT SWATCH UNWRAP")
    logger.info("==========================================================================")

    if output_path.exists():
        logger.info(f"Step 1 output exists at {output_path}. Using existing swatch.")
        return output_path

    system_instruction = (
        "You are an expert AI Textile Pattern Engineer and Orthographic Illustrator.\n\n"
        "TASK - 2D SAREE TEXTURE DE-FOLDING & FLATTENING:\n"
        "1. De-fold, unroll, and orthographically flatten the saree cloth shown across the reference input images into a clean 2D flat pattern map.\n"
        "2. Segment and display three flat panels side-by-side or clearly laid out:\n"
        "   - panel_main_body: Base ground color, micro-motifs, jacquard weaves, and body pattern.\n"
        "   - panel_zari_border: Horizontal border edge with authentic zari/embroidery detailing.\n"
        "   - panel_pallu: Main decorative end-piece pallu panel with diamond arrays, motifs, and tassels.\n"
        "3. Remove all cloth folds, harsh creases, physical wrinkles, shadows, and perspective distortions. Render a clean 2D flat textile swatch matrix on a clean white background with 100% fidelity to the original fabric colors and patterns."
    )

    contents = [types.Part.from_text(text=system_instruction)]
    for idx, img_path in enumerate(input_images, 1):
        contents.append(types.Part.from_text(text=f"=== INPUT IMAGE {idx}: {img_path.name} ==="))
        contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg"))

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes_data)
        logger.info(f"✓ STEP 1 SUCCESS: Saved {output_path.name} ({len(bytes_data)} bytes)")
        return output_path
    raise RuntimeError(f"Step 1 failed for {output_path}")

def run_step_2_flat_diffuse_3d_drape(client, step1_swatch_path: Path, output_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 2: HIGH-VISIBILITY FLAT-LIT 3D GEOMETRY DRAPE (TECHNICAL BLUEPRINT)")
    logger.info("==========================================================================")

    if output_path.exists():
        logger.info(f"Step 2 output exists at {output_path}. Using existing drape.")
        return output_path

    system_instruction = (
        "You are an expert AI Technical 3D Garment CAD Engineer rendering a High-Visibility Drape Blueprint.\n\n"
        "CRITICAL LIGHTING & PATTERN VISIBILITY DIRECTIVES:\n"
        "1. FLAT DIFFUSE LIGHTING ONLY: STRICTLY FORBIDDEN to add harsh shadows, specular reflections, glossy fabric glare, or dramatic studio lighting. The lighting MUST be completely flat, even, and diffuse (like a 3D CAD UV texture preview).\n"
        "2. MAXIMUM PATTERN CLARITY: Every zari motif, pallu diamond array, border, and pleat fold MUST remain 100% crisp, sharp, un-shadowed, and fully visible across the entire surface.\n"
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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes_data)
        logger.info(f"✓ STEP 2 SUCCESS: Saved refined flat-lit 3D drape to {output_path.name} ({len(bytes_data)} bytes)")
        return output_path
    raise RuntimeError(f"Step 2 failed for {output_path}")

def run_step_3_model_fusion(client, step2_drape_path: Path, moodboard_path: Path, output_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 3: HUMAN MODEL & ENVIRONMENT FUSION")
    logger.info("==========================================================================")

    if output_path.exists():
        logger.info(f"Step 3 output exists at {output_path}. Using existing catalog image.")
        return output_path

    system_instruction = (
        "You are an expert AI Luxury Fashion Photographer rendering final catalog masters.\n\n"
        "TASK - ON-MODEL CATALOG FUSION:\n"
        "1. Take the high-visibility pre-draped 3D saree cloth structure from Image 1 (Step 2 3D Technical Drape).\n"
        "2. Fuse this exact pre-draped saree onto an elegant female fashion model.\n"
        "3. Replicate the model pose, body posture, facial expression, camera framing, studio lighting, and background atmosphere from Image 2 (Moodboard Reference).\n"
        "4. Render a fitted saree blouse matching the border/body of the saree. Ensure razor-sharp 4K catalog resolution, realistic fabric drape physics, natural lighting shadows, and photorealistic human model features."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== IMAGE 1: HIGH-VISIBILITY 3D DRAPED SAREE CLOTH STRUCTURE ==="),
        types.Part.from_bytes(data=step2_drape_path.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="=== IMAGE 2: MOODBOARD REFERENCE (POSE, LIGHTING & ENVIRONMENT SOURCE - IGNORE CLOTHING) ==="),
        types.Part.from_bytes(data=moodboard_path.read_bytes(), mime_type="image/jpeg")
    ]

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes_data)
        logger.info(f"✓ STEP 3 SUCCESS: Saved final catalog image to {output_path.name} ({len(bytes_data)} bytes)")
        return output_path
    raise RuntimeError(f"Step 3 failed for {output_path}")

def process_saree(saree_folder_name: str, moodboard_file: str = "1000221736.jpg"):
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

    # Output directory structured as requested: output_sari/<saree_folder_name>/v2
    output_dir = ROOT_DIR / "output_sari" / saree_folder_name / "v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    step1_out = output_dir / f"step1_flat_swatch_{saree_folder_name}.png"
    step2_out = output_dir / f"step2_3d_draped_{saree_folder_name}.png"
    step3_out = output_dir / f"step3_final_on_model_{saree_folder_name}.png"
    qc_report_out = output_dir / f"qc_report_{saree_folder_name}.json"

    client = get_genai_client()
    inspector = VisualQCInspector()

    logger.info(f"Starting 3-Step Saree Generation for Saree '{saree_folder_name}'...")
    logger.info(f"Input images: {[img.name for img in input_images]}")
    logger.info(f"Moodboard ref: {moodboard_path.name}")
    logger.info(f"Output directory: {output_dir}")

    # Step 1
    step1_path = run_step_1_flattening(client, input_images, step1_out)

    logger.info("Pausing 30s for API rate-limiting...")
    time.sleep(30)

    # Step 2
    step2_path = run_step_2_flat_diffuse_3d_drape(client, step1_path, step2_out)

    logger.info("Pausing 30s for API rate-limiting...")
    time.sleep(30)

    # Step 3
    step3_path = run_step_3_model_fusion(client, step2_path, moodboard_path, step3_out)

    # Step 4: QC
    logger.info(f"\nExecuting Visual QC Inspector on Step 3 output against input images...")
    report = inspector.inspect(product_image_paths=input_images, generated_image_path=step3_path)
    qc_report_out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    logger.info("\n==========================================================================")
    logger.info(f" SAREE {saree_folder_name} EXECUTION COMPLETE!")
    logger.info(f" Step 1 Swatch  : {step1_path}")
    logger.info(f" Step 2 3D Drape: {step2_path}")
    logger.info(f" Step 3 Final   : {step3_path}")
    logger.info(f" QC Report      : {qc_report_out}")
    logger.info(f" QC Result      : Pass={report.pass_quality_gate}, Score={report.composite_quality_score:.2f}")
    logger.info("==========================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 3-Step Saree Pipeline on saree_unfolded")
    parser.add_argument("--saree", type=str, default="1", help="Folder name inside saree_unfolded (e.g. 1, 2, 3)")
    parser.add_argument("--moodboard", type=str, default="1000221736.jpg", help="Moodboard filename in moodboard_2")
    args = parser.parse_args()

    process_saree(args.saree, args.moodboard)
