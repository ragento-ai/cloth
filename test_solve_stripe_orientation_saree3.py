"""
Test solving stripe orientation on Saree 3 using Gemini 3 Pro Image (Advanced Spatial Reasoning) + Critic Audit.
"""

import sys
import json
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from src.vertex_client import get_genai_client
from test_critic_detection import TextileQCCritique

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Solve_Stripe_Orientation")

def run_experiment():
    client = get_genai_client()
    output_dir = ROOT_DIR / "output_sari/3/stripe_orientation_tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    input_img1 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134554.jpg.jpeg"
    input_img2 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134602.jpg.jpeg"
    moodboard_img = ROOT_DIR / "moodboard_2/1000221736.jpg"
    flawed_draft_img = ROOT_DIR / "output_sari/3/critic_loop/iteration_3_corrected_stripes.png"

    # Test with gemini-3-pro-image
    system_instruction = (
        "You are an expert AI Luxury Fashion Photographer and 3D Garment Spatial Engineer.\n\n"
        "TASK - CORRECT SPATIAL STRIPE GEOMETRY & DRAPE:\n"
        "1. GROUND TRUTH WEAVE ORIENTATION (Images 1 & 2):\n"
        "   - The saree fabric has horizontal stripes running across the 1.1m fabric width (parallel to the red Ajrakh pallu bands).\n"
        "   - CRITICAL SPATIAL RULE FOR HANGING PALLU:\n"
        "     When the saree hangs vertically from the left shoulder down the front/side, the black-and-white stripes MUST RUN HORIZONTALLY across the width of the hanging fabric, staying strictly parallel to the red Ajrakh bands and white polka dot strip at the bottom.\n"
        "     STRICTLY FORBIDDEN: Do NOT draw vertical stripes on the hanging pallu fall.\n"
        "2. BODY & PLEATS:\n"
        "   - Completely borderless edge-to-edge stripes across torso and skirt pleats.\n"
        "3. MODEL & STUDIO (Image 3 - Moodboard):\n"
        "   - Replicate the exact model pose, lighting, and warm architectural studio environment from Image 3 (ignore clothing in Image 3).\n"
        "4. Render commercial 4K ultra-high definition clarity with photorealistic skin and natural cloth physics."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 1 ==="),
        types.Part.from_bytes(data=input_img1.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 2 ==="),
        types.Part.from_bytes(data=input_img2.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== MOODBOARD REFERENCE PHOTO (POSE & STUDIO) ==="),
        types.Part.from_bytes(data=moodboard_img.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== PREVIOUS DEFECTIVE DRAFT (SHOWING WRONG VERTICAL STRIPES ON PALLU) ==="),
        types.Part.from_bytes(data=flawed_draft_img.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="=== CRITIC DIRECTIVE: Fix the stripe direction on the hanging pallu so stripes run horizontally across the fall, strictly parallel to the red decorative bands. ===")
    ]

    logger.info("Generating with gemini-3-pro-image in 4K...")
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )

    res = client.models.generate_content(
        model="gemini-3-pro-image",
        contents=contents,
        config=config
    )

    out_image_path = output_dir / "saree3_gemini3_pro_4k.png"
    if res.candidates:
        for part in res.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                out_image_path.write_bytes(part.inline_data.data)
                logger.info(f"✓ Saved Pro generated image to {out_image_path} ({len(part.inline_data.data)} bytes)")
                break

    if not out_image_path.exists():
        raise RuntimeError("Pro Image generation failed.")

    # Audit with Gemini 3.6 Flash Critic
    logger.info("Auditing result with Gemini 3.6 Flash Visual Critic...")
    audit_instruction = (
        "You are an expert AI Master Textile Inspector conducting a Quality Control audit.\n\n"
        "TASK:\n"
        "Audit the GENERATED CATALOG IMAGE against the ORIGINAL GROUND TRUTH PRODUCT PHOTOS.\n"
        "Inspect the black-and-white stripes on the hanging pallu fall.\n"
        "Check whether the stripes run horizontally (parallel to the red Ajrakh bands) or vertically (perpendicular to the red bands)."
    )

    audit_contents = [
        types.Part.from_text(text=audit_instruction),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 1 ==="),
        types.Part.from_bytes(data=input_img1.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 2 ==="),
        types.Part.from_bytes(data=input_img2.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GENERATED CATALOG IMAGE TO AUDIT ==="),
        types.Part.from_bytes(data=out_image_path.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="Conduct the audit and return structured JSON.")
    ]

    res_audit = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=audit_contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TextileQCCritique,
            temperature=0.1
        )
    )

    audit_result = json.loads(res_audit.text)
    audit_path = output_dir / "audit_gemini3_pro.json"
    audit_path.write_text(json.dumps(audit_result, indent=2), encoding="utf-8")

    logger.info("--- AUDIT RESULT ---")
    print(json.dumps(audit_result, indent=2))
    return out_image_path, audit_result

if __name__ == "__main__":
    run_experiment()
