"""
Pipeline Manager: Coordinates Pass 1 Orchestration, Gemini 3.6 Flash Moodboard Shot Planning, Multi-Reference Generation, Pass 2 Inspection, and Quality Gate Routing.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from config import settings
from models import JSONPromptPayload, VisualQCReport, ShotPlan
from src.orchestrator import PromptOrchestrator
from src.generator import ImageGenerator
from src.inspector import VisualQCInspector

logger = logging.getLogger(__name__)


class PipelineManager:
    """End-to-end Manager for SKU Visual Generation and QC pipeline via Vertex AI."""

    def __init__(self, max_retries: int = None):
        self.max_retries = max_retries or settings.MAX_RETRIES

        self.orchestrator = PromptOrchestrator()
        self.generator = ImageGenerator()
        self.inspector = VisualQCInspector()

    def process_sku_shot(
        self,
        sku_id: str,
        product_image_paths: List[Path],
        moodboard_image_paths: List[Path],
        shot_plan: ShotPlan,
        output_dir: Path = None,
        controls: Any = None,
        batch_id: str = None,
        batch_label: str = None,
    ) -> Dict[str, Any]:
        """Runs complete generation, QC, and routing pipeline for a single planned shot."""

        output_dir = output_dir or settings.OUTPUT_DIR
        approved_dir = settings.APPROVED_DIR / sku_id
        review_dir = settings.HUMAN_REVIEW_DIR / sku_id

        output_dir.mkdir(parents=True, exist_ok=True)
        approved_dir.mkdir(parents=True, exist_ok=True)
        review_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        shot_tag = f"shot_{shot_plan.shot_number}_{timestamp_str}"
        logger.info(f"--- Pipeline Execution for SKU: {sku_id} ({shot_tag}) | Pose: {shot_plan.pose_source} ---")

        # Step 1: Orchestrator & JSON Prompt Payload Builder
        payload = self.orchestrator.build_payload(
            product_image_paths=product_image_paths,
            moodboard_image_paths=moodboard_image_paths,
            shot_plan=shot_plan,
            sku_id=sku_id,
            controls=controls
        )
        json_prompt_str = self.orchestrator.serialize_prompt(payload)

        prompt_log_path = output_dir / f"{sku_id}_{shot_tag}_prompt.json"
        prompt_log_path.write_text(json_prompt_str, encoding="utf-8")

        attempt = 0
        passed = False
        final_output_path = output_dir / f"{sku_id}_{shot_tag}_generated.png"
        qc_report = None

        # Filter specific pose image from moodboards
        selected_moodboard = [m for m in moodboard_image_paths if m.name == shot_plan.pose_source]
        if not selected_moodboard:
            selected_moodboard = moodboard_image_paths[:2]

        while attempt <= self.max_retries and not passed:
            attempt += 1
            logger.info(f"Attempt {attempt}/{self.max_retries + 1} for SKU {sku_id} ({shot_tag})")

            # Step 2: Generation Engine (Vertex AI Gemini 3 Pro Image)
            self.generator.generate(
                json_prompt_str=json_prompt_str,
                product_image_paths=product_image_paths,
                moodboard_image_paths=selected_moodboard,
                output_path=final_output_path
            )

            # Step 3: Visual QC Inspector (Gemini 3.6 Flash Layer 1 & 2)
            qc_report = self.inspector.inspect(
                product_image_paths=product_image_paths,
                generated_image_path=final_output_path
            )

            passed = qc_report.pass_quality_gate
            logger.info(
                f"Attempt {attempt} Composite: {qc_report.composite_quality_score:.2f}, "
                f"BinarySanity: {qc_report.is_same_garment_or_valid_piece}, Passed: {passed}"
            )

        # Step 4: Quality Gate Routing
        report_path = output_dir / f"{sku_id}_{shot_tag}_qc_report.json"
        report_path.write_text(qc_report.model_dump_json(indent=2), encoding="utf-8")

        if passed:
            dest_img = approved_dir / f"{sku_id}_{shot_tag}_final.png"
            dest_img.write_bytes(final_output_path.read_bytes())
            status = "AUTO_APPROVED"
            logger.info(f"SKU {sku_id} ({shot_tag}) AUTO-APPROVED and saved to {dest_img}")
        else:
            dest_img = review_dir / f"{sku_id}_{shot_tag}_flagged.png"
            dest_img.write_bytes(final_output_path.read_bytes())
            status = "FLAGGED_FOR_HUMAN_REVIEW"
            logger.warning(f"SKU {sku_id} ({shot_tag}) FLAGGED FOR HUMAN REVIEW and saved to {dest_img}")

        return {
            "batch_id": batch_id,
            "batch_label": batch_label,
            "sku_id": sku_id,
            "shot_number": shot_plan.shot_number,
            "timestamp": timestamp_str,
            "framing": shot_plan.framing,
            "pose_source": shot_plan.pose_source,
            "status": status,
            "attempts": attempt,
            "final_image_path": str(dest_img),
            "qc_report": qc_report.model_dump(),
            "json_prompt_path": str(prompt_log_path),
            "controls": {
                "background": getattr(controls, 'background', 'auto') if controls else 'auto',
                "pose": getattr(controls, 'pose', 'auto') if controls else 'auto',
                "model": getattr(controls, 'model', 'auto') if controls else 'auto',
                "resolution": getattr(controls, 'resolution', '2048x2048') if controls else '2048x2048',
                "custom_override": getattr(controls, 'custom_override', None) if controls else None
            }
        }

    def process_sku_multi_pose(
        self,
        sku_id: str,
        product_image_paths: List[Path],
        moodboard_image_paths: List[Path],
        requested_num_shots: int = 3,
        controls: Any = None,
        batch_id: str = None,
        batch_label: str = None,
    ) -> List[Dict[str, Any]]:
        """Uses Gemini 3.6 Flash to plan N catalog shots and executes multi-pose generation."""

        # Step 1: LLM Intelligent Shot Planning
        shot_plans = self.orchestrator.plan_catalog_shots(
            product_image_paths=product_image_paths,
            moodboard_image_paths=moodboard_image_paths,
            requested_num_shots=requested_num_shots
        )

        results = []
        for plan in shot_plans:
            res = self.process_sku_shot(
                sku_id=sku_id,
                product_image_paths=product_image_paths,
                moodboard_image_paths=moodboard_image_paths,
                shot_plan=plan,
                controls=controls,
                batch_id=batch_id,
                batch_label=batch_label,
            )
            results.append(res)
        return results
