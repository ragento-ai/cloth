"""
Pydantic data models for structured JSON prompts, moodboard shot planner, and Visual QC reports.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TransferControls(BaseModel):
    """Controls for selective feature transfer between Input, Moodboard, and Model Decides (Auto)."""
    background: str = Field("auto", description="Source for background/environment: 'auto' (Model Decides), 'input', 'moodboard'")
    pose: str = Field("auto", description="Source for pose & gesture: 'auto' (Model Decides), 'input', 'moodboard'")
    model: str = Field("auto", description="Source for model identity: 'auto' (Model Decides), 'input', 'moodboard'")
    resolution: str = Field("4096x4096", description="Target output image resolution: '1024x1024', '2048x2048', '4096x4096'")
    custom_override: Optional[str] = Field(None, description="High-priority user directive that overrides default toggles")


class ShotPlan(BaseModel):
    """Configuration plan for a single catalog shot planned via Gemini 3.7 Flash."""
    shot_number: int = Field(..., description="1-indexed shot sequence number")
    pose_source: str = Field(..., description="Filename of moodboard reference selected for model pose")
    lighting_source: str = Field(..., description="Filename of moodboard reference selected for lighting/atmosphere")
    framing: str = Field(..., description="Framing type e.g. full_body_catalog, 3_4_lifestyle, close_up_drape_detail")
    camera_angle: str = Field("eye_level_studio", description="Camera perspective")
    rationale: str = Field(..., description="Reasoning for selecting this moodboard pose pairing")


class ShotPlanList(BaseModel):
    """Container for multi-shot catalog plan."""
    shots: List[ShotPlan] = Field(..., description="List of shot plans selected by Gemini 3.6 Flash")


class GarmentIdentitySpec(BaseModel):
    """Configuration rules for preserving garment pattern, color, piece composition, and texture."""
    source_images: List[str] = Field(..., description="Filenames or labels of product shots")
    fabric_texture_anchor: str = Field(..., description="High-res close-up shot used as fabric anchor")
    fidelity_rules: List[str] = Field(
        default_factory=lambda: [
            "100% fabric pattern, weave, print scale, and embroidery preservation",
            "Preserve garment piece composition (full set or individual piece draped)",
            "Exact base color palette retention under studio lighting"
        ],
        description="Strict rules for pattern and color preservation"
    )


class CompositionSpec(BaseModel):
    """Target composition and aesthetic extracted from moodboard references."""
    pose_source: str = Field(..., description="Moodboard image controlling model pose")
    lighting_source: str = Field(..., description="Moodboard image controlling lighting/atmosphere")
    framing: str = Field("full_body_catalog_shot", description="Framing type e.g. full body, medium shot, close up")
    camera_angle: str = Field("eye_level_studio", description="Camera angle and perspective")


class AestheticSpec(BaseModel):
    """Overall aesthetic guidelines for the rendered output."""
    style: str = Field("photorealistic_commercial_fashion", description="Overall artistic style")
    model_rendering: str = Field("natural_skin_texture_and_anatomy", description="Anatomy and skin texture rule")
    background: str = Field("authentic_luxury_fashion_studio_environment", description="Background aesthetic")


class JSONPromptPayload(BaseModel):
    """Structured JSON prompt passed alongside images to Gemini Image Models."""
    task: str = Field("D2C_apparel_model_transfer", description="Pipeline task identifier")
    garment_identity: GarmentIdentitySpec
    composition_spec: CompositionSpec
    aesthetic: AestheticSpec


class VisualQCReport(BaseModel):
    """Structured JSON report returned by Gemini 3.6 Flash Visual QC Inspector with Layer 1 Binary & Layer 2 Granular Guardrails."""
    is_same_garment_or_valid_piece: bool = Field(..., description="Layer 1 Binary Sanity Check: True if output is the exact garment SKU or a valid individual piece/styling of the SKU")
    garment_type_match: float = Field(..., ge=0.0, le=1.0, description="Verification that output garment/piece matches product category or valid ensemble styling (0.0 to 1.0)")
    base_color_fidelity: float = Field(..., ge=0.0, le=1.0, description="Fidelity of primary & secondary color palette vs input product shots (0.0 to 1.0)")
    pattern_match_confidence: float = Field(..., ge=0.0, le=1.0, description="Pattern and weave preservation score (0.0 to 1.0)")
    anatomical_correctness: float = Field(..., ge=0.0, le=1.0, description="Anatomical correctness score (0.0 to 1.0)")
    garment_drape_realism: float = Field(..., ge=0.0, le=1.0, description="Realism of cloth draping and folds (0.0 to 1.0)")
    transformation_verification: float = Field(..., ge=0.0, le=1.0, description="Verification that model/pose/background transfer occurred (0.0 if raw copy)")
    composite_quality_score: float = Field(..., ge=0.0, le=1.0, description="Weighted composite score")
    pass_quality_gate: bool = Field(..., description="True if passes automated QC thresholds")
    detected_defects: List[str] = Field(default_factory=list, description="List of detected defects if any")
    human_review_reason: Optional[str] = Field(None, description="Reason for flagging for human review if applicable")


class VisualCriticFeedback(BaseModel):
    """Structured feedback from Gemini 3.6 Flash Visual Critic on structural and pattern fidelity."""
    approved: bool = Field(..., description="True if the generated image matches the input garment without structural hallucinations, missing elements, or wrong borders.")
    overall_fidelity_score: float = Field(..., description="Score between 0.0 and 1.0 evaluating textile fidelity.")
    structural_hallucinations: List[str] = Field(default_factory=list, description="List of patterns/borders/elements added to the generated image that DO NOT exist in the input garment.")
    missing_or_misplaced_elements: List[str] = Field(default_factory=list, description="List of genuine garment elements that are missing, misplaced, or distorted.")
    refinement_instructions: str = Field(..., description="Concise, high-impact prompt instructions for the generator to fix discrepancies.")


class RefineRequest(BaseModel):
    """Payload to trigger 2-pass visual critic refinement on an existing output."""
    sku_id: str = Field(..., description="SKU Identifier e.g. GARMENT_1")
    image_path: str = Field(..., description="Full path or relative path of image to refine")
    timestamp: Optional[str] = Field(None, description="Shot timestamp identifier")
    shot_number: Optional[int] = Field(None, description="Shot number")
    user_feedback: Optional[str] = Field("", description="Optional custom user instructions / refinement feedback")
    max_iterations: int = Field(2, description="Maximum critic refinement loops")

