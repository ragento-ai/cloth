import time
import json
import logging
from pathlib import Path
from PIL import Image

from google.genai import types
from config import settings
from src.vertex_client import get_genai_client
from src.inspector import VisualQCInspector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Saree_Batch_Runner")

ROOT_DIR = Path(__file__).resolve().parent
SAREE_DIR = ROOT_DIR / "saree"
MOODBOARD_2_DIR = ROOT_DIR / "moodboard_2"
OUTPUT_DIR = ROOT_DIR / "output" / "saree_moodboard2_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = get_genai_client()
inspector = VisualQCInspector()

mb_img = MOODBOARD_2_DIR / "1000221736.jpg"
remaining_sarees = ["50632.jpg", "IMG_20251203_180500.jpg"]

system_instruction = (
    "You are an expert AI Luxury Fashion Photographer and Master Stylist rendering ultra-high-definition catalog masters.\n\n"
    "CRITICAL TASK - SAREE DRAPING FROM UN-DRAPED / FLAT GARMENT PHOTO:\n"
    "1. TARGET GARMENT (UN-DRAPED SAREE PHOTO):\n"
    "   - Extract exact base fabric color palette, textile weave, pattern motifs, zari/printed borders, and pallu design.\n"
    "   - Render an elegant female fashion model DRAPING and WEARING this exact saree as a complete traditional Indian saree ensemble (6-yard draped silk saree with waist pleats, shoulder pallu drape, tucked border, and matching/fitted blouse).\n"
    "   - STRICTLY FORBIDDEN: Do not leave the garment flat or folded. Do not render a kurta, salwar suit, pants, or dupatta. It MUST be a draped saree.\n\n"
    "2. MOODBOARD REFERENCE SHOTS:\n"
    "   - Extract model pose, posture, facial expression, camera framing, studio lighting, and background ambience from moodboard reference image.\n"
    "   - IGNORE ALL CLOTHING WORN IN THE MOODBOARD REFERENCE! ONLY USE MOODBOARD FOR MODEL POSE AND ENVIRONMENT.\n\n"
    "OUTPUT SPECIFICATION:\n"
    "Render a luxury fashion D2C e-commerce catalog master in high-definition 4K resolution with razor-sharp textile texture, crisp saree pleating, and realistic fabric drape physics."
)

for saree_name in remaining_sarees:
    saree_file = SAREE_DIR / saree_name
    sku_name = saree_file.stem
    output_file = OUTPUT_DIR / f"{sku_name}_shot_1_mb_1000221736_draped_catalog.png"

    if output_file.exists():
        logger.info(f"Skipping {output_file.name} (already exists)")
        continue

    logger.info(f"\n==========================================================================")
    logger.info(f" Processing Saree: {saree_name} -> {output_file.name}")
    logger.info(f"==========================================================================")
    logger.info("Pausing 45s for Vertex AI API quota cooldown...")
    time.sleep(45)

    contents = [
        types.Part.from_text(text=system_instruction),
        types.Part.from_text(text="=== TARGET GARMENT SOURCE OF TRUTH (UN-DRAPED SAREE CLOTH) ==="),
        types.Part.from_bytes(data=saree_file.read_bytes(), mime_type="image/jpeg"),
        types.Part.from_text(text="=== MOODBOARD REFERENCE (SOURCE FOR MODEL POSE & ENVIRONMENT ONLY - IGNORE CLOTHING) ==="),
        types.Part.from_bytes(data=mb_img.read_bytes(), mime_type="image/jpeg")
    ]

    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
    )

    logger.info(f"Executing Gemini 3 Pro Image generation for {saree_name}...")
    res = client.models.generate_content(
        model=settings.GENERATION_MODEL,
        contents=contents,
        config=config
    )

    if res.candidates:
        for part in res.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                output_file.write_bytes(data)
                logger.info(f"✓ SUCCESS: Saved {output_file.name} ({len(data)} bytes)")
                break

    if output_file.exists():
        try:
            qc_report = inspector.inspect(product_image_paths=[saree_file], generated_image_path=output_file)
            logger.info(f"✓ QC Report for {sku_name}: Passed={qc_report.pass_quality_gate}, Score={qc_report.composite_quality_score:.2f}")
        except Exception as e:
            logger.warning(f"QC Inspection failed for {sku_name}: {e}")

logger.info("\nAll saree generations completed successfully!")
