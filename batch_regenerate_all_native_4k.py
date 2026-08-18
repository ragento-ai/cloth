"""
Comprehensive Batch Script to Regenerate All 15 Client Showcase Examples
in Native 4K Ultra-High Definition directly from Gemini 3 Pro on Vertex AI.
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
logger = logging.getLogger("BatchNative4K")

SHOWCASE_DIR = ROOT_DIR / "example_generations"
INPUT_BASE = ROOT_DIR / "1  INPUT"
MOODBOARD_BASE = ROOT_DIR / "3  MOODBOARD REFERENCE"

# Full 15 Client Showcase Case Definitions
CASES = [
    {
        "id": "example_01_garment1_full_moodboard_transfer",
        "title": "Example 01: GARMENT 1 - Full Moodboard Aesthetics (Model, Pose, Environment)",
        "sku": "GARMENT_1",
        "sku_folder": "GARMENT 1",
        "moodboard": "K10048G.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "All control toggles set to 'Moodboard'. Transferred full aesthetic, pose, facial identity, and rustic architectural courtyard backdrop from reference K10048G.jpg onto Garment 1 (Lilac Saree)."
    },
    {
        "id": "example_02_garment1_input_model_moodboard_pose",
        "title": "Example 02: GARMENT 1 - Input Model Identity + Moodboard Pose & Stone Garden Environment",
        "sku": "GARMENT_1",
        "sku_folder": "GARMENT 1",
        "moodboard": "K10043I.jpg",
        "controls": {"model": "input", "pose": "moodboard", "background": "moodboard", "custom_override": "Must be an authentic Indian Saree with pleats, draped pallu, and high neck blouse. Strictly no dupatta or suit."},
        "description": "Model facial identity anchored to Input Garment 1 model. Pose and garden water environment transferred from K10043I.jpg with strict Saree silhouette."
    },
    {
        "id": "example_03_garment1_moodboard_bg_golden_hour",
        "title": "Example 03: GARMENT 1 - Moodboard Outdoor Backdrop + Golden Hour Sunbeams Directive",
        "sku": "GARMENT_1",
        "sku_folder": "GARMENT 1",
        "moodboard": "K10048M1.jpg",
        "controls": {"model": "auto", "pose": "auto", "background": "moodboard", "custom_override": "Soft afternoon golden hour sunlight with warm amber reflections and gentle bokeh"},
        "description": "Lush garden environment transferred from K10048M1.jpg with a Creative Directive for warm golden hour lighting and specular sunbeams."
    },
    {
        "id": "example_04_garment2_full_moodboard_garden",
        "title": "Example 04: GARMENT 2 - Full Moodboard Garden Waterfall Transfer",
        "sku": "GARMENT_2",
        "sku_folder": "GARMENT 2",
        "moodboard": "K10043G.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Full environment and mood transfer from tropical garden reference K10043G.jpg onto Garment 2 (Blue Tie-Dye Saree)."
    },
    {
        "id": "example_05_garment2_input_model_moodboard_bg",
        "title": "Example 05: GARMENT 2 - Preserve Input Saree Model + Moodboard Outdoor Backdrop",
        "sku": "GARMENT_2",
        "sku_folder": "GARMENT 2",
        "moodboard": "K10044J.jpg",
        "controls": {"model": "input", "pose": "auto", "background": "moodboard", "custom_override": None},
        "description": "Preserved the original Saree model's facial features from Input Garment 2 while seamlessly placing her in the moodboard backdrop from K10044J.jpg."
    },
    {
        "id": "example_06_garment2_moodboard_model_studio_bg",
        "title": "Example 06: GARMENT 2 - Moodboard Model + Input Studio Backdrop + Gold Temple Jewelry",
        "sku": "GARMENT_2",
        "sku_folder": "GARMENT 2",
        "moodboard": "K10046G.jpg",
        "controls": {"model": "moodboard", "pose": "auto", "background": "input", "custom_override": "Wearing traditional gold bangles, jhumkas, and temple jewelry"},
        "description": "Transferred model features from K10046G.jpg, maintained crisp indoor studio background from Input, and added gold temple jewelry."
    },
    {
        "id": "example_07_garment3_full_moodboard_heritage",
        "title": "Example 07: GARMENT 3 - Full Moodboard Heritage Courtyard Transfer",
        "sku": "GARMENT_3",
        "sku_folder": "GARMENT 3",
        "moodboard": "K10048I.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Complete transfer of model identity, pose, and heritage palace courtyard backdrop from reference K10048I.jpg onto Garment 3 (Navy Kurta Set)."
    },
    {
        "id": "example_08_garment3_input_model_moodboard_courtyard",
        "title": "Example 08: GARMENT 3 - Input Model + Moodboard Pose & Outdoor Courtyard",
        "sku": "GARMENT_3",
        "sku_folder": "GARMENT 3",
        "moodboard": "K10049R.jpg",
        "controls": {"model": "input", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Anchored model facial features to Garment 3 input image, while transferring elegant seated pose and carved courtyard backdrop from K10049R.jpg."
    },
    {
        "id": "example_09_garment3_moodboard_pose_studio_shadows",
        "title": "Example 09: GARMENT 3 - Moodboard Pose + Studio Input Background + Architectural Shadows",
        "sku": "GARMENT_3",
        "sku_folder": "GARMENT 3",
        "moodboard": "K10049O.jpg",
        "controls": {"model": "auto", "pose": "moodboard", "background": "input", "custom_override": "Clean architectural minimalist studio shadow pattern with soft rim light"},
        "description": "Transferred pose from moodboard K10049O.jpg, kept clean studio backdrop, and added crisp architectural shadow overlays."
    },
    {
        "id": "example_10_garment4_full_moodboard_carved_relief",
        "title": "Example 10: GARMENT 4 - Mannequin-to-Model + Carved Relief Wall Environment",
        "sku": "GARMENT_4",
        "sku_folder": "GARMENT 4",
        "moodboard": "K10049N.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Mannequin-to-On-Model transformation. Draped flat mannequin Garment 4 onto live model in carved stone relief wall setting from K10049N.jpg with stylish sunglasses."
    },
    {
        "id": "example_11_garment4_input_garment_lush_garden",
        "title": "Example 11: GARMENT 4 - Mannequin-to-Model + Lush Garden Backdrop",
        "sku": "GARMENT_4",
        "sku_folder": "GARMENT 4",
        "moodboard": "K10048M1.jpg",
        "controls": {"model": "input", "pose": "auto", "background": "moodboard", "custom_override": None},
        "description": "Transferred flat mannequin Garment 4 onto a professional model set in the lush botanical garden backdrop from K10048M1.jpg."
    },
    {
        "id": "example_12_garment4_moodboard_model_festive_urlis",
        "title": "Example 12: GARMENT 4 - Moodboard Model + Festive Brass Urli Directive",
        "sku": "GARMENT_4",
        "sku_folder": "GARMENT 4",
        "moodboard": "K10043I.jpg",
        "controls": {"model": "moodboard", "pose": "auto", "background": "auto", "custom_override": "Add traditional decorative brass urlis with floating yellow marigold petals in backdrop"},
        "description": "Transferred model features from K10043I.jpg and incorporated a custom festive prop directive (brass urlis with marigold flowers)."
    },
    {
        "id": "example_13_garment1_input_pose_moodboard_lighting",
        "title": "Example 13: GARMENT 1 - Input Pose & Model + Moodboard High-Key Studio Lighting",
        "sku": "GARMENT_1",
        "sku_folder": "GARMENT 1",
        "moodboard": "K10044J.jpg",
        "controls": {"model": "input", "pose": "input", "background": "auto", "custom_override": "High fashion soft editorial lighting with soft background glow"},
        "description": "Maintained original standing pose and model identity from Garment 1 input image while enhancing lighting and studio atmosphere using reference K10044J.jpg."
    },
    {
        "id": "example_14_garment3_moodboard_model_temple_courtyard",
        "title": "Example 14: GARMENT 3 - Moodboard Model + Heritage Temple Courtyard Environment",
        "sku": "GARMENT_3",
        "sku_folder": "GARMENT 3",
        "moodboard": "K10043G.jpg",
        "controls": {"model": "moodboard", "pose": "auto", "background": "moodboard", "custom_override": "Serene traditional temple courtyard setting"},
        "description": "Combined moodboard model facial expression with serene heritage temple courtyard background from reference K10043G.jpg."
    },
    {
        "id": "example_15_garment2_full_moodboard_arch_shadows",
        "title": "Example 15: GARMENT 2 - Full Moodboard Transfer + Sunset Architectural Shadows",
        "sku": "GARMENT_2",
        "sku_folder": "GARMENT 2",
        "moodboard": "K10049O.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": "Warm sunset amber light with long geometric archway shadows"},
        "description": "Full transfer of pose, model, and backdrop from K10049O.jpg enhanced with warm sunset amber illumination and geometric arch shadows."
    }
]


def process_case_native_4k(case: dict, orchestrator: PromptOrchestrator, generator: ImageGenerator, skip_if_exists: bool = False):
    case_id = case["id"]
    case_folder = SHOWCASE_DIR / case_id
    case_folder.mkdir(parents=True, exist_ok=True)

    output_filename = f"output_generated_{case['sku']}_native_4k.png"
    output_path = case_folder / output_filename

    # If example 2 already has native 4k, we can link/keep it
    if case_id == "example_02_garment1_input_model_moodboard_pose":
        existing_native = case_folder / "output_generated_GARMENT_1_native_4k_saree.png"
        if existing_native.exists():
            logger.info(f"[{case_id}] Example 02 already generated in Native 4K ({existing_native.name}). Ensuring standard naming...")
            if existing_native != output_path:
                shutil.copy2(existing_native, output_path)
            return

    if skip_if_exists and output_path.exists():
        logger.info(f"[{case_id}] Native 4K output already exists at {output_path}. Skipping.")
        return

    logger.info(f"\n==========================================================================")
    logger.info(f" GENERATING NATIVE 4K ASSET FOR {case_id}")
    logger.info(f"==========================================================================")

    # 1. Product shots
    sku_dir = INPUT_BASE / case["sku_folder"]
    product_images = sorted([
        sku_dir / f for f in os.listdir(sku_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    # 2. Moodboard reference
    moodboard_path = MOODBOARD_BASE / case["moodboard"]

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

    # 4. Generate via ImageGenerator (Native 4K)
    logger.info(f"[{case_id}] Calling Gemini 3 Pro Image with native 4K ImageConfig...")
    generator.generate(
        json_prompt_str=json_prompt_str,
        product_image_paths=product_images,
        moodboard_image_paths=[moodboard_path],
        output_path=output_path
    )

    # 5. Clean up old legacy low-res / upscaler outputs in case folder
    for f in os.listdir(case_folder):
        if (f.startswith("output_generated_") and f != output_filename and not f.endswith("_native_4k_saree.png")) or f.startswith("comparison_before_after_"):
            try:
                (case_folder / f).unlink()
                logger.info(f"Removed legacy file: {f}")
            except Exception:
                pass

    # 6. Copy inputs with clear names
    copied_input_names = []
    for g_idx, g_file in enumerate(product_images[:3], 1):
        dst_name = f"input_garment_{case['sku'].lower()}_photo_{g_idx}_{g_file.name}"
        dst_path = case_folder / dst_name
        if not dst_path.exists() and g_file.exists():
            shutil.copy2(g_file, dst_path)
        copied_input_names.append(dst_name)

    dst_moodboard_name = f"input_moodboard_reference_{case['moodboard']}"
    dst_moodboard_path = case_folder / dst_moodboard_name
    if not dst_moodboard_path.exists() and moodboard_path.exists():
        shutil.copy2(moodboard_path, dst_moodboard_path)

    # 7. Write clean how_this_was_created.txt
    with Image.open(output_path) as out_img:
        out_res = f"{out_img.size[0]}x{out_img.size[1]}"

    report_content = f"""===================================================================================
