"""
Flask Web Server for Ragento Visual Studio - Studio Grade AI Catalog & Workflow Management.
"""

import os
import json
import logging
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import settings
from src.pipeline import PipelineManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app)

pipeline = PipelineManager()

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/skus", methods=["GET"])
def get_skus():
    """List all available SKU directories with full image details for Garment-wise Division Gallery."""
    input_base_dir = settings.INPUT_DIR
    if not input_base_dir.exists():
        return jsonify([])
    
    skus = []
    for d in sorted(input_base_dir.iterdir()):
        if d.is_dir():
            images = [
                {
                    "filename": p.name,
                    "url": f"/api/image/input/{d.name}/{p.name}"
                }
                for p in sorted(d.glob("*")) if allowed_file(p.name)
            ]
            skus.append({
                "id": d.name.replace(" ", "_"),
                "name": d.name,
                "image_count": len(images),
                "images": images,
                "sample_image": images[0]["url"] if images else None
            })
    return jsonify(skus)

@app.route("/api/moodboards", methods=["GET"])
def get_moodboards():
    """List all available moodboard reference images for Moodboard Gallery."""
    moodboard_dir = settings.MOODBOARD_DIR
    if not moodboard_dir.exists():
        return jsonify([])
    
    moodboards = []
    for p in sorted(moodboard_dir.glob("*")):
        if allowed_file(p.name):
            moodboards.append({
                "filename": p.name,
                "url": f"/api/image/moodboard/{p.name}"
            })
    return jsonify(moodboards)

@app.route("/api/upload/garment", methods=["POST"])
def upload_garment():
    """Upload custom garment images into a specified SKU folder."""
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400
    
    sku_name = request.form.get("sku_name", "GARMENT_NEW").strip().replace(" ", "_")
    target_dir = settings.INPUT_DIR / sku_name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    files = request.files.getlist("files")
    for f in files:
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            dest = target_dir / filename
            f.save(dest)
            saved_files.append(filename)
            
    return jsonify({"status": "SUCCESS", "sku_id": sku_name, "files": saved_files})

@app.route("/api/upload/moodboard", methods=["POST"])
def upload_moodboard():
    """Upload custom moodboard reference images."""
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400
    
    target_dir = settings.MOODBOARD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    files = request.files.getlist("files")
    for f in files:
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            dest = target_dir / filename
            f.save(dest)
            saved_files.append(filename)
            
    return jsonify({"status": "SUCCESS", "files": saved_files})

@app.route("/api/delete/garment_photo", methods=["POST"])
def delete_garment_photo():
    """Deletes a photo from a garment SKU folder."""
    data = request.json or {}
    sku_id = data.get("sku_id")
    filename = data.get("filename")
    if not sku_id or not filename:
        return jsonify({"error": "Missing parameters"}), 400
    
    target_dir = settings.INPUT_DIR / sku_id
    if not target_dir.exists():
        target_dir = settings.INPUT_DIR / sku_id.replace("_", " ")
        
    file_path = target_dir / filename
    if file_path.exists():
        file_path.unlink()
        return jsonify({"status": "SUCCESS"})
    return jsonify({"error": "File not found"}), 404

@app.route("/api/delete/moodboard_photo", methods=["POST"])
def delete_moodboard_photo():
    """Deletes a photo from the moodboard reference gallery."""
    data = request.json or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Missing filename"}), 400
    
    file_path = settings.MOODBOARD_DIR / filename
    if file_path.exists():
        file_path.unlink()
        return jsonify({"status": "SUCCESS"})
    return jsonify({"error": "File not found"}), 404

@app.route("/api/summary", methods=["GET"])
def get_batch_summary():
    """Returns the latest batch_execution_summary.json results."""
    summary_path = settings.OUTPUT_DIR / "batch_execution_summary.json"
    if not summary_path.exists():
        return jsonify([])
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generate", methods=["POST"])
def trigger_generation():
    """Triggers generation for a specific SKU with optional moodboard selections."""
    data = request.json or {}
    target_sku = data.get("sku_id")
    requested_num_shots = int(data.get("num_shots", 3))
    selected_moodboard_filenames = data.get("moodboards", [])
    
    input_base_dir = settings.INPUT_DIR
    moodboard_dir = settings.MOODBOARD_DIR
    output_dir = settings.OUTPUT_DIR
    
    # Filter specific selected moodboards if provided, else use all available
    if selected_moodboard_filenames and len(selected_moodboard_filenames) > 0:
        moodboard_images = [
            moodboard_dir / fname for fname in selected_moodboard_filenames
            if (moodboard_dir / fname).exists()
        ]
    else:
        moodboard_images = sorted([
            p for p in moodboard_dir.glob("*")
            if allowed_file(p.name)
        ])
    
    garment_dirs = sorted([d for d in input_base_dir.iterdir() if d.is_dir()])
    
    summary_path = output_dir / "batch_execution_summary.json"
    existing_summary = []
    if summary_path.exists():
        try:
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            existing_summary = []

    summary_map = {f"{item.get('sku_id')}_{item.get('shot_number')}": item for item in existing_summary}
    
    for garment_dir in garment_dirs:
        sku_id = garment_dir.name.replace(" ", "_")
        if target_sku and target_sku != sku_id:
            continue
            
        product_images = sorted([
            p for p in garment_dir.glob("*")
            if allowed_file(p.name)
        ])
        
        if not product_images:
            continue
            
        logger.info(f"UI Triggered Generation for SKU {sku_id} ({requested_num_shots} shots) with {len(moodboard_images)} moodboards...")
        results = pipeline.process_sku_multi_pose(
            sku_id=sku_id,
            product_image_paths=product_images,
            moodboard_image_paths=moodboard_images,
            requested_num_shots=requested_num_shots
        )
        for r in results:
            key = f"{r.get('sku_id')}_{r.get('shot_number')}"
            summary_map[key] = r

    final_summary_list = list(summary_map.values())
    summary_path.write_text(json.dumps(final_summary_list, indent=2), encoding="utf-8")
    
    return jsonify({"status": "SUCCESS", "results": final_summary_list})

# Image Static Routes
@app.route("/api/image/input/<garment_dir>/<filename>")
def serve_input_image(garment_dir, filename):
    folder = settings.INPUT_DIR / garment_dir
    return send_from_directory(folder, filename)

@app.route("/api/image/moodboard/<filename>")
def serve_moodboard_image(filename):
    return send_from_directory(settings.MOODBOARD_DIR, filename)

@app.route("/api/image/output/<path:filename>")
def serve_output_image(filename):
    return send_from_directory(settings.OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
