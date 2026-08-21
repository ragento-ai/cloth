"""
Pass 1 Orchestrator: Uses Gemini 3.7 Flash to analyze product shots, group moodboard references,
plan multi-shot catalog visual payloads, and track token usage.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from PIL import Image

from config import settings
from models import JSONPromptPayload, GarmentIdentitySpec, CompositionSpec, AestheticSpec, ShotPlanList, ShotPlan
from src.vertex_client import get_genai_client
from src.cost_tracker import calculate_step_cost

from prompts import format_shot_planning_prompt, GARMENT_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class PromptOrchestrator:
    """Orchestrates payload indexing, moodboard shot planning, and structured JSON prompt generation using Gemini 3.7 Flash."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.ORCHESTRATOR_MODEL
        self.client = get_genai_client()

    def select_fabric_anchor(self, product_image_paths: List[Path]) -> Path:
        """Selects the best fabric close-up image from product shots."""
        for p in product_image_paths:
            name_lower = p.stem.lower()
            if any(k in name_lower for k in ["detail", "fabric", "close", "weave", "pattern", "j", "k"]):
                return p
        return product_image_paths[-1] if product_image_paths else product_image_paths[0]

    def plan_catalog_shots(
        self,
        product_image_paths: List[Path],
        moodboard_image_paths: List[Path],
        requested_num_shots: int = 3
    ) -> List[ShotPlan]:
        """Uses Gemini 3.7 Flash to analyze the moodboard library and intelligently plan N distinct catalog shots."""
        logger.info(f"Using '{self.model_name}' to analyze moodboard and plan {requested_num_shots} distinct catalog shots...")

        moodboard_filenames = [m.name for m in moodboard_image_paths]

        if not moodboard_image_paths:
            return [
                ShotPlan(
                    shot_number=i + 1,
                    pose_source="moodboard_pose.jpg",
                    lighting_source="moodboard_lighting.jpg",
                    framing="full_body_catalog" if i == 0 else ("medium_shot" if i == 1 else "close_up_fabric_drape"),
                    rationale="Fallback default shot plan"
                )
                for i in range(requested_num_shots)
            ]

        prompt = format_shot_planning_prompt(moodboard_filenames, requested_num_shots)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
                config=dict(
                    response_mime_type="application/json",
                    response_schema=ShotPlanList
                )
            )
            plan_data = json.loads(response.text)
            plan_list = ShotPlanList(**plan_data)
            # Ensure pose_source and lighting_source match the 1-to-1 assigned moodboards if available
            for idx, shot in enumerate(plan_list.shots):
                if idx < len(moodboard_filenames):
                    assigned_file = moodboard_filenames[idx]
                    shot.pose_source = assigned_file
                    shot.lighting_source = assigned_file
            logger.info(f"Gemini 3.7 Flash planned {len(plan_list.shots)} catalog shots successfully (1-to-1 moodboard mapping).")
            return plan_list.shots
        except Exception as e:
            logger.warning(f"Shot planning fallback triggered ({e}). Generating fallback plan...")
            fallback_shots = []
            for i in range(requested_num_shots):
                assigned_file = moodboard_filenames[i % len(moodboard_filenames)]
                framing = "full_body_catalog" if i == 0 else ("3_4_lifestyle" if i == 1 else "close_up_fabric_drape")
                fallback_shots.append(
                    ShotPlan(
                        shot_number=i + 1,
                        pose_source=assigned_file,
                        lighting_source=assigned_file,
                        framing=framing,
                        rationale=f"Single moodboard assignment ({assigned_file}) for shot {i + 1}"
                    )
                )
            return fallback_shots

    def build_payload(
        self,
        product_image_paths: List[Path],
        moodboard_image_paths: List[Path],
        shot_plan: ShotPlan,
        sku_id: str = "SKU_001",
        controls: Optional[Any] = None
    ) -> JSONPromptPayload:
        """Constructs structured JSONPromptPayload object using Gemini 3.7 Flash visual analysis and selective transfer controls."""

        anchor_img = self.select_fabric_anchor(product_image_paths)
        product_filenames = [p.name for p in product_image_paths]

        analysis_details = ""
        try:
            pil_images = [Image.open(p) for p in product_image_paths if p.exists()]
            analysis_prompt = GARMENT_ANALYSIS_PROMPT
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[analysis_prompt] + pil_images[:2]
            )
            analysis_details = response.text.replace("\n", " ").strip()
            logger.info(f"Gemini 3.7 Flash Visual Analysis for {sku_id}: {analysis_details[:150]}...")
        except Exception as e:
            logger.warning(f"Visual analysis query skipped: {e}")

        fidelity_rules = [
            "100% fabric pattern, weave, print scale, and embroidery preservation",
            "Maintain exact garment identity or individual piece styling (Saree/Kurta/Piece)",
            "Exact base color palette retention under studio lighting",
            "Maintain original fabric drape physics and texture placement"
        ]
        if analysis_details:
            fidelity_rules.append(f"Visual Specs: {analysis_details[:200]}")

        # Process selective transfer controls
        bg_source = "auto"
        pose_ctrl = "auto"
        model_ctrl = "auto"
        custom_override = None
        if controls:
            bg_source = getattr(controls, 'background', 'auto')
            pose_ctrl = getattr(controls, 'pose', 'auto')
            model_ctrl = getattr(controls, 'model', 'auto')
            custom_override = getattr(controls, 'custom_override', None)

        if custom_override and custom_override.strip():
            override_str = custom_override.strip()
            fidelity_rules.insert(0, f"HIGH-PRIORITY CREATIVE OVERRIDE (MUST FULFILL): {override_str}")

        model_spec = "natural_fashion_model_rendering | match_moodboard_subject_vertical_scale_and_canvas_occupancy"
        if model_ctrl == "input":
            model_spec = "match_human_model_appearance_from_input_photo"
        elif model_ctrl == "moodboard":
            model_spec = "adopt_model_facial_features_hair_and_scale_from_moodboard_reference"

        pose_spec = shot_plan.pose_source
        if pose_ctrl == "input":
            pose_spec = "input_product_photo_pose"
        elif pose_ctrl == "moodboard":
            pose_spec = shot_plan.pose_source

        framing_spec = f"{shot_plan.framing} | preserve_moodboard_subject_proportions_and_distance (avoid oversized subject, maintain natural headroom & floor clearance)"

        bg_spec = "replicate_authentic_fashion_studio_environment_from_moodboard"
        if bg_source == "input":
            bg_spec = "replicate_background_environment_from_input_photo"
        elif bg_source == "moodboard":
            bg_spec = f"replicate_backdrop_architectural_set_and_lighting_from_{shot_plan.lighting_source}"

        if custom_override and custom_override.strip():
            bg_spec = f"{bg_spec} | OVERRIDE INSTRUCTION: {custom_override.strip()}"

        payload = JSONPromptPayload(
            task=f"D2C_apparel_model_transfer_{sku_id}_shot_{shot_plan.shot_number}",
            garment_identity=GarmentIdentitySpec(
                source_images=product_filenames,
                fabric_texture_anchor=anchor_img.name,
                fidelity_rules=fidelity_rules
            ),
            composition_spec=CompositionSpec(
                pose_source=pose_spec,
                lighting_source=shot_plan.lighting_source,
                framing=framing_spec,
                camera_angle=shot_plan.camera_angle
            ),
            aesthetic=AestheticSpec(
                style="photorealistic_commercial_fashion",
                model_rendering=model_spec,
                background=bg_spec
            )
        )

        return payload

    def serialize_prompt(self, payload: JSONPromptPayload) -> str:
        """Serializes JSONPromptPayload to formatted JSON string."""
        return payload.model_dump_json(indent=2)
