import time
import sys
from pathlib import Path
from google.genai import types
from config import settings
from src.vertex_client import get_genai_client

ROOT_DIR = Path(__file__).resolve().parent
output_path = ROOT_DIR / "output" / "saree_draped_catalog" / "50631_draped_catalog.png"
output_path.parent.mkdir(parents=True, exist_ok=True)

print("Pausing 30s for Vertex AI API quota cooldown...")
time.sleep(30)

client = get_genai_client()
saree_img = ROOT_DIR / "saree" / "50631.jpg"
mb_img = ROOT_DIR / "moodboard_2" / "1000221736.jpg"

system_instruction = (
    "You are an expert AI Luxury Fashion Photographer and Master Stylist rendering ultra-high-definition catalog masters.\n\n"
    "CRITICAL TASK - SAREE DRAPING FROM UN-DRAPED / FLAT GARMENT PHOTO:\n"
    "1. TARGET GARMENT (UN-DRAPED SAREE PHOTO):\n"
    "   - The input product shot depicts an un-draped / flat / folded Indian saree cloth piece.\n"
    "   - Extract exact base fabric color palette, textile weave, pattern motifs, zari/printed borders, and pallu design.\n"
    "   - Render an elegant female fashion model DRAPING and WEARING this exact saree as a complete traditional Indian saree ensemble (6-yard draped silk saree with waist pleats, shoulder pallu drape, tucked border, and matching/fitted blouse).\n"
    "   - STRICTLY FORBIDDEN: Do not leave the garment flat or folded. Do not render a kurta, salwar suit, pants, or dupatta. It MUST be a draped saree.\n\n"
    "2. MOODBOARD REFERENCE SHOTS:\n"
    "   - Extract model pose, posture, facial expression, camera framing, studio lighting, and background ambience from moodboard reference image.\n"
    "   - IGNORE ALL CLOTHING WORN IN THE MOODBOARD REFERENCE! ONLY USE MOODBOARD FOR MODEL POSE AND ENVIRONMENT.\n\n"
    "OUTPUT SPECIFICATION:\n"
    "Render a luxury fashion D2C e-commerce catalog master in high-definition 4K resolution with razor-sharp textile texture, crisp saree pleating, and realistic fabric drape physics."
)

contents = [
    types.Part.from_text(text=system_instruction),
    types.Part.from_text(text="=== TARGET GARMENT SOURCE OF TRUTH (UN-DRAPED SAREE CLOTH) ==="),
    types.Part.from_bytes(data=saree_img.read_bytes(), mime_type="image/jpeg"),
    types.Part.from_text(text="=== MOODBOARD REFERENCE (SOURCE FOR MODEL POSE & ENVIRONMENT ONLY - IGNORE CLOTHING) ==="),
    types.Part.from_bytes(data=mb_img.read_bytes(), mime_type="image/jpeg")
]

config = types.GenerateContentConfig(
    response_modalities=["TEXT", "IMAGE"],
    image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
)

print(f"Generating draped saree output for {saree_img.name} using {mb_img.name}...")
res = client.models.generate_content(
    model=settings.GENERATION_MODEL,
    contents=contents,
    config=config
)

if res.candidates:
    for part in res.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            data = part.inline_data.data
            output_path.write_bytes(data)
            print(f"✓ SUCCESS: Written {output_path} ({len(data)} bytes)")
            break
else:
    print("❌ Generation failed: No candidates returned.")