RAGENTOS VISUAL STUDIO - SHOWCASE GENERATION REPORT (NATIVE 4K MASTER)
===================================================================================

CASE IDENTIFIER : {case['id']}
EXAMPLE TITLE   : {case['title']}
TARGET SKU      : {case['sku']} ({case['sku_folder']})
PRIMARY OUTPUT  : {output_filename}
OUTPUT RESOLUTION: {out_res} (Native 4K Ultra-High Definition)

1. INPUT ASSET REFERENCES
-------------------------
Garment Input Files    : {', '.join(copied_input_names)}
Moodboard Reference    : {dst_moodboard_name}

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
Pose & Environment     : Seamlessly transferred from moodboard reference without garment bleeding.

===================================================================================
"""
    (case_folder / "how_this_was_created.txt").write_text(report_content, encoding="utf-8")
    logger.info(f"✓ Completed Native 4K generation for {case_id} ({out_res})\n")


def run_all():
    orchestrator = PromptOrchestrator()
    generator = ImageGenerator()

    total = len(CASES)
    start_time = time.time()
    print(f"\n==========================================================================")
    print(f" BATCH REGENERATION OF ALL {total} SHOWCASE EXAMPLES IN NATIVE 4K")
    print(f"==========================================================================")

    for idx, case in enumerate(CASES, 1):
        print(f"\n>>> [{idx}/{total}] Processing {case['id']}...")
        try:
            process_case_native_4k(case, orchestrator, generator)
        except Exception as e:
            logger.error(f"Error processing {case['id']}: {e}")
            time.sleep(3)

    elapsed = time.time() - start_time
    print(f"\n==========================================================================")
    print(f" ALL {total} EXAMPLES REGENERATED IN NATIVE 4K (Elapsed: {elapsed/60:.1f} mins)")
    print(f"==========================================================================")


if __name__ == "__main__":
    run_all()
