"""
Main CLI entry point for Mirchi Fashion Gemini Visual Generation & Quality Control System.
Powered by Gemini 3.6 Flash (Orchestration & Inspection) + Gemini 3 Pro Image (Generation).
"""

import sys
import json
import logging
from pathlib import Path
from typing import List

from config import settings
from src.pipeline import PipelineManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("==========================================================================")
    logger.info(" Mirchi Fashion Gemini 3.6 Flash Multi-Pose Generation & QC System        ")
    logger.info("==========================================================================")

    input_base_dir = settings.INPUT_DIR
    moodboard_dir = settings.MOODBOARD_DIR
    output_dir = settings.OUTPUT_DIR

    if not input_base_dir.exists():
        logger.error(f"Input base directory not found at {input_base_dir}")
        sys.exit(1)

    # Gather moodboard reference images
    moodboard_images = sorted([
        p for p in moodboard_dir.glob("*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
    ])
    logger.info(f"Found {len(moodboard_images)} moodboard reference images in {moodboard_dir}")

    # Gather SKU garment subdirectories
    garment_dirs = sorted([d for d in input_base_dir.iterdir() if d.is_dir()])
    if not garment_dirs:
        logger.warning(f"No garment directories found in {input_base_dir}")
        return

    logger.info(f"Found {len(garment_dirs)} SKU garment directories: {[d.name for d in garment_dirs]}")

    pipeline = PipelineManager()
    summary_results = []

    # Target SKUs: Process GARMENT 2 and GARMENT 4 with Multi-Pose Catalog Generation (3 shots per SKU)
    for garment_dir in garment_dirs:
        sku_id = garment_dir.name.replace(" ", "_")
        product_images = sorted([
            p for p in garment_dir.glob("*")
            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
        ])

        if not product_images:
            logger.warning(f"Skipping {sku_id}: No images found in {garment_dir}")
            continue

        # Generate 3 intelligent catalog shots for GARMENT 2 and GARMENT 4
        if sku_id in ["GARMENT_2", "GARMENT_4"]:
            logger.info(f"\nProcessing SKU: {sku_id} (Gemini 3.6 Flash 3-Shot Catalog Generation)")
            sku_results = pipeline.process_sku_multi_pose(
                sku_id=sku_id,
                product_image_paths=product_images,
                moodboard_image_paths=moodboard_images,
                requested_num_shots=3
            )
            summary_results.extend(sku_results)
        else:
            logger.info(f"\nProcessing SKU: {sku_id} (Single Shot Generation)")
            sku_results = pipeline.process_sku_multi_pose(
                sku_id=sku_id,
                product_image_paths=product_images,
                moodboard_image_paths=moodboard_images,
                requested_num_shots=1
            )
            summary_results.extend(sku_results)

    # Save Batch Execution Summary
    summary_path = output_dir / "batch_execution_summary.json"
    summary_path.write_text(json.dumps(summary_results, indent=2), encoding="utf-8")

    logger.info("\n==========================================================================")
    logger.info(f" Batch Execution Completed! Summary saved to {summary_path}")
    logger.info("==========================================================================")


if __name__ == "__main__":
    main()
