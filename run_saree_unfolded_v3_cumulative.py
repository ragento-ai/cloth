"""
Ragento Visual Studio - Cumulative Multi-Reference Saree Pipeline (v3_cumulative)
Executes 3-Step saree generation with:
- Step 1: Clean, full continuous horizontal 2D flat-lay garment canvas (un-creased, orthographic, full textile layout).
- Step 2: High-Visibility 3D Geometry Drape Blueprint (Cumulative Inputs: Original Photos + Step 1 Flat-Lay).
- Step 3: Human Model & Moodboard Scene Fusion (Cumulative Inputs: Original Photos + Step 1 Flat-Lay + Step 2 3D Drape + Moodboard Ref).
- Pass 4: Automated Visual QC Inspector
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
logger = logging.getLogger("Saree_Pipeline_Cumulative")

def call_with_retry(client, contents, model="gemini-3.1-flash-image", max_attempts=5):
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Sending generate_content request to {model} (Attempt {attempt}/{max_attempts})...")
            res = client.models.generate_content(
                model=model,
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

def run_step_1_full_flatlay(client, input_images: list[Path], output_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 1: UNIFIED CONTINUOUS 2D FLAT-LAY TEXTILE CANVAS (GEMINI 3.1 FLASH)")
    logger.info("==========================================================================")

    if output_path.exists():
        logger.info(f"Step 1 output exists at {output_path}. Using existing flat-lay canvas.")
        return output_path

    system_instruction = (
        "You are an expert AI Textile Pattern Engineer and Orthographic Fashion Illustrator.\n\n"
        "TASK - UNIFIED 2D FULL FLAT-LAY SAREE CANVAS:\n"
        "1. De-fold, unroll, and orthographically render the entire saree as a SINGLE, UNIFIED, CONTINUOUS 2D FLAT-LAY TEXTILE spread out horizontally across a clean matte white surface.\n"
        "2. DO NOT split or crop the saree into separate isolated swatch boxes or fragmented tiles.\n"
        "3. Show the complete authentic structure and continuous flow of the saree:\n"
        "   - The decorative pallu at one end with its exact motif arrays, borders, and fringe tassels (if present in photo).\n"
        "   - The continuous running main body with its exact ground color, weave texture, and micro-motifs.\n"
        "   - The continuous running horizontal zari/embroidered borders running along the length.\n"
        "4. STRICT FIDELITY DIRECTIVE:\n"
        "   - Faithfully replicate ONLY the exact motifs visible in the reference photos (e.g. if peacocks/stripes are present, render peacocks/stripes).\n"
        "   - STRICTLY DO NOT hallucinate unrelated patterns like generic paisley/kalka, mandalas, or faux tassels unless visible in the photos.\n"
        "5. Eliminate all physical folds, harsh wrinkles, perspective skew, and shadows. Present a pristine, perfectly straight, museum-grade orthographic textile layout with 100% color, texture, and pattern fidelity."
    )

    contents = [types.Part.from_text(text=system_instruction)]
    for idx, img_path in enumerate(input_images, 1):
        contents.append(types.Part.from_text(text=f"=== ORIGINAL INPUT PHOTO {idx}: {img_path.name} (PRIMARY GROUND TRUTH FOR WEAVE, MOTIFS & COLOR) ==="))
        contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg"))

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes_data)
        logger.info(f"✓ STEP 1 SUCCESS: Saved {output_path.name} ({len(bytes_data)} bytes)")
        return output_path
    raise RuntimeError(f"Step 1 failed for {output_path}")

def run_step_2_flat_diffuse_3d_drape(client, input_images: list[Path], step1_flatlay_path: Path, output_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 2: 3D GEOMETRY DRAPE BLUEPRINT (CUMULATIVE GROUND TRUTH)")
    logger.info("==========================================================================")

    if output_path.exists():
        logger.info(f"Step 2 output exists at {output_path}. Using existing drape.")
        return output_path

    system_instruction = (
        "You are an expert AI Technical 3D Garment CAD Engineer rendering a High-Visibility Saree Drape Blueprint.\n\n"
        "TASK & DRAPING DIRECTIVES:\n"
        "1. Take the continuous 2D textile pattern from the Flat-Lay Blueprint (Image 1) and cross-reference the Original Product Photos for exact texture, sheen, and micro-motifs.\n"
        "2. Drape this exact continuous saree onto an invisible ghost mannequin in classic Nivi saree style:\n"
        "   - 6 to 8 crisp, sharp, vertically aligned waist pleats at the center bottom.\n"
        "   - Smooth, fitted waist wrap showing the continuous running border.\n"
        "   - The decorative pallu pleated and draped diagonally across the torso over the left shoulder, falling gracefully down the back/side.\n"
        "3. LIGHTING & VISIBILITY:\n"
        "   - Flat, completely even, diffuse CAD lighting. Strictly NO harsh shadows or dark occlusions.\n"
        "   - Every border motif, pallu pattern, and fabric weave must remain razor-sharp and 100% visible across all folds.\n"
        "4. Neutral matte white studio background with zero human features, zero skin, and zero face."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== REFERENCE 1: STEP 1 UNIFIED 2D FLAT-LAY BLUEPRINT (SOURCE FOR 2D CONTINUOUS PATTERN & GEOMETRY) ==="),
        types.Part.from_bytes(data=step1_flatlay_path.read_bytes(), mime_type="image/png")
    ]
    for idx, img_path in enumerate(input_images, 1):
        contents.append(types.Part.from_text(text=f"=== REFERENCE {idx+1}: ORIGINAL PRODUCT PHOTO {idx} (GROUND TRUTH FOR WEAVE FIDELITY & AUTHENTIC COLOR) ==="))
        contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg"))

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes_data)
        logger.info(f"✓ STEP 2 SUCCESS: Saved cumulative 3D drape to {output_path.name} ({len(bytes_data)} bytes)")
        return output_path
    raise RuntimeError(f"Step 2 failed for {output_path}")

def run_step_3_model_fusion(client, input_images: list[Path], step1_flatlay_path: Path, step2_drape_path: Path, moodboard_path: Path, output_path: Path) -> Path:
    logger.info("\n==========================================================================")
    logger.info(" STEP 3: HUMAN MODEL & ENVIRONMENT FUSION (FULL CUMULATIVE CONTEXT)")
    logger.info("==========================================================================")

    if output_path.exists():
        logger.info(f"Step 3 output exists at {output_path}. Using existing catalog image.")
        return output_path

    system_instruction = (
        "You are an expert AI Luxury Fashion Photographer creating a master commercial catalog image.\n\n"
        "ROLE-BASED GENERATION DIRECTIVES (CUMULATIVE CONTEXT):\n"
        "1. GARMENT SILHOUETTE & DRAPE SOURCE: Exact 3D drape structure, pleat arrangement, and shoulder pallu fall from Image 1 (Step 2 3D Drape Blueprint).\n"
        "2. GARMENT FABRIC, MOTIFS & COLOR GROUND TRUTH: Exact pattern continuity from Image 2 (Step 1 2D Flat-Lay) and original micro-weave / gold zari / color tones from the Original Product Photos (Images 3 & 4). DO NOT alter or hallucinate the garment pattern.\n"
        "3. POSE, LIGHTING & STUDIO ATMOSPHERE SOURCE: Replicate the female fashion model pose, body posture, facial expression, camera angle, realistic lighting, and aesthetic studio/outdoor environment from Image 5 (Moodboard Reference). STRICTLY IGNORE any clothing worn in Image 5.\n"
        "4. STYLING: Render an elegant, well-fitted blouse complementary to the saree border and body. Render hyper-realistic skin texture, natural cloth physics, and commercial 4K e-commerce fidelity."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== IMAGE 1: 3D DRAPED SAREE STRUCTURE (SOURCE OF TRUTH FOR 3D PLEATS & DRAPE SHAPE) ==="),
        types.Part.from_bytes(data=step2_drape_path.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="=== IMAGE 2: UNIFIED 2D FLAT-LAY BLUEPRINT (SOURCE OF TRUTH FOR 2D PATTERN CONTINUITY & BORDER SCALE) ==="),
        types.Part.from_bytes(data=step1_flatlay_path.read_bytes(), mime_type="image/png")
    ]
    for idx, img_path in enumerate(input_images, 1):
        contents.append(types.Part.from_text(text=f"=== IMAGE {idx+2}: ORIGINAL PRODUCT PHOTO {idx} (GROUND TRUTH FOR AUTHENTIC WEAVE, FABRIC TEXTURE & TRUE COLOR) ==="))
        contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg"))

    contents.append(types.Part.from_text(text=f"=== IMAGE {len(input_images)+3}: MOODBOARD REFERENCE PHOTO (SOURCE FOR MODEL POSE, LIGHTING & BACKGROUND ONLY - IGNORE CLOTHING) ==="))
    contents.append(types.Part.from_bytes(data=moodboard_path.read_bytes(), mime_type="image/jpeg"))

    bytes_data = call_with_retry(client, contents)
    if bytes_data:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes_data)
        logger.info(f"✓ STEP 3 SUCCESS: Saved final catalog image to {output_path.name} ({len(bytes_data)} bytes)")
        return output_path
    raise RuntimeError(f"Step 3 failed for {output_path}")

def process_saree_cumulative(saree_folder_name: str, moodboard_file: str = "1000221736.jpg", force: bool = False):
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

    # Output directory structured as output_sari/<saree_folder_name>/v3
    output_dir = ROOT_DIR / "output_sari" / saree_folder_name / "v3"
    output_dir.mkdir(parents=True, exist_ok=True)

    step1_out = output_dir / f"step1_unified_flatlay_{saree_folder_name}.png"
    step2_out = output_dir / f"step2_3d_draped_{saree_folder_name}.png"
    step3_out = output_dir / f"step3_final_on_model_{saree_folder_name}.png"
    qc_report_out = output_dir / f"qc_report_{saree_folder_name}.json"

    if force:
        for f in [step1_out, step2_out, step3_out, qc_report_out]:
            if f.exists():
                f.unlink()

    client = get_genai_client()
    inspector = VisualQCInspector()

    logger.info(f"Starting Cumulative 3-Step Saree Generation (Gemini 3.1 Flash) for Saree '{saree_folder_name}'...")
    logger.info(f"Input images: {[img.name for img in input_images]}")
    logger.info(f"Moodboard ref: {moodboard_path.name}")
    logger.info(f"Output directory: {output_dir}")

    # Step 1: Unified Continuous Flat-Lay
    step1_path = run_step_1_full_flatlay(client, input_images, step1_out)

    logger.info("Pausing 15s for API rate-limiting...")
    time.sleep(15)

    # Step 2: Cumulative 3D Drape (Step 1 + Original Photos)
    step2_path = run_step_2_flat_diffuse_3d_drape(client, input_images, step1_path, step2_out)

    logger.info("Pausing 15s for API rate-limiting...")
    time.sleep(15)

    # Step 3: Cumulative Final Fusion (Step 2 + Step 1 + Original Photos + Moodboard)
    step3_path = run_step_3_model_fusion(client, input_images, step1_path, step2_path, moodboard_path, step3_out)

    # Step 4: QC
    logger.info(f"\nExecuting Visual QC Inspector on Step 3 output against original input images...")
    report = inspector.inspect(product_image_paths=input_images, generated_image_path=step3_path)
    qc_report_out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    logger.info("\n==========================================================================")
    logger.info(f" SAREE {saree_folder_name} (CUMULATIVE V3 - FLASH 4K) COMPLETE!")
    logger.info(f" Step 1 Flat-Lay: {step1_path}")
    logger.info(f" Step 2 3D Drape: {step2_path}")
    logger.info(f" Step 3 Final   : {step3_path}")
    logger.info(f" QC Report      : {qc_report_out}")
    logger.info(f" QC Result      : Pass={report.pass_quality_gate}, Score={report.composite_quality_score:.2f}")
    logger.info("==========================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Cumulative 3-Step Saree Pipeline on saree_unfolded")
    parser.add_argument("--saree", type=str, default="all", help="Folder name (1, 2, 3) or 'all'")
    parser.add_argument("--moodboard", type=str, default="1000221736.jpg", help="Moodboard filename in moodboard_2")
    parser.add_argument("--force", action="store_true", help="Force regenerate all steps")
    args = parser.parse_args()

    if args.saree.lower() == "all":
        sarees = ["1", "2", "3"]
        for s in sarees:
            try:
                process_saree_cumulative(s, args.moodboard, force=args.force)
            except Exception as e:
                logger.error(f"Error processing saree {s}: {e}")
    else:
        process_saree_cumulative(args.saree, args.moodboard, force=args.force)
