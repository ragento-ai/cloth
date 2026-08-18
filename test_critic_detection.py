"""
Test script to verify if the Visual QC Critic reliably catches the stripe orientation flaw on iteration_3_corrected_stripes.png.
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
logger = logging.getLogger("Verify_Critic_Detection")

class TextileQCCritique(BaseModel):
    approved: bool = Field(description="True if image has no textile, border, or orientation defects.")
    textile_fidelity_score: float = Field(description="Score between 0.0 and 1.0.")
    stripe_and_motif_orientation_check: str = Field(description="Analysis of stripe/weave/motif angles on the body, pleats, and hanging pallu relative to ground truth.")
    defects_found: list[str] = Field(description="List of specific flaws found.")
    recommendation: str = Field(description="Actionable fix recommendation.")

def verify_critic():
    client = get_genai_client()
    input_img1 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134554.jpg.jpeg"
    input_img2 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134602.jpg.jpeg"
    final_img = ROOT_DIR / "output_sari/3/critic_loop/iteration_3_corrected_stripes.png"

    system_instruction = (
        "You are an expert AI Master Textile Inspector conducting a rigorous Quality Control audit.\n\n"
        "TASK:\n"
        "Audit the GENERATED CATALOG IMAGE against the ORIGINAL GROUND TRUTH PRODUCT PHOTOS.\n\n"
        "MANDATORY GEOMETRIC AUDIT CHECKLIST:\n"
        "1. STRIPE & MOTIF ORIENTATION RELATIVE TO PALU:\n"
        "   - Inspect the black-and-white stripes on the hanging pallu fall.\n"
        "   - In the real product, the stripes and the red Ajrakh bands are PARALLEL (both run horizontally across fabric width).\n"
        "   - Check if the generated image incorrectly rendered stripes as VERTICAL lines running into the horizontal red band.\n"
        "2. BORDERS & TRIMS:\n"
        "   - Verify that no hallucinated borders exist on the body/pleats.\n"
        "3. PALLU ELEMENTS:\n"
        "   - Check order of Ajrakh arches, white circular discs, and pom-pom fringe.\n\n"
        "If the stripe direction on the pallu is perpendicular instead of parallel to the red bands, FAIL the audit (approved=False)."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 1 ==="),
        types.Part.from_bytes(data=input_img1.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 2 ==="),
        types.Part.from_bytes(data=input_img2.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GENERATED CATALOG IMAGE TO AUDIT ==="),
        types.Part.from_bytes(data=final_img.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="Conduct the rigorous audit and return the structured JSON report.")
    ]

    logger.info("Running Gemini 3.6 Flash Audit on Iteration 3 Image...")
    res = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TextileQCCritique,
            temperature=0.1
        )
    )

    result = json.loads(res.text)
    print("\n--- QC AUDIT REPORT ---")
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    verify_critic()
