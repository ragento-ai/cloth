"""
Test script to verify Gemini 3.6 Flash Visual Critic on Saree 3 v4 output.
"""

import sys
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from src.vertex_client import get_genai_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Test_Critic")

class VisualCriticFeedback(BaseModel):
    approved: bool = Field(description="True if the generated image matches the input garment without structural hallucinations, missing elements, or wrong borders.")
    overall_fidelity_score: float = Field(description="Score between 0.0 and 1.0 evaluating textile fidelity.")
    structural_hallucinations: list[str] = Field(description="List of patterns/borders/elements added to the generated image that DO NOT exist in the input garment.")
    missing_or_misplaced_elements: list[str] = Field(description="List of genuine garment elements that are missing, misplaced, or distorted.")
    refinement_instructions: str = Field(description="Concise, high-impact prompt instructions for the generator to fix the discrepancies in the next pass.")

def test_critic_on_saree3():
    client = get_genai_client()
    input_img1 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134554.jpg.jpeg"
    input_img2 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134602.jpg.jpeg"
    generated_img = ROOT_DIR / "output_sari/3/v4/final_on_model_v4_3.png"

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

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== ORIGINAL PRODUCT PHOTO 1 (GROUND TRUTH) ==="),
        types.Part.from_bytes(data=input_img1.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== ORIGINAL PRODUCT PHOTO 2 (GROUND TRUTH) ==="),
        types.Part.from_bytes(data=input_img2.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GENERATED CATALOG IMAGE TO CRITIQUE ==="),
        types.Part.from_bytes(data=generated_img.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="Analyze the generated catalog image against the ground truth photos and return your structured critique JSON.")
    ]

    logger.info("Calling Gemini 3.6 Flash for Visual Critique...")
    res = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisualCriticFeedback,
            temperature=0.1
        )
    )

    result_json = json.loads(res.text)
    print("\n--- CRITIC REPORT ---\n")
    print(json.dumps(result_json, indent=2))
    return result_json

if __name__ == "__main__":
    test_critic_on_saree3()
