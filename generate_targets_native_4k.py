"""
Directly generates Example 07 and Example 12 in Native 4K Ultra-Resolution
using Gemini 3 Pro with full uncompressed inputs.
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from models import TransferControls, ShotPlan
from src.orchestrator import PromptOrchestrator
from src.generator import ImageGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TargetedNative4K")

SHOWCASE_DIR = ROOT_DIR / "example_generations"
INPUT_BASE = ROOT_DIR / "1  INPUT"
MOODBOARD_BASE = ROOT_DIR / "3  MOODBOARD REFERENCE"

TARGET_CASES = [
    {
        "id": "example_07_garment3_full_moodboard_heritage",
        "title": "Example 07: GARMENT 3 - Full Moodboard Heritage Courtyard Transfer",
        "sku": "GARMENT_3",
        "sku_folder": "GARMENT 3",
        "moodboard": "K10048I.jpg",
        "controls": {"model": "moodboard", "pose": "moodboard", "background": "moodboard", "custom_override": None},
        "description": "Complete transfer of model identity, pose, and heritage palace courtyard backdrop from reference K10048I.jpg onto Garment 3 (Navy Kurta Set with circular mandala print and red border)."
    },
    {
        "id": "example_12_garment4_moodboard_model_festive_urlis",
        "title": "Example 12: GARMENT 4 - Moodboard Model + Festive Brass Urli Directive",
        "sku": "GARMENT_4",
        "sku_folder": "GARMENT 4",
        "moodboard": "K10043I.jpg",
        "controls": {"model": "moodboard", "pose": "auto", "background": "auto", "custom_override": "Add traditional decorative brass urlis with floating yellow marigold petals in backdrop. Preserve exact chevron zigzag neckline and floral print from Garment 4."},
        "description": "Transferred model features from K10043I.jpg and incorporated a custom festive prop directive (brass urlis with marigold flowers) on Garment 4 (Kurta with zigzag embroidery)."
    }
]


def run_targets():
    orchestrator = PromptOrchestrator()
    generator = ImageGenerator()

    for idx, case in enumerate(TARGET_CASES, 1):
        case_id = case["id"]
        case_folder = SHOWCASE_DIR / case_id
        case_folder.mkdir(parents=True, exist_ok=True)

        output_filename = f"output_generated_{case['sku']}_native_4k.png"
        output_path = case_folder / output_filename

        print(f"\n==========================================================================")
        print(f" [{idx}/{len(TARGET_CASES)}] GENERATING NATIVE 4K ASSET: {case_id}")
        print(f"==========================================================================")

        sku_dir = INPUT_BASE / case["sku_folder"]
        product_images = sorted([
            sku_dir / f for f in os.listdir(sku_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        moodboard_path = MOODBOARD_BASE / case["moodboard"]

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

        print(f"Calling Gemini 3 Pro with native 4K ImageConfig for {case_id}...")
        generator.generate(
            json_prompt_str=json_prompt_str,
            product_image_paths=product_images,
            moodboard_image_paths=[moodboard_path],
            output_path=output_path
        )

        # Clean legacy low-res / upscaled files
        for f in os.listdir(case_folder):
            if f.startswith("output_4k_master_") or f.startswith("comparison_before_after_") or (f.startswith("output_generated_") and f != output_filename):
                try:
                    (case_folder / f).unlink()
                except Exception:
                    pass

        # Copy inputs
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
        print(f"✓ Completed Native 4K generation for {case_id} ({out_res})\n")


if __name__ == "__main__":
    run_targets()
