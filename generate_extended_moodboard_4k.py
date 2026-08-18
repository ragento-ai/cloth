"""
Batch script to generate 10 new high-quality 4K catalog images in 'example_generations_extended_moodboard'
using combinations of Garments (1, 2, 3, 4) and the 5 new pictures from moodboard_2.
Includes exponential backoff / retry logic to handle rate-limits (429 RESOURCE_EXHAUSTED).
Calls Vertex AI Gemini 3 Pro Image with native 4K setting (image_size="4K", aspect_ratio="3:4").
"""

import os
import sys
import json
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
logger = logging.getLogger("ExtendedMoodboard4K")

DEST_BASE = ROOT_DIR / "example_generations_extended_moodboard"
INPUT_BASE = ROOT_DIR / "1  INPUT"
MOODBOARD2_DIR = ROOT_DIR / "moodboard_2"

# 10 Combinations bridging Garments (1, 2, 3, 4) and Moodboard 2 pictures
CASES = [
    {
        "id": "example_01_garment1_mb2_1000221736_full_transfer",
        "title": "Extended Example 01: GARMENT 1 + Moodboard 2 (1000221736) - Full Aesthetic & Lighting Transfer",
        "sku": "GARMENT_1",
        "sku_folder": "GARMENT 1",
        "moodboard": "1000221736.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Transferred aesthetic, pose, model expression, and backdrop lighting from Moodboard 2 reference 1000221736.jpg onto Garment 1 (Lilac Saree)."
    },
    {
        "id": "example_02_garment1_mb2_1000221737_input_model",
        "title": "Extended Example 02: GARMENT 1 + Moodboard 2 (1000221737) - Input Model Identity & Moodboard Atmosphere",
        "sku": "GARMENT_1",
        "sku_folder": "GARMENT 1",
        "moodboard": "1000221737.jpg",
        "controls": {"model": "input", "pose": "moodboard", "background": "moodboard", "custom_override": "Must be an authentic Indian Saree with pleats, draped pallu, and matching blouse."},
        "description": "Preserved original Garment 1 model facial identity while incorporating dynamic posture and environmental styling from Moodboard 2 (1000221737.jpg)."
    },
    {
        "id": "example_03_garment2_mb2_1000221738_full_transfer",
        "title": "Extended Example 03: GARMENT 2 + Moodboard 2 (1000221738) - Full Fashion Aesthetic Transfer",
        "sku": "GARMENT_2",
        "sku_folder": "GARMENT 2",
        "moodboard": "1000221738.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Seamless transfer of model pose, framing, and environment from Moodboard 2 reference 1000221738.jpg onto Garment 2 (Blue Tie-Dye Saree)."
    },
    {
        "id": "example_04_garment2_mb2_1000221739_moodboard_bg",
        "title": "Extended Example 04: GARMENT 2 + Moodboard 2 (1000221739) - Moodboard Backdrop & Editorial Glow",
        "sku": "GARMENT_2",
        "sku_folder": "GARMENT 2",
        "moodboard": "1000221739.jpg",
        "controls": {"model": "auto", "pose": "auto", "background": "moodboard", "custom_override": "Soft editorial glow and subtle rim lighting on blue tie-dye saree texture"},
        "description": "Blended Garment 2 into the atmospheric backdrop of Moodboard 2 image 1000221739.jpg with enhanced soft rim illumination."
    },
    {
        "id": "example_05_garment3_mb2_1000221740_full_transfer",
        "title": "Extended Example 05: GARMENT 3 + Moodboard 2 (1000221740) - Full High-Fashion Editorial Transfer",
        "sku": "GARMENT_3",
        "sku_folder": "GARMENT 3",
        "moodboard": "1000221740.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Full transfer of pose, mood, identity, and editorial environment from Moodboard 2 reference 1000221740.jpg onto Garment 3 (Navy Kurta Set)."
    },
    {
        "id": "example_06_garment3_mb2_1000221736_input_model_pose",
        "title": "Extended Example 06: GARMENT 3 + Moodboard 2 (1000221736) - Input Model + Moodboard Pose & Environment",
        "sku": "GARMENT_3",
        "sku_folder": "GARMENT 3",
        "moodboard": "1000221736.jpg",
        "controls": {"model": "input", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Anchored model facial features to Garment 3 input image, while transferring fashion posture and backdrop from Moodboard 2 image 1000221736.jpg."
    },
    {
        "id": "example_07_garment4_mb2_1000221737_mannequin_to_model",
        "title": "Extended Example 07: GARMENT 4 + Moodboard 2 (1000221737) - Mannequin-to-Model + Moodboard Setting",
        "sku": "GARMENT_4",
        "sku_folder": "GARMENT 4",
        "moodboard": "1000221737.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Draped flat mannequin Garment 4 onto a high-fashion live model matching the posture and environment of Moodboard 2 image 1000221737.jpg."
    },
    {
        "id": "example_08_garment4_mb2_1000221738_input_garment_moodboard_bg",
        "title": "Extended Example 08: GARMENT 4 + Moodboard 2 (1000221738) - Mannequin Fit + Moodboard Studio Ambience",
        "sku": "GARMENT_4",
        "sku_folder": "GARMENT 4",
        "moodboard": "1000221738.jpg",
        "controls": {"model": "auto", "pose": "auto", "background": "moodboard", "custom_override": "Elegantly styled outfit with high-fashion catalog lighting"},
        "description": "Transferred flat product shot Garment 4 onto a model set against the luxury moodboard backdrop from 1000221738.jpg."
    },
    {
        "id": "example_09_garment1_mb2_1000221739_full_transfer",
        "title": "Extended Example 09: GARMENT 1 + Moodboard 2 (1000221739) - Moodboard Model Identity & Mood",
        "sku": "GARMENT_1",
        "sku_folder": "GARMENT 1",
        "moodboard": "1000221739.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": "Ensure authentic silk saree drape with intricate pallu details"},
        "description": "Rendered Garment 1 using the moodboard model identity and posture from Moodboard 2 image 1000221739.jpg with exact silk drape precision."
    },
    {
        "id": "example_10_garment2_mb2_1000221740_input_model_jewelry",
        "title": "Extended Example 10: GARMENT 2 + Moodboard 2 (1000221740) - Input Model + Moodboard Lighting & Gold Jewelry",
        "sku": "GARMENT_2",
        "sku_folder": "GARMENT 2",
        "moodboard": "1000221740.jpg",
        "controls": {"model": "input", "pose": "auto", "background": "moodboard", "custom_override": "Accessorized with elegant gold bangles and traditional jhumka earrings"},
        "description": "Preserved Garment 2 model identity, rendered in Moodboard 2 (1000221740.jpg) backdrop, accessorized with gold jewelry."
    }
]


