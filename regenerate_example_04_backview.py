"""
Single script to explicitly re-generate Example 04 in Native 4K using 49292J.jpg and 49292K.jpg (back view inputs).
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from config import settings
from models import TransferControls, ShotPlan
from src.orchestrator import PromptOrchestrator
from src.generator import ImageGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RegenExample04")

SHOWCASE_DIR = ROOT_DIR / "example_generations"
INPUT_BASE = ROOT_DIR / "1  INPUT"
MOODBOARD_BASE = ROOT_DIR / "3  MOODBOARD REFERENCE"

def regenerate_example_04():
    case_id = "example_04_garment2_full_moodboard_garden"
    case_folder = SHOWCASE_DIR / case_id
    case_folder.mkdir(parents=True, exist_ok=True)

    output_filename = "output_generated_GARMENT_2_native_4k.png"
    output_path = case_folder / output_filename

    logger.info(f"Re-generating Example 04 in Native 4K using back-view photos 49292J.jpg and 49292K.jpg...")

    # Explicitly pick 49292J.jpg and 49292K.jpg plus 49292G.jpg
    garment2_dir = INPUT_BASE / "GARMENT 2"
    selected_inputs = [
        garment2_dir / "49292J.jpg",
        garment2_dir / "49292K.jpg",
        garment2_dir / "49292G.jpg"
    ]

    moodboard_path = MOODBOARD_BASE / "K10043G.jpg"

    orchestrator = PromptOrchestrator()
    generator = ImageGenerator()

    shot_plan = ShotPlan(
        shot_number=1,
        pose_source="K10043G.jpg",
        lighting_source="K10043G.jpg",
        framing="full_body_catalog",
        camera_angle="eye_level",
        rationale="Full back-view saree drape transfer matching moodboard posture and garden environment."
    )

    ctrl_obj = TransferControls(
        model="moodboard",
        pose="moodboard",
        background="moodboard",
        custom_override="Strict back view drape matching back-view photos 49292J.jpg and 49292K.jpg showing blouse back and pallu placement."
    )

    payload = orchestrator.build_payload(
        product_image_paths=selected_inputs,
        moodboard_image_paths=[moodboard_path],
        shot_plan=shot_plan,
        sku_id="GARMENT_2",
        controls=ctrl_obj
    )

    json_prompt_str = orchestrator.serialize_prompt(payload)

    logger.info("Calling Gemini 3 Pro Image with native 4K ImageConfig (4K, 3:4)...")
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            generator.generate(
                json_prompt_str=json_prompt_str,
                product_image_paths=selected_inputs,
                moodboard_image_paths=[moodboard_path],
                output_path=output_path
            )
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait_time = attempt * 45
                logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry (Attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e

    # Clean old input files in showcase example 04 directory
    for f in os.listdir(case_folder):
        if f.startswith("input_garment_"):
            try:
                (case_folder / f).unlink()
            except Exception:
                pass

    # Copy selected back-view inputs into case folder
    copied_input_names = []
    for g_idx, g_file in enumerate(selected_inputs, 1):
        dst_name = f"input_garment_garment_2_photo_{g_idx}_{g_file.name}"
        dst_path = case_folder / dst_name
        shutil.copy2(g_file, dst_path)
        copied_input_names.append(dst_name)

    dst_moodboard_name = "input_moodboard_reference_K10043G.jpg"
    dst_moodboard_path = case_folder / dst_moodboard_name
    shutil.copy2(moodboard_path, dst_moodboard_path)

    with Image.open(output_path) as out_img:
        out_res = f"{out_img.size[0]}x{out_img.size[1]}"

    report_content = f"""===================================================================================
RAGENTOS VISUAL STUDIO - SHOWCASE GENERATION REPORT (RE-GENERATED NATIVE 4K BACK VIEW)
===================================================================================

CASE IDENTIFIER : example_04_garment2_full_moodboard_garden
EXAMPLE TITLE   : Example 04: GARMENT 2 - Full Moodboard Garden Waterfall Transfer (Back View)
TARGET SKU      : GARMENT_2 (GARMENT 2)
PRIMARY OUTPUT  : output_generated_GARMENT_2_native_4k.png
OUTPUT RESOLUTION: {out_res} (Native 4K Ultra-High Definition)

1. INPUT ASSET REFERENCES (INCLUDES BACK-VIEW RAW PHOTOS)
---------------------------------------------------------
Garment Input Files    : {', '.join(copied_input_names)}
Moodboard Reference    : input_moodboard_reference_K10043G.jpg

2. SELECTIVE CONTROL TOGGLE CONFIGURATION
-----------------------------------------
Model Identity Toggle  : MOODBOARD
Pose & Gesture Toggle  : MOODBOARD (Back-View Pose Alignment)
Background Backdrop    : MOODBOARD
Creative Override      : Strict back view drape matching back-view photos 49292J.jpg and 49292K.jpg

3. TECHNICAL PROVENANCE & 4K RESOLUTION SPECIFICATION
------------------------------------------------------
Engine Model           : Gemini 3 Pro Image (Vertex AI)
Image Size Parameter   : 4K (Native High-Fidelity Render)
Aspect Ratio           : 3:4 (Catalog Portrait Standard)
Garment Integrity      : Back-view input photos 49292J.jpg & 49292K.jpg explicitly provided to capture 
                         rear blouse neck cut, back pallu drape fold, and tie-dye motif alignment.

===================================================================================
"""
    (case_folder / "how_this_was_created.txt").write_text(report_content, encoding="utf-8")
    logger.info(f"✓ Successfully re-generated Example 04 in Native 4K with back-view photos! ({out_res})\n")

if __name__ == "__main__":
    regenerate_example_04()
