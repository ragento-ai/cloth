"""
Automated Batch Processor for V-Transfer Garments with Smart Early-Stopping Critic Loop in Native 4K.
Processes all extracted Kurti and Saree garments, stopping immediately when an asset is approved by the Visual Critic.
"""

import sys
import json
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from config import settings
from models import JSONPromptPayload, GarmentIdentitySpec, CompositionSpec, AestheticSpec, ShotPlan, VisualCriticFeedback, TransferControls
from src.vertex_client import get_genai_client
from src.orchestrator import PromptOrchestrator
from src.generator import ImageGenerator
from src.critic import VisualCritic
from src.inspector import VisualQCInspector
from src.cost_tracker import calculate_step_cost, aggregate_costs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("vtransfer_batch")


def get_all_moodboards() -> List[Path]:
    """Combines moodboards from '3  MOODBOARD REFERENCE' and 'moodboard_2'."""
    mb_dir_1 = ROOT_DIR / "3  MOODBOARD REFERENCE"
    mb_dir_2 = ROOT_DIR / "moodboard_2"

    mbs = []
    if mb_dir_1.exists():
        mbs.extend(sorted([p for p in mb_dir_1.glob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]))
    if mb_dir_2.exists():
        mbs.extend(sorted([p for p in mb_dir_2.glob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]))

    logger.info(f"Loaded {len(mbs)} combined moodboard references ({len(list(mb_dir_1.glob('*')))} from Ref 1, {len(list(mb_dir_2.glob('*')))} from Ref 2).")
    return mbs


def plan_diverse_shots(input_photos: List[Path], moodboards: List[Path], garment_type: str, garment_id: str) -> List[Dict[str, Any]]:
    """Plans N distinct commercial shots matching the number of input photos with varied framing and distinct moodboards."""
    num_shots = len(input_photos)
    
    # Shuffle or cycle moodboards to ensure diverse mixing across garments
    seed_val = sum(ord(c) for c in f"{garment_type}_{garment_id}")
    rng = random.Random(seed_val)
    sampled_mbs = rng.sample(moodboards, min(num_shots, len(moodboards)))
    if len(sampled_mbs) < num_shots:
        sampled_mbs += rng.choices(moodboards, k=num_shots - len(sampled_mbs))

    # Standard e-commerce catalog shot progression
    framings = [
        "full_body_front_catalog",
        "three_quarter_standing_lifestyle",
        "side_angle_drape_silhouette",
        "medium_close_up_textile_detail",
        "relaxed_editorial_posture"
    ]

    plans = []
    for i in range(num_shots):
        framing = framings[i % len(framings)]
        mb = sampled_mbs[i]
        input_ref = input_photos[i]
        
        plans.append({
            "shot_number": i + 1,
            "framing": framing,
            "moodboard_path": mb,
            "primary_input_photo": input_ref,
            "rationale": f"E-commerce commercial catalog angle {i + 1} ({framing}) using moodboard {mb.name}"
        })

    return plans


