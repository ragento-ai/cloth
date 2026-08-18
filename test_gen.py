import time
import sys
from pathlib import Path
from google.genai import types
from config import settings
from src.vertex_client import get_genai_client

print("Waiting 30s to cool down quota...")
time.sleep(30)

client = get_genai_client()
saree_img = Path("saree/50631.jpg")
mb_img = Path("moodboard_2/1000221736.jpg")

system_instruction = (
    "You are an expert AI Fashion Photographer.\n"
    "GARMENT (UN-DRAPED SAREE PHOTO): Target image shows an un-draped Indian saree cloth.\n"
    "Render an Indian female fashion model wearing and draping this exact saree (silk saree with pleats, shoulder pallu, blouse).\n"
    "MOODBOARD REFERENCE: Extract model pose, lighting, and background atmosphere from the moodboard reference."
)

contents = [
    types.Part.from_text(text=system_instruction),
    types.Part.from_bytes(data=saree_img.read_bytes(), mime_type="image/jpeg"),
    types.Part.from_bytes(data=mb_img.read_bytes(), mime_type="image/jpeg")
]

config = types.GenerateContentConfig(
    response_modalities=["TEXT", "IMAGE"],
    image_config=types.ImageConfig(image_size="4K", aspect_ratio="3:4")
)

print("Sending generate_content request for saree/50631.jpg...")
res = client.models.generate_content(
    model=settings.GENERATION_MODEL,
    contents=contents,
    config=config
)

print("Response candidates:", len(res.candidates) if res.candidates else 0)
if res.candidates:
    for part in res.candidates[0].content.parts:
        if part.inline_data:
            data = part.inline_data.data
            out_path = Path("output/saree_50631_draped.png")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
            print(f"SUCCESS! Saved {out_path} ({len(data)} bytes)")