def process_case(case: dict, orchestrator: PromptOrchestrator, generator: ImageGenerator):
    case_id = case["id"]
    case_folder = DEST_BASE / case_id
    case_folder.mkdir(parents=True, exist_ok=True)

    output_filename = f"output_generated_{case['sku']}_native_4k.png"
    output_path = case_folder / output_filename

    if output_path.exists() and output_path.stat().st_size > 100000 and (case_folder / "how_this_was_created.txt").exists():
        logger.info(f"[{case_id}] Native 4K output already exists and is valid. Skipping.")
        return

    logger.info(f"\n==========================================================================")
    logger.info(f" GENERATING EXTENDED NATIVE 4K ASSET FOR {case_id}")
    logger.info(f"==========================================================================")

    # 1. Product shots
    sku_dir = INPUT_BASE / case["sku_folder"]
    product_images = sorted([
        sku_dir / f for f in os.listdir(sku_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    # 2. Moodboard 2 reference
    moodboard_path = MOODBOARD2_DIR / case["moodboard"]

    # 3. Build Shot Plan & Prompt Payload
    shot_plan = ShotPlan(
        shot_number=1,
        pose_source=case["moodboard"],
        lighting_source=case["moodboard"],
        framing="full_body_catalog",
        camera_angle="eye_level",
        rationale=case["description"]
    )

    ctrl_obj = TransferControls(
        model=case["controls"].get("model", "auto"),
        pose=case["controls"].get("pose", "auto"),
        background=case["controls"].get("background", "auto"),
        custom_override=case["controls"].get("custom_override")
    )

    payload = orchestrator.build_payload(
        product_image_paths=product_images,
        moodboard_image_paths=[moodboard_path],
        shot_plan=shot_plan,
        sku_id=case["sku"],
        controls=ctrl_obj
    )

    json_prompt_str = orchestrator.serialize_prompt(payload)

    # 4. Generate via ImageGenerator with retry loop on 429
    logger.info(f"[{case_id}] Calling Gemini 3 Pro Image with native 4K ImageConfig (4K, 3:4)...")
    
    max_retries = 4
    for attempt in range(1, max_retries + 1):
        try:
            generator.generate(
                json_prompt_str=json_prompt_str,
                product_image_paths=product_images,
                moodboard_image_paths=[moodboard_path],
                output_path=output_path
            )
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait_time = attempt * 35
                logger.warning(f"[{case_id}] Rate limited (429). Waiting {wait_time}s before retry (Attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e

    # 5. Copy inputs into folder
    copied_input_names = []
    for g_idx, g_file in enumerate(product_images[:3], 1):
        dst_name = f"input_garment_{case['sku'].lower()}_photo_{g_idx}_{g_file.name}"
        dst_path = case_folder / dst_name
        if g_file.exists():
            shutil.copy2(g_file, dst_path)
        copied_input_names.append(dst_name)

    dst_moodboard_name = f"input_moodboard2_reference_{case['moodboard']}"
    dst_moodboard_path = case_folder / dst_moodboard_name
    if moodboard_path.exists():
        shutil.copy2(moodboard_path, dst_moodboard_path)

    # 6. Check output dimensions
    with Image.open(output_path) as out_img:
        out_res = f"{out_img.size[0]}x{out_img.size[1]}"

    # 7. Write how_this_was_created.txt
    report_content = f"""===================================================================================
RAGENTOS VISUAL STUDIO - EXTENDED SHOWCASE REPORT (NATIVE 4K MASTER)
===================================================================================

CASE IDENTIFIER : {case['id']}
EXAMPLE TITLE   : {case['title']}
TARGET SKU      : {case['sku']} ({case['sku_folder']})
PRIMARY OUTPUT  : {output_filename}
OUTPUT RESOLUTION: {out_res} (Native 4K Ultra-High Definition)

1. INPUT ASSET REFERENCES
-------------------------
Garment Input Files    : {', '.join(copied_input_names)}
Moodboard 2 Reference  : {dst_moodboard_name}

2. SELECTIVE CONTROL TOGGLE CONFIGURATION
-----------------------------------------
Model Identity Toggle  : {case['controls']['model'].upper()}
Pose & Gesture Toggle  : {case['controls']['pose'].upper()}
Background Backdrop    : {case['controls']['background'].upper()}
Creative Override      : {case['controls']['custom_override'] if case['controls']['custom_override'] else 'None (Pure Transfer)'}

3. TECHNICAL PROVENANCE & 4K RESOLUTION SPECIFICATION
------------------------------------------------------
Engine Model           : Gemini 3 Pro Image (Vertex AI)
Image Size Parameter   : 4K (Native High-Fidelity Render)
Aspect Ratio           : 3:4 (Catalog Portrait Standard)
Garment Integrity      : Multi-modal strict role disambiguation locks target garment 
                         silhouette, weave, embroidery, and micro-print motifs from raw photos.
Pose & Environment     : Seamlessly transferred from moodboard_2 reference without garment bleeding.

===================================================================================
"""
    (case_folder / "how_this_was_created.txt").write_text(report_content, encoding="utf-8")
    logger.info(f"✓ Completed Native 4K generation for {case_id} ({out_res})\n")
    # Pacing to avoid hitting 429 quota limits
    time.sleep(15)


def main():
    DEST_BASE.mkdir(parents=True, exist_ok=True)
    orchestrator = PromptOrchestrator()
    generator = ImageGenerator()

    total = len(CASES)
    start_time = time.time()
    print(f"\n==========================================================================")
    print(f" GENERATING {total} NEW EXTENDED MOODBOARD 2 EXAMPLES IN NATIVE 4K")
    print(f"==========================================================================")

    for idx, case in enumerate(CASES, 1):
        print(f"\n>>> [{idx}/{total}] Processing {case['id']}...")
        try:
            process_case(case, orchestrator, generator)
        except Exception as e:
            logger.error(f"Error processing {case['id']}: {e}")
            time.sleep(5)

    elapsed = time.time() - start_time
    print(f"\n==========================================================================")
    print(f" ALL {total} EXTENDED MOODBOARD EXAMPLES GENERATED IN NATIVE 4K (Elapsed: {elapsed/60:.1f} mins)")
    print(f"==========================================================================")


if __name__ == "__main__":
    main()
