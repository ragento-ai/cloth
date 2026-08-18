"""
Ragento Visual Studio - Self-Correcting Critic-in-the-Loop Saree Pipeline (Critic-Loop v5)
Engine:
- Generator: Gemini 3.1 Flash Image (4K Native Resolution)
- Visual Critic: Gemini 3.6 Flash
- Control Flow: Max 3 Iterative Refinement Loops (Stops early when Critic approves)
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from src.vertex_client import get_genai_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Critic_Loop_Pipeline")

class VisualCriticFeedback(BaseModel):
    approved: bool = Field(description="True if the generated image matches the input garment without structural hallucinations, missing elements, or wrong borders.")
    overall_fidelity_score: float = Field(description="Score between 0.0 and 1.0 evaluating textile fidelity.")
    structural_hallucinations: list[str] = Field(description="List of patterns/borders/elements added to the generated image that DO NOT exist in the input garment.")
    missing_or_misplaced_elements: list[str] = Field(description="List of genuine garment elements that are missing, misplaced, or distorted.")
    refinement_instructions: str = Field(description="Concise, high-impact prompt instructions for the generator to fix the discrepancies in the next pass.")

def call_generator(client, contents, max_attempts=5) -> bytes:
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Generating image with gemini-3.1-flash-image (Attempt {attempt}/{max_attempts})...")
            res = client.models.generate_content(
                model="gemini-3.1-flash-image",
                contents=contents,
                config=config
            )
            if res.candidates:
                for part in res.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        return part.inline_data.data
            logger.warning(f"Attempt {attempt}: No image bytes in response.")
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                backoff = 30 * attempt
                logger.info(f"Quota 429 encountered. Sleeping {backoff}s before retry...")
                time.sleep(backoff)
            else:
                time.sleep(10)
    raise RuntimeError("Generator failed to produce image.")

def call_critic(client, input_images: list[Path], generated_img_bytes: bytes) -> VisualCriticFeedback:
    system_instruction = (
        "You are an expert AI Master Textile Inspector and Fashion QC Critic.\n\n"
        "TASK:\n"
        "Strictly compare the GENERATED CATALOG IMAGE against the ORIGINAL UNFOLDED PRODUCT PHOTOS.\n"
        "Evaluate whether the garment in the generated image is a 100% authentic representation of the real physical saree.\n\n"
        "KEY CHECKS TO PERFORM:\n"
        "1. BORDERS & TRIMS: Did the generator hallucinate top/bottom/side borders on areas of the saree that are actually borderless? Are borders present only where they physically exist in the input photos?\n"
        "2. PALLU vs BODY SEPARATION: Is the decorative pallu correctly restricted to the end-drape, or did the generator mistakenly use pallu motifs to frame the chest/waist/body?\n"
        "3. MOTIF & PATTERN ACCURACY: Are micro-motifs, stripes, geometric shapes, or embroideries warped, mutated, or substituted with generic patterns?\n"
        "4. COLOR & TEXTURE FIDELITY: Ground color, sheen, opacity, and fabric weave.\n\n"
        "If you find ANY structural hallucination (e.g. fake borders on borderless fabric) or pattern distortion, set approved=False and provide explicit, actionable correction instructions."
    )

    contents = [types.Part.from_text(text=system_instruction)]
    for idx, img_path in enumerate(input_images, 1):
        contents.append(types.Part.from_text(text=f"=== ORIGINAL PRODUCT PHOTO {idx} (GROUND TRUTH) ==="))
        contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg"))

    contents.append(types.Part.from_text(text="=== GENERATED CATALOG IMAGE TO CRITIQUE ==="))
    contents.append(types.Part.from_bytes(data=generated_img_bytes, mime_type="image/png"))
    contents.append(types.Part.from_text(text="Analyze the generated catalog image against the ground truth photos and return your structured critique JSON."))

    logger.info("Calling Gemini 3.6 Flash Visual Critic...")
    res = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisualCriticFeedback,
            temperature=0.1
        )
    )
    return VisualCriticFeedback.model_validate_json(res.text)

def run_critic_loop(saree_folder_name: str, moodboard_file: str = "1000221736.jpg", max_iterations: int = 3):
    saree_dir = ROOT_DIR / "saree_unfolded" / saree_folder_name
    if not saree_dir.exists():
        raise ValueError(f"Saree directory not found: {saree_dir}")

    input_images = sorted([
        f for f in saree_dir.iterdir()
        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ])
    if not input_images:
        raise ValueError(f"No valid images found in {saree_dir}")

    moodboard_path = ROOT_DIR / "moodboard_2" / moodboard_file
    if not moodboard_path.exists():
        raise ValueError(f"Moodboard file not found: {moodboard_path}")

    output_dir = ROOT_DIR / "output_sari" / saree_folder_name / "critic_loop"
    output_dir.mkdir(parents=True, exist_ok=True)

    client = get_genai_client()

    logger.info(f"\n==========================================================================")
    logger.info(f" STARTING CRITIC LOOP (MAX {max_iterations} ITERATIONS) FOR SAREE {saree_folder_name}")
    logger.info(f"==========================================================================")

    previous_image_bytes = None
    refinement_prompt = None

    for iteration in range(1, max_iterations + 1):
        logger.info(f"\n>>> ITERATION {iteration}/{max_iterations} <<<")
        iter_img_path = output_dir / f"iteration_{iteration}.png"
        iter_critique_path = output_dir / f"critique_{iteration}.json"

        # Build Generator Contents
        system_instruction = (
            "You are an expert AI Luxury Fashion Photographer creating a master commercial catalog image for Indian Ethnic Wear.\n\n"
            "TASK:\n"
            "1. GARMENT FIDELITY (Reference Images 1 & 2):\n"
            "   - Drape the exact authentic saree shown in Reference Images 1 & 2 onto the fashion model in classic Nivi saree style.\n"
            "   - Replicate the exact colors, weave textures, motifs, borders, and pallu decorations exactly as seen in the unfolded photos.\n"
            "   - DO NOT hallucinate extra borders or trims on areas of the saree that are borderless in the photos.\n"
            "2. MODEL POSE & ENVIRONMENT (Moodboard Reference Image 3):\n"
            "   - Replicate the model pose, lighting, angle, and studio environment from Reference Image 3. STRICTLY IGNORE any clothing worn in Image 3.\n"
            "3. STYLING:\n"
            "   - Render an elegant, well-fitted blouse complementary in color to the saree.\n"
            "   - Render hyper-realistic skin texture, natural cloth draping physics, and 4K commercial fidelity."
        )

        contents = [types.Part.from_text(text=system_instruction)]
        for idx, img_path in enumerate(input_images, 1):
            contents.append(types.Part.from_text(text=f"=== REFERENCE IMAGE {idx}: GROUND TRUTH PRODUCT PHOTO {idx} ==="))
            contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg"))

        contents.append(types.Part.from_text(text=f"=== REFERENCE IMAGE {len(input_images)+1}: MOODBOARD (POSE & STUDIO ONLY) ==="))
        contents.append(types.Part.from_bytes(data=moodboard_path.read_bytes(), mime_type="image/jpeg"))

        if iteration > 1 and previous_image_bytes and refinement_prompt:
            contents.append(types.Part.from_text(text=f"=== PREVIOUS DRAFT (NEEDS CORRECTION) ==="))
            contents.append(types.Part.from_bytes(data=previous_image_bytes, mime_type="image/png"))
            contents.append(types.Part.from_text(text=f"=== CRITIC CORRECTION DIRECTIVES (MUST FIX) ===\n{refinement_prompt}"))

        # Generate Image
        img_bytes = call_generator(client, contents)
        iter_img_path.write_bytes(img_bytes)
        previous_image_bytes = img_bytes
        logger.info(f"✓ Saved Iteration {iteration} Image to {iter_img_path.name} ({len(img_bytes)} bytes)")

        # Critique Image
        logger.info("Evaluating iteration with Gemini 3.6 Flash Visual Critic...")
        critique = call_critic(client, input_images, img_bytes)
        iter_critique_path.write_text(critique.model_dump_json(indent=2), encoding="utf-8")

        logger.info(f"Critic Result for Iteration {iteration}: Approved={critique.approved}, Score={critique.overall_fidelity_score:.2f}")
        logger.info(f"Structural Hallucinations: {critique.structural_hallucinations}")
        logger.info(f"Refinement Instructions: {critique.refinement_instructions}")

        if critique.approved:
            logger.info(f"\n🎉 CRITIC APPROVED IN ITERATION {iteration}! Finalizing...")
            final_path = output_dir / f"final_approved_saree_{saree_folder_name}.png"
            final_path.write_bytes(img_bytes)
            return final_path, critique

        # Setup for next iteration
        refinement_prompt = critique.refinement_instructions
        logger.info("Pausing 15s before next refinement pass...")
        time.sleep(15)

    final_path = output_dir / f"final_approved_saree_{saree_folder_name}.png"
    final_path.write_bytes(previous_image_bytes)
    logger.info(f"Reached max iterations ({max_iterations}). Final image saved to {final_path.name}")
    return final_path, critique

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Self-Correcting Critic-in-the-Loop Saree Pipeline")
    parser.add_argument("--saree", type=str, default="3", help="Folder name (e.g. 3, 1, 2)")
    parser.add_argument("--moodboard", type=str, default="1000221736.jpg", help="Moodboard filename")
    parser.add_argument("--max_iter", type=int, default=3, help="Max critique loops")
    args = parser.parse_args()

    run_critic_loop(args.saree, args.moodboard, args.max_iter)
