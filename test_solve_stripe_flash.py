"""
Solve Stripe Orientation on Saree 3 with Gemini 3.1 Flash Image using Spatial Drape Anchoring.
"""

import sys
import json
import time
import logging
from pathlib import Path
from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from google.genai import types
from src.vertex_client import get_genai_client
from test_critic_detection import TextileQCCritique

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Solve_Stripe_Flash")

def generate_spatial_orientation_guide(out_path: Path):
    """Creates a visual sketch showing horizontal rungs (stripes) across a hanging pallu fall."""
    img = Image.new("RGB", (600, 800), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    
    # Pallu outline
    draw.rectangle([100, 50, 500, 750], fill=(255, 255, 255), outline=(100, 100, 100), width=3)
    
    # Horizontal stripes across the hanging pallu
    for y in range(80, 500, 20):
        draw.line([100, y, 500, y], fill=(20, 20, 20), width=8)
    
    # Red Ajrakh band & Polka band at bottom
    draw.rectangle([100, 500, 500, 700], fill=(180, 20, 30), outline=(120, 10, 20), width=2)
    # Polka dots
    for x in range(150, 480, 70):
        draw.ellipse([x, 570, x+40, 610], fill=(255, 255, 255))
        
    draw.text((120, 20), "CORRECT DRAPE: HORIZONTAL STRIPES PARALLEL TO RED BAND", fill=(0, 0, 0))
    img.save(out_path)
    return out_path

def run_flash_spatial_experiment():
    client = get_genai_client()
    output_dir = ROOT_DIR / "output_sari/3/stripe_orientation_tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    input_img1 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134554.jpg.jpeg"
    input_img2 = ROOT_DIR / "saree_unfolded/3/IMG_20260813_134602.jpg.jpeg"
    moodboard_img = ROOT_DIR / "moodboard_2/1000221736.jpg"
    flawed_draft_img = ROOT_DIR / "output_sari/3/critic_loop/iteration_3_corrected_stripes.png"
    
    guide_path = output_dir / "pallu_spatial_guide.png"
    generate_spatial_orientation_guide(guide_path)

    system_instruction = (
        "You are an expert AI Master Fashion Photographer and Technical Garment CAD Illustrator.\n\n"
        "TASK - FLAWLESS 4K SAREE DRAPING WITH PHYSICAL STRIPE ALIGNMENT:\n"
        "1. PHYSICAL STRIPE & WEAVE GEOMETRY (Ground Truth Images 1 & 2 + Spatial Guide Image 3):\n"
        "   - The black and white stripes and the decorative red Ajrakh pallu bands are strictly PARALLEL to each other.\n"
        "   - HANGING PALLU DRAPE:\n"
        "     As shown in the Spatial Guide (Image 3), all stripes across the hanging pallu MUST run HORIZONTALLY across the width of the fall (horizontal ladder rungs), strictly parallel to the red bands at the bottom.\n"
        "     DO NOT draw vertical pinstripes running into the red band.\n"
        "2. BODY & PLEATS:\n"
        "   - Clean borderless edge-to-edge black and white stripes.\n"
        "3. MODEL & STUDIO (Image 4 - Moodboard):\n"
        "   - Replicate the exact model pose, lighting, and warm architectural studio environment from Image 4 (ignore clothing in Image 4).\n"
        "4. Render commercial 4K ultra-high definition clarity with photorealistic skin and natural cloth physics."
    )

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 1 ==="),
        types.Part.from_bytes(data=input_img1.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== GROUND TRUTH PRODUCT PHOTO 2 ==="),
        types.Part.from_bytes(data=input_img2.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== SPATIAL GUIDANCE SCHEMATIC (CORRECT HORIZONTAL STRIPE FLOW ON PALLU) ==="),
        types.Part.from_bytes(data=guide_path.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="=== MOODBOARD REFERENCE PHOTO (POSE & STUDIO ONLY) ==="),
        types.Part.from_bytes(data=moodboard_img.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== INCORRECT DRAFT (SHOWS WRONG VERTICAL PINSTRIPES ON PALLU - MUST FIX TO HORIZONTAL) ==="),
        types.Part.from_bytes(data=flawed_draft_img.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text="Generate the corrected 4K catalog image with horizontal stripes across the hanging pallu.")
    ]

    logger.info("Generating with gemini-3.1-flash-image using Spatial Guide in 4K...")
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )

    res = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=contents,
        config=config
    )

    out_image_path = output_dir / "saree3_spatial_guide_4k.png"
    if res.candidates:
        for part in res.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                out_image_path.write_bytes(part.inline_data.data)
                logger.info(f"✓ Saved Spatial Guide generated image to {out_image_path} ({len(part.inline_data.data)} bytes)")
                break

    if not out_image_path.exists():
        raise RuntimeError("Generation failed.")

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
    audit_path = output_dir / "audit_spatial_guide.json"
    audit_path.write_text(json.dumps(audit_result, indent=2), encoding="utf-8")

    logger.info("--- AUDIT RESULT ---")
    print(json.dumps(audit_result, indent=2))
    return out_image_path, audit_result

if __name__ == "__main__":
    run_flash_spatial_experiment()
