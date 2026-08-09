"""
Pass 1 Orchestrator: Uses Gemini 3.6 Flash to analyze product shots, group moodboard references, and plan multi-shot catalog visual payloads.
"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path
from PIL import Image

from config import settings
from models import JSONPromptPayload, GarmentIdentitySpec, CompositionSpec, AestheticSpec, ShotPlanList, ShotPlan
from src.vertex_client import get_genai_client

logger = logging.getLogger(__name__)


class PromptOrchestrator:
    """Orchestrates payload indexing, moodboard shot planning, and structured JSON prompt generation using Gemini 3.6 Flash."""

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
        """Uses Gemini 3.6 Flash to analyze the moodboard library and intelligently plan N distinct catalog shots."""
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

        prompt = (
            f"You are an AI Fashion Art Director.\n"
            f"Available Moodboard Reference Images: {moodboard_filenames}\n\n"
            f"TASK:\n"
            f"Plan exactly {requested_num_shots} distinct catalog shots for a D2C apparel SKU.\n"
            f"For each shot (1 to {requested_num_shots}):\n"
            f"1. Select the best moodboard image for model pose (pose_source).\n"
            f"2. Select a moodboard image for lighting/mood (lighting_source).\n"
            f"3. Specify framing (e.g. full_body_catalog, 3_4_lifestyle, close_up_drape_detail).\n"
            f"4. Provide a brief rationale for why this moodboard pairing creates visual variety.\n\n"
            f"Return JSON matching the ShotPlanList schema."
        )

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
            logger.info(f"Gemini 3.6 Flash planned {len(plan_list.shots)} catalog shots successfully.")
            return plan_list.shots
        except Exception as e:
            logger.warning(f"Shot planning fallback triggered ({e}). Generating fallback plan...")
            fallback_shots = []
            for i in range(requested_num_shots):
                pose_file = moodboard_filenames[i % len(moodboard_filenames)]
                light_file = moodboard_filenames[(i + 1) % len(moodboard_filenames)]
                framing = "full_body_catalog" if i == 0 else ("3_4_lifestyle" if i == 1 else "close_up_fabric_drape")
                fallback_shots.append(
                    ShotPlan(
                        shot_number=i + 1,
                        pose_source=pose_file,
                        lighting_source=light_file,
                        framing=framing,
                        rationale=f"Fallback rotation plan for shot {i + 1}"
                    )
                )
            return fallback_shots

    def build_payload(
        self,
        product_image_paths: List[Path],
        moodboard_image_paths: List[Path],
        shot_plan: ShotPlan,
        sku_id: str = "SKU_001"
    ) -> JSONPromptPayload:
        """Constructs structured JSONPromptPayload object using Gemini 3.6 Flash visual analysis."""

        anchor_img = self.select_fabric_anchor(product_image_paths)
        product_filenames = [p.name for p in product_image_paths]

        analysis_details = ""
        try:
            pil_images = [Image.open(p) for p in product_image_paths if p.exists()]
            analysis_prompt = (
                "Analyze these product shots of a D2C fashion garment.\n"
                "Extract concisely:\n"
                "1. Exact Garment Type & Ensemble Pieces (e.g. Saree with unstitched blouse, 3-piece Kurta set, or single dupata/kurta piece)\n"
                "2. Exact Base Fabric Color Palette (e.g. Deep Emerald Green, Indigo Blue, Lilac)\n"
                "3. Pattern & Weave Details (e.g. Bandhani tie-dye, Zari border motif, floral embroidery)\n"
                "Provide a 2-sentence visual specification."
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[analysis_prompt] + pil_images[:2]
            )
            analysis_details = response.text.replace("\n", " ").strip()
            logger.info(f"Gemini 3.6 Flash Visual Analysis for {sku_id}: {analysis_details[:150]}...")
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

        payload = JSONPromptPayload(
            task=f"D2C_apparel_model_transfer_{sku_id}_shot_{shot_plan.shot_number}",
            garment_identity=GarmentIdentitySpec(
                source_images=product_filenames,
                fabric_texture_anchor=anchor_img.name,
                fidelity_rules=fidelity_rules
            ),
            composition_spec=CompositionSpec(
                pose_source=shot_plan.pose_source,
                lighting_source=shot_plan.lighting_source,
                framing=shot_plan.framing,
                camera_angle=shot_plan.camera_angle
            ),
            aesthetic=AestheticSpec(
                style="photorealistic_commercial_fashion",
                model_rendering="natural_skin_texture_and_anatomy",
                background="soft_minimalist_studio_environment"
            )
        )

        return payload

    def serialize_prompt(self, payload: JSONPromptPayload) -> str:
        """Serializes JSONPromptPayload to formatted JSON string."""
        return payload.model_dump_json(indent=2)
