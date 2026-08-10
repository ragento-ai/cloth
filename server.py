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
from models import TransferControls
from src.pipeline import PipelineManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app)
settings.ensure_runtime_dirs()

pipeline = None

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def get_pipeline():
    global pipeline
    if pipeline is None:
        pipeline = PipelineManager()
    return pipeline

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _resolve_prompt_path(json_prompt_path):
    if not json_prompt_path:
        return None
    raw_path = Path(json_prompt_path)
    candidates = [raw_path, settings.OUTPUT_DIR / raw_path.name]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _get_input_folder_for_sku(sku_id):
    candidates = [settings.INPUT_DIR / sku_id, settings.INPUT_DIR / sku_id.replace("_", " ")]
    for folder in candidates:
        if folder.exists():
            return folder
    return None


def _build_input_image_url(sku_id, filename):
    folder = _get_input_folder_for_sku(sku_id)
    if not folder:
        return None
    file_path = folder / filename
    if not file_path.exists():
        return None
    return f"/api/image/input/{folder.name}/{filename}"


def _build_moodboard_image_url(filename):
    if not filename:
        return None
    file_path = settings.MOODBOARD_DIR / filename
    if not file_path.exists():
        return None
    return f"/api/image/moodboard/{filename}"


def _dedupe_source_images(images):
    seen = set()
    deduped = []
    for image in images:
        key = (image.get("filename"), image.get("url"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(image)
    return deduped


def _extract_source_assets(item):
    prompt_path = _resolve_prompt_path(item.get("json_prompt_path"))
    payload = {}
    if prompt_path:
        try:
            payload = json.loads(prompt_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

    garment_identity = payload.get("garment_identity", {})
    composition_spec = payload.get("composition_spec", {})

    target_images = []
    for filename in garment_identity.get("source_images", []) or []:
        url = _build_input_image_url(item.get("sku_id", ""), filename)
        if url:
            target_images.append({"filename": filename, "url": url})

    reference_names = []
    for name in [
        composition_spec.get("pose_source"),
        composition_spec.get("lighting_source"),
        item.get("pose_source"),
    ]:
        if name and name not in reference_names:
            reference_names.append(name)

    reference_images = []
    missing_reference_names = []
    for filename in reference_names:
        url = _build_moodboard_image_url(filename)
        if url:
            reference_images.append({"filename": filename, "url": url})
        else:
            missing_reference_names.append(filename)

    target_images = _dedupe_source_images(target_images)
    reference_images = _dedupe_source_images(reference_images)

    return {
        "target_images": target_images,
        "reference_images": reference_images,
        "missing_reference_names": missing_reference_names,
        "primary_target_image": target_images[0] if target_images else None,
        "primary_reference_image": reference_images[0] if reference_images else None,
    }


def _enrich_summary_items(items):
    enriched = []
    for item in items:
        item_copy = dict(item)
        item_copy["source_assets"] = _extract_source_assets(item_copy)
        enriched.append(item_copy)
    return enriched

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

import datetime

def get_admin_stats():
    """Load or initialize persistent admin statistics."""
    stats_path = settings.OUTPUT_DIR / "admin_stats.json"
    default_stats = {
        "generate_click_count": 0,
        "activity_log": []
    }
    if stats_path.exists():
        try:
            return json.loads(stats_path.read_text(encoding="utf-8"))
        except Exception:
            return default_stats
    return default_stats

def save_admin_stats(stats):
    """Save persistent admin statistics."""
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stats_path = settings.OUTPUT_DIR / "admin_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

@app.route("/api/summary", methods=["GET"])
def get_batch_summary():
    """Returns the latest batch_execution_summary.json results."""
    summary_path = settings.OUTPUT_DIR / "batch_execution_summary.json"
    if not summary_path.exists():
        return jsonify([])
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return jsonify(_enrich_summary_items(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/stats", methods=["GET"])
def get_admin_analytics():
    """Returns detailed statistics and metrics for the Admin Dashboard."""
    admin_stats = get_admin_stats()
    
    # Read summary list for output metrics
    summary_path = settings.OUTPUT_DIR / "batch_execution_summary.json"
    summary_data = []
    if summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            summary_data = []

    total_images_generated = len(summary_data)
    auto_approved_count = sum(1 for item in summary_data if item.get("status") == "AUTO_APPROVED")
    flagged_count = total_images_generated - auto_approved_count

    # Resolution breakdown
    res_counts = {"1024x1024": 0, "2048x2048": 0, "4096x4096": 0}
    for item in summary_data:
        res = item.get("controls", {}).get("resolution", "2048x2048")
        res_counts[res] = res_counts.get(res, 0) + 1

    # SKU and Moodboard counts
    input_base_dir = settings.INPUT_DIR
    sku_count = len([d for d in input_base_dir.iterdir() if d.is_dir()]) if input_base_dir.exists() else 0

    moodboard_dir = settings.MOODBOARD_DIR
    moodboard_count = len([p for p in moodboard_dir.glob("*") if allowed_file(p.name)]) if moodboard_dir.exists() else 0

    return jsonify({
        "generate_click_count": admin_stats.get("generate_click_count", 0),
        "total_images_generated": total_images_generated,
        "auto_approved_count": auto_approved_count,
        "flagged_count": flagged_count,
        "total_skus": sku_count,
        "total_moodboards": moodboard_count,
        "resolution_counts": res_counts,
        "activity_log": admin_stats.get("activity_log", [])[:30]
    })

@app.route("/api/admin/reset", methods=["POST"])
def reset_admin_analytics():
    """Resets generation click count and activity logs."""
    stats = {"generate_click_count": 0, "activity_log": []}
    save_admin_stats(stats)
    return jsonify({"status": "SUCCESS", "message": "Admin metrics reset successfully"})

@app.route("/api/generate", methods=["POST"])
def trigger_generation():
    """Triggers generation for a specific SKU with optional moodboard selections and transfer controls."""
    data = request.json or {}
    target_sku = data.get("sku_id")
    requested_num_shots = int(data.get("num_shots", 3))
    selected_moodboard_filenames = data.get("moodboards", [])
    batch_started_at = datetime.datetime.now()
    batch_id = batch_started_at.strftime("BATCH_%Y%m%d_%H%M%S")
    
    # Track admin generate click count
    admin_stats = get_admin_stats()
    admin_stats["generate_click_count"] = admin_stats.get("generate_click_count", 0) + 1
    
    # Parse transfer controls from request
    controls_raw = data.get("controls", {})
    controls = TransferControls(
        background=controls_raw.get("background", "auto"),
        pose=controls_raw.get("pose", "auto"),
        model=controls_raw.get("model", "auto"),
        resolution=controls_raw.get("resolution", "2048x2048"),
        custom_override=controls_raw.get("custom_override", None)
    )
    
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

    moodboard_label = (
        Path(selected_moodboard_filenames[0]).stem if selected_moodboard_filenames
        else (moodboard_images[0].stem if moodboard_images else "Auto Moodboard")
    )
    batch_label = f"{(target_sku or 'ALL_SKUS')} x {moodboard_label}"
    
    garment_dirs = sorted([d for d in input_base_dir.iterdir() if d.is_dir()])
    
    summary_path = output_dir / "batch_execution_summary.json"
    existing_summary = []
    if summary_path.exists():
        try:
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            existing_summary = []

    new_results = []
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
            
        logger.info(f"UI Triggered Generation for SKU {sku_id} ({requested_num_shots} shots) with controls: {controls.model_dump()}...")
        results = get_pipeline().process_sku_multi_pose(
            sku_id=sku_id,
            product_image_paths=product_images,
            moodboard_image_paths=moodboard_images,
            requested_num_shots=requested_num_shots,
            controls=controls,
            batch_id=batch_id,
            batch_label=batch_label,
        )
        new_results.extend(results)

    final_summary_list = new_results + existing_summary
    summary_path.write_text(json.dumps(final_summary_list, indent=2), encoding="utf-8")
    
    # Log activity entry for admin analytics
    log_entry = {
        "timestamp": batch_started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "batch_id": batch_id,
        "batch_label": batch_label,
        "sku_id": target_sku or "ALL_SKUS",
        "requested_shots": requested_num_shots,
        "generated_shots": len(new_results),
        "resolution": controls.resolution,
        "moodboards": selected_moodboard_filenames,
        "custom_override": controls.custom_override,
        "status": "SUCCESS"
    }
    if "activity_log" not in admin_stats or not isinstance(admin_stats["activity_log"], list):
        admin_stats["activity_log"] = []
    admin_stats["activity_log"].insert(0, log_entry)
    save_admin_stats(admin_stats)
    
    enriched_results = _enrich_summary_items(final_summary_list)
    enriched_new_results = _enrich_summary_items(new_results)

    return jsonify({
        "status": "SUCCESS",
        "batch_id": batch_id,
        "batch_label": batch_label,
        "results": enriched_results,
        "new_results": enriched_new_results,
    })

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
