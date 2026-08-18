"""
Targeted Critic & Refinement Pass for Saree 3 (Iteration 3)
Focus: Physical Stripe Orientation & Weave Alignment relative to Pallu Bands
"""

import sys
import json
import time
import logging
from pathlib import Path
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from src.vertex_client import get_genai_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Saree3_Targeted_Refinement")

class TargetedCriticFeedback(BaseModel):
    approved: bool = Field(description="True only if stripe orientation and all garment features match physical ground truth.")
    stripe_orientation_analysis: str = Field(description="Detailed physical analysis of stripe direction in input photo vs generated draft.")
    detected_discrepancies: list[str] = Field(description="List of geometry/orientation errors found.")
    refinement_instructions: str = Field(description="Strict, high-impact generation prompt instructing the model how to fix stripe orientation on the drape and pallu.")

def run_targeted_critic_and_regenerate():
    client = get_genai_client()
    output_dir = ROOT_DIR / "output_sari/3/critic_loop"
    output_dir.mkdir(parents=True, exist_ok=True)

    input_img1 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134554.jpg.jpeg"
    input_img2 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134602.jpg.jpeg"
    draft_img = output_dir / "iteration_2.png"
    moodboard_img = ROOT_DIR / "moodboard_2/1000221736.jpg"

    # Step 1: Critic Analysis with Stripe Orientation Focus
    system_instruction_critic = (
        "You are an expert AI Master Textile Structural Engineer and Fashion QC Critic.\n\n"
        "TASK:\n"
        "Critique the GENERATED IMAGE (Draft 2) against the ORIGINAL GROUND TRUTH PHOTOS with specific focus on:\n"
        "1. STRIPE ORIENTATION RELATIVE TO PALLU: In the original saree, the black-and-white stripes and the red Ajrakh pallu bands are strictly PARALLEL to each other (both run horizontally across the width of the saree, perpendicular to the 5.5m length).\n"
        "2. PALLU DRAPE GEOMETRY: Check the hanging pallu in the generated image. Are the stripes running parallel to the red bands (horizontal across the hanging width), or did the generator render them perpendicular (running vertically down the length of the fall)?\n"
        "3. DRAPE CONSISTENCY: Ensure the waist pleats and torso wrap maintain physically correct stripe alignment.\n\n"
        "Analyze the discrepancies, explain the physical reasoning, and provide exact generative refinement directives."
    )

    critic_contents = [
        types.Part.from_text(text=system_instruction_critic),
        types.Part.from_text(text="=== ORIGINAL GROUND TRUTH PHOTO 1 ==="),
        types.Part.from_bytes(data=input_img1.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== ORIGINAL GROUND TRUTH PHOTO 2 ==="),
        types.Part.from_bytes(data=input_img2.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== CURRENT DRAFT IMAGE (TO CRITIQUE) ==="),
        types.Part.from_bytes(data=draft_img.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="Perform the geometric analysis and return the structured critique JSON.")
    ]

    logger.info("Executing Gemini 3.6 Flash Targeted Structural Critique...")
    critic_res = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=critic_contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TargetedCriticFeedback,
            temperature=0.1
        )
    )

    critique_data = json.loads(critic_res.text)
    critique_out_path = output_dir / "critique_3_stripe_orientation.json"
    critique_out_path.write_text(json.dumps(critique_data, indent=2), encoding="utf-8")
    
    logger.info(f"Targeted Critique saved to {critique_out_path}")
    print("\n--- TARGETED CRITIC REPORT ---")
    print(json.dumps(critique_data, indent=2))

    # Step 2: Regenerate (Iteration 3) using Gemini 3.1 Flash Image in 4K
    system_instruction_gen = (
        "You are an expert AI Luxury Fashion Photographer creating a master commercial catalog image for Indian Ethnic Wear.\n\n"
        "TASK - PERFECT PHYSICAL DRAPING & STRIPE ORIENTATION:\n"
        "1. GARMENT STRIPE & WEAVE GEOMETRY (Ground Truth Images 1 & 2):\n"
        "   - In the authentic product, the black-and-white stripes are strictly PARALLEL to the red Ajrakh pallu bands (both run horizontally across the width of the saree).\n"
        "   - ON THE HANGING PALLU: The black-and-white stripes MUST RUN HORIZONTALLY across the width of the hanging pallu, perfectly parallel to the red Ajrakh bands and white polka dot stripe below them. DO NOT render vertical stripes on the hanging pallu.\n"
        "   - ON THE BODY & PLEATS: The saree body is 100% borderless edge-to-edge stripes.\n"
        "2. MODEL & ENVIRONMENT (Image 3 - Moodboard):\n"
        "   - Replicate the exact pose, lighting, model posture, and warm terracotta architectural environment from Moodboard Image 3. Ignore clothing in Image 3.\n"
        "3. Render commercial 4K ultra-high definition clarity with photorealistic skin and natural fabric physics."
    )

    gen_contents = [
        types.Part.from_text(text=system_instruction_gen),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 1 ==="),
        types.Part.from_bytes(data=input_img1.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 2 ==="),
        types.Part.from_bytes(data=input_img2.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== MOODBOARD REFERENCE PHOTO (POSE & STUDIO) ==="),
        types.Part.from_bytes(data=moodboard_img.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== PREVIOUS DRAFT (SHOWING INCORRECT VERTICAL STRIPES ON PALLU) ==="),
        types.Part.from_bytes(data=draft_img.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text=f"=== CRITIC REFINEMENT DIRECTIVE (MUST FIX) ===\n{critique_data['refinement_instructions']}")
    ]

    logger.info("Generating Iteration 3 with gemini-3.1-flash-image in 4K...")
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )

    res_gen = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=gen_contents,
        config=config
    )

    if res_gen.candidates:
        for part in res_gen.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                iter3_path = output_dir / "iteration_3_corrected_stripes.png"
                iter3_path.write_bytes(part.inline_data.data)
                logger.info(f"✓ Iteration 3 generated and saved to {iter3_path} ({len(part.inline_data.data)} bytes)")
                
                # Update final approved asset
                final_path = output_dir / "final_approved_saree_3.png"
                final_path.write_bytes(part.inline_data.data)
                logger.info(f"✓ Updated final approved asset at {final_path}")
                return iter3_path, critique_data

    raise RuntimeError("Iteration 3 generation failed.")

if __name__ == "__main__":
    run_targeted_critic_and_regenerate()
