"""
Production 4K Batch Runner powered by Gemini 3.0 Pro Image (gemini-3-pro-image).
Executes catalog production for:
- Kurtis: 01, 03, 04
- Sarees: 04, 05, 06, 07, 08, 09, 10

Generates 4 distinct 4K catalog shots per SKU using the 4 specified moodboards:
1. 3  MOODBOARD REFERENCE/K10049O.jpg
2. 3  MOODBOARD REFERENCE/K10049R.jpg
3. 3  MOODBOARD REFERENCE/K10043I.jpg
4. moodboard_2/1000221736.jpg
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from models import ShotPlan
from src.patch_extractor import SemanticPatchExtractor
from src.orchestrator import PromptOrchestrator
from src.generator import ImageGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("pro_batch_production")


def run_production():
    output_base_dir = ROOT_DIR / "outputs_vtransfer_4K"
    output_base_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_base_dir / "production_manifest.json"

    # Load existing manifest if resuming
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    # Target SKUs as requested by user
    target_skus = [
        {"category": "Kurti", "id": "01"},
        {"category": "Kurti", "id": "02"},
        {"category": "Kurti", "id": "03"},
        {"category": "Kurti", "id": "04"},
        {"category": "Saree", "id": "01"},
        {"category": "Saree", "id": "02"},
        {"category": "Saree", "id": "03"},
        {"category": "Saree", "id": "04"},
        {"category": "Saree", "id": "05"},
        {"category": "Saree", "id": "06"},
        {"category": "Saree", "id": "07"},
        {"category": "Saree", "id": "08"},
        {"category": "Saree", "id": "09"},
        {"category": "Saree", "id": "10"},
    ]

    # 4 User-specified Moodboards
    moodboard_paths = [
        ROOT_DIR / "3  MOODBOARD REFERENCE" / "K10049O.jpg",
        ROOT_DIR / "3  MOODBOARD REFERENCE" / "K10049R.jpg",
        ROOT_DIR / "3  MOODBOARD REFERENCE" / "K10043I.jpg",
        ROOT_DIR / "moodboard_2" / "1000221736.jpg"
    ]

    logger.info("===================================================================")
    logger.info(f"STARTING PRODUCTION 4K BATCH RUN ({len(target_skus)} SKUs × 4 Moodboards = {len(target_skus) * 4} 4K Masters)")
    logger.info("ENGINE: Gemini 3.0 Pro Image (gemini-3-pro-image)")
    logger.info("===================================================================")

    patch_extractor = SemanticPatchExtractor(model_name="gemini-3.6-flash")
    orchestrator = PromptOrchestrator(model_name="gemini-3.7-flash")
    generator = ImageGenerator(model_name="gemini-3-pro-image")

    for sku_idx, sku in enumerate(target_skus, start=1):
        category = sku["category"]
        sku_id = sku["id"]
        sku_key = f"{category}_{sku_id}"
        sku_dir = ROOT_DIR / "inputs_vtransfer" / "18.08.2026" / category / sku_id

        if not sku_dir.exists():
            logger.warning(f"SKU directory not found: {sku_dir}. Skipping.")
            continue

        product_shots = sorted([
            p for p in sku_dir.glob("*")
            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
        ])

        if not product_shots:
            logger.warning(f"No input images found in {sku_dir}. Skipping.")
            continue

        sku_output_dir = output_base_dir / category / sku_id
        sku_output_dir.mkdir(parents=True, exist_ok=True)
        patches_dir = sku_output_dir / "extracted_patches"

        logger.info(f"\n===================================================================")
        logger.info(f"[{sku_idx}/{len(target_skus)}] PROCESSING SKU: {category}/{sku_id} ({len(product_shots)} input photos)")
        logger.info(f"===================================================================")

        # 1. Extract 4 essential micro-patches once per SKU (balanced coverage for neckline, sleeves, pants & hem)
        logger.info(f"Step 1: Extracting semantic micro-patches for {sku_key}...")
        try:
            patches = patch_extractor.extract_patches(product_shots[0], patches_dir, max_patches=4)
            patch_paths = [Path(p["file_path"]) for p in patches[:4]]
            logger.info(f"Extracted {len(patch_paths)} essential semantic patches for {sku_key}.")
        except Exception as e:
            logger.error(f"Error extracting patches for {sku_key}: {e}. Continuing with empty patches.")
            patch_paths = []

        completed_shots = manifest.get(sku_key, [])
        completed_mb_names = {s["moodboard"] for s in completed_shots}

        # 2. Iterate through each of the 4 moodboards
        for mb_idx, mb_path in enumerate(moodboard_paths, start=1):
            if not mb_path.exists():
                logger.warning(f"Moodboard {mb_path.name} not found. Skipping.")
                continue

            if mb_path.name in completed_mb_names:
                logger.info(f"Shot {mb_idx}/4 with moodboard {mb_path.name} already completed for {sku_key}. Skipping.")
                continue

            shot_output_path = sku_output_dir / f"{category}_{sku_id}_shot_{mb_idx}_{mb_path.stem}_3pro_4K.png"

            logger.info(f"\n--- Generating Shot {mb_idx}/4 for {sku_key} with Moodboard: {mb_path.name} ---")

            shot_plan = ShotPlan(
                shot_number=mb_idx,
                pose_source=mb_path.name,
                lighting_source=mb_path.name,
                framing="full_length_editorial_catalog",
                camera_angle="eye_level_studio",
                rationale=f"{category}/{sku_id} Shot {mb_idx}: Dynamic pose, styling, and set transfer from {mb_path.name}"
            )

            try:
                # Orchestrate visual spec payload
                json_payload = orchestrator.build_payload(
                    sku_id=f"{category}/{sku_id}",
                    product_image_paths=product_shots,
                    moodboard_image_paths=[mb_path],
                    shot_plan=shot_plan
                )

                # Generate 4K Master with Gemini 3.0 Pro
                gen_path, cost_info = generator.generate(
                    json_prompt_str=json_payload.model_dump_json(),
                    product_image_paths=product_shots,
                    moodboard_image_paths=[mb_path],
                    output_path=shot_output_path,
                    patch_image_paths=patch_paths
                )

                logger.info(f"✓ [{sku_key}] Shot {mb_idx} completed: {gen_path.name} ({cost_info['formatted_cost']})")

                # Record in manifest
                completed_shots.append({
                    "shot_number": mb_idx,
                    "moodboard": mb_path.name,
                    "output_file": str(gen_path),
                    "file_size_bytes": gen_path.stat().st_size,
                    "cost": cost_info,
                    "timestamp": time.time()
                })
                manifest[sku_key] = completed_shots
                manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            except Exception as e:
                logger.error(f"Failed to generate shot {mb_idx} for {sku_key}: {e}", exc_info=True)

    logger.info("\n===================================================================")
    logger.info("PRODUCTION 4K BATCH RUN FINISHED FOR ALL TARGET SKUS!")
    logger.info("===================================================================")


if __name__ == "__main__":
    run_production()