def run_garment_pipeline(
    garment_folder: Path,
    category: str,
    garment_id: str,
    all_moodboards: List[Path],
    output_base_dir: Path,
    generator: ImageGenerator,
    critic: VisualCritic,
    inspector: VisualQCInspector,
    manifest_path: Path
) -> List[Dict[str, Any]]:
    """Processes a single garment: generates N 4K shots and stops immediately upon approval."""
    
    input_photos = sorted([
        p for p in garment_folder.glob("*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
    ])
    
    if not input_photos:
        logger.warning(f"No input images found in {garment_folder}. Skipping.")
        return []

    garment_output_dir = output_base_dir / category / garment_id
    garment_output_dir.mkdir(parents=True, exist_ok=True)

    shot_plans = plan_diverse_shots(input_photos, all_moodboards, category, garment_id)
    logger.info(f"=== PROCESSING GARMENT: {category}/{garment_id} ({len(input_photos)} Input Photos -> {len(shot_plans)} 4K Catalog Shots) ===")

    # Load existing manifest to resume if interrupted
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    garment_key = f"{category}_{garment_id}"
    completed_shots = manifest.get(garment_key, [])
    completed_numbers = {s["shot_number"] for s in completed_shots}

    results = list(completed_shots)
    orchestrator = PromptOrchestrator()

    for plan in shot_plans:
        shot_num = plan["shot_number"]
        if shot_num in completed_numbers:
            logger.info(f"Shot {shot_num}/{len(shot_plans)} already completed for {garment_key}. Skipping.")
            continue

        logger.info(f"\n--- Starting Shot {shot_num}/{len(shot_plans)} ({plan['framing']}) for {category}/{garment_id} ---")
        logger.info(f"Assigned Moodboard: {plan['moodboard_path'].name} | Input Anchor: {plan['primary_input_photo'].name}")

        step_costs = []
        shot_stem = f"shot_{shot_num}_{plan['framing']}"
        
        # 1. Build Orchestrator Prompt Payload via 3-Way Toggle System (Model Decides: Auto)
        shot_plan_obj = ShotPlan(
            shot_number=shot_num,
            pose_source=plan["moodboard_path"].name,
            lighting_source=plan["moodboard_path"].name,
            framing=plan["framing"],
            camera_angle="eye_level_studio",
            rationale=plan["rationale"]
        )
        controls = TransferControls(
            model="auto",
            pose="auto",
            background="auto",
            resolution="4096x4096"
        )
        payload = orchestrator.build_payload(
            product_image_paths=input_photos,
            moodboard_image_paths=[plan["moodboard_path"]],
            shot_plan=shot_plan_obj,
            sku_id=f"{category}_{garment_id}",
            controls=controls
        )
        json_prompt_str = orchestrator.serialize_prompt(payload)

        initial_draft_path = garment_output_dir / f"{shot_stem}_draft_0.png"
        
        # 2. Initial 4K Generation
        logger.info(f"Generating initial 4K draft for shot {shot_num}...")
        _, gen_cost = generator.generate(
            json_prompt_str=json_prompt_str,
            product_image_paths=input_photos,
            moodboard_image_paths=[plan["moodboard_path"]],
            output_path=initial_draft_path
        )
        gen_cost["step_name"] = "Initial 4K Generation"
        step_costs.append(gen_cost)

        current_bytes = initial_draft_path.read_bytes()
        critique_history = []
        last_critique = None
        max_iterations = 2

        # 3. Dynamic Critic Loop with Early Stopping on Approval
        for iter_num in range(1, max_iterations + 1):
            logger.info(f">> Running Visual Critic Evaluation (Pass {iter_num}/{max_iterations}) for Shot {shot_num}...")

            # 3a. Visual Critic Evaluation (Gemini 3.7 Flash with fallback to 3.6 Flash)
            critique, crit_cost = critic.evaluate(
                product_image_paths=input_photos,
                generated_img_bytes=current_bytes,
                user_feedback="Preserve exact ground fabric weave, motif alignment, and border geometry authentic to ground truth product photos."
            )
            crit_cost["step_name"] = f"Visual Critic Pass {iter_num}"
            step_costs.append(crit_cost)
            last_critique = critique

            crit_data = critique.model_dump()
            crit_data["iteration"] = iter_num
            crit_data["cost_metrics"] = crit_cost
            critique_history.append(crit_data)

            # Save critique JSON log
            crit_log_file = garment_output_dir / f"{shot_stem}_critique_pass_{iter_num}.json"
            crit_log_file.write_text(critique.model_dump_json(indent=2), encoding="utf-8")

            logger.info(f"Pass {iter_num} Critic Score: {critique.overall_fidelity_score:.2f} | Approved: {critique.approved}")
            if critique.structural_hallucinations:
                logger.info(f"Pass {iter_num} Detected Defects: {critique.structural_hallucinations}")

            # SMART EARLY EXIT: If approved with high fidelity and no structural hallucinations, stop immediately!
            if critique.approved and critique.overall_fidelity_score >= 0.90 and not critique.structural_hallucinations:
                logger.info(f"🎉 Asset approved by Visual Critic on Pass {iter_num} (Score: {critique.overall_fidelity_score:.2f})! Skipping further refinement.")
                break

            # 3b. Refinement Generation only if defects or unapproved
            if iter_num <= max_iterations:
                logger.info(f"Applying refinement directives to correct defects on Pass {iter_num}...")
                iter_output_path = garment_output_dir / f"{shot_stem}_refined_pass_{iter_num}.png"
                _, ref_cost = generator.refine(
                    product_image_paths=input_photos,
                    moodboard_image_path=plan["moodboard_path"],
                    previous_image_bytes=current_bytes,
                    critic_instructions=critique.refinement_instructions,
                    user_feedback="",
                    output_path=iter_output_path
                )
                ref_cost["step_name"] = f"4K Refinement Gen Pass {iter_num}"
                step_costs.append(ref_cost)

                current_bytes = iter_output_path.read_bytes()

        # 4. Save Final Master Image
        final_master_path = garment_output_dir / f"{shot_stem}_FINAL_4K.png"
        final_master_path.write_bytes(current_bytes)
        logger.info(f"✓ Saved Final 4K Master to: {final_master_path.name}")

        # 5. Final Visual QC Inspection (Gemini 3.7 Flash)
        qc_report, qc_cost = inspector.inspect(
            product_image_paths=input_photos,
            generated_image_path=final_master_path
        )
        qc_cost["step_name"] = "Final QC Inspection (3.7 Flash)"
        step_costs.append(qc_cost)

        # Aggregate total shot cost
        total_shot_cost = aggregate_costs(step_costs)
        logger.info(f"💰 Shot {shot_num} Total Cost: {total_shot_cost['formatted_total_cost']} ({total_shot_cost['total_tokens']} tokens)")

        shot_record = {
            "category": category,
            "garment_id": garment_id,
            "shot_number": shot_num,
            "framing": plan["framing"],
            "moodboard": plan["moodboard_path"].name,
            "primary_input_photo": plan["primary_input_photo"].name,
            "final_image_path": str(final_master_path),
            "qc_score": qc_report.composite_quality_score,
            "pass_quality_gate": qc_report.pass_quality_gate,
            "cost_metrics": total_shot_cost,
            "critique_history": critique_history,
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        results.append(shot_record)
        manifest[garment_key] = results
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Brief pause between shots for API rate limit smoothing
        time.sleep(3)

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run V-Transfer 4K Batch Generation (V2)")
    parser.add_argument("--target", type=str, default="Kurti/01", help="Target garment to run e.g. 'Kurti/01' or 'all'")
    parser.add_argument("--version", type=str, default="v2", help="Output version directory name (default: 'v2')")
    args = parser.parse_args()

    logger.info("===================================================================")
    logger.info(f"V-TRANSFER BATCH PROCESSOR (VERSION: {args.version}, TARGET: {args.target})")
    logger.info("===================================================================")

    input_root = ROOT_DIR / "inputs_vtransfer" / "18.08.2026"
    output_base_dir = ROOT_DIR / "batch_vtransfer_output" / args.version
    output_base_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_base_dir / "progress_manifest.json"

    all_moodboards = get_all_moodboards()
    if not all_moodboards:
        logger.error("No moodboard reference images found.")
        return

    generator = ImageGenerator(model_name="gemini-3.1-flash-image")
    critic = VisualCritic(model_name="gemini-3.7-flash")
    inspector = VisualQCInspector(model_name="gemini-3.7-flash")

    # Discover all garments
    garments = []
    target_list = [t.strip().lower() for t in args.target.split(",")]
    for cat_dir in sorted(input_root.iterdir()):
        if cat_dir.is_dir():
            category = cat_dir.name
            for g_dir in sorted(cat_dir.iterdir()):
                if g_dir.is_dir():
                    garment_tag = f"{category}/{g_dir.name}"
                    if "all" not in target_list and garment_tag.lower() not in target_list:
                        continue
                    garments.append((category, g_dir.name, g_dir))

    logger.info(f"Filtered {len(garments)} garment(s) to process for target(s): {target_list}")

    total_shots_all = 0
    total_cost_all = 0.0

    for idx, (category, garment_id, garment_folder) in enumerate(garments, 1):
        logger.info(f"\n===================================================================")
        logger.info(f"GARMENT {idx}/{len(garments)}: {category}/{garment_id}")
        logger.info(f"===================================================================")
        
        garment_results = run_garment_pipeline(
            garment_folder=garment_folder,
            category=category,
            garment_id=garment_id,
            all_moodboards=all_moodboards,
            output_base_dir=output_base_dir,
            generator=generator,
            critic=critic,
            inspector=inspector,
            manifest_path=manifest_path
        )
        total_shots_all += len(garment_results)
        for r in garment_results:
            total_cost_all += r.get("cost_metrics", {}).get("total_cost_usd", 0.0)

    logger.info("\n===================================================================")
    logger.info(f"COMPLETED RUN FOR {args.version.upper()}!")
    logger.info(f"Total Completed 4K Master Shots: {total_shots_all}")
    logger.info(f"Total Spend: ${total_cost_all:.4f}")
    logger.info(f"Output Master Directory: {output_base_dir}")
    logger.info("===================================================================")


if __name__ == "__main__":
    main()
