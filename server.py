"""
Flask Web Server for Ragento Visual Studio - Studio Grade AI Catalog & Workflow Management.
Featuring Single Moodboard Allocation, Gemini 3.1 Flash Image Generation, and 2-Pass Visual Critic Refinement.
"""

import os
import json
import logging
import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import settings
from models import TransferControls, RefineRequest
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

def get_admin_stats():
    """Load or initialize persistent admin statistics."""
    stats_path = settings.OUTPUT_DIR / "admin_stats.json"
    default_stats = {
        "generate_click_count": 0,
        "refine_click_count": 0,
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
        return jsonify(data)
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

    # Calculate cumulative studio API costs and tokens across all shots and critique loops
    total_cost_usd = 0.0
    total_prompt_tokens = 0
    total_candidates_tokens = 0
    total_cached_tokens = 0
    total_tokens = 0

    for item in summary_data:
        cost_metrics = item.get("cost_metrics", {})
        item_cost = cost_metrics.get("total_cost_usd")
        if item_cost is not None:
            total_cost_usd += float(item_cost)
            total_prompt_tokens += int(cost_metrics.get("prompt_tokens", 0))
            total_candidates_tokens += int(cost_metrics.get("candidates_tokens", 0))
            total_cached_tokens += int(cost_metrics.get("cached_tokens", 0))
            total_tokens += int(cost_metrics.get("total_tokens", 0))
        else:
            # Baseline estimation for legacy generations: $0.030 per image
            total_cost_usd += 0.030

    avg_cost_per_shot = (total_cost_usd / total_images_generated) if total_images_generated > 0 else 0.0

    # Resolution breakdown (Enforcing 4K)
    res_counts = {"1024x1024": 0, "2048x2048": 0, "4096x4096": 0}
    for item in summary_data:
        res = item.get("controls", {}).get("resolution", "4096x4096")
        res_counts[res] = res_counts.get(res, 0) + 1

    # SKU and Moodboard counts
    input_base_dir = settings.INPUT_DIR
    sku_count = len([d for d in input_base_dir.iterdir() if d.is_dir()]) if input_base_dir.exists() else 0

    moodboard_dir = settings.MOODBOARD_DIR
    moodboard_count = len([p for p in moodboard_dir.glob("*") if allowed_file(p.name)]) if moodboard_dir.exists() else 0

    return jsonify({
        "generate_click_count": admin_stats.get("generate_click_count", 0),
        "refine_click_count": admin_stats.get("refine_click_count", 0),
        "total_images_generated": total_images_generated,
        "auto_approved_count": auto_approved_count,
        "flagged_count": flagged_count,
        "total_cost_usd": round(total_cost_usd, 4),
        "formatted_total_cost": f"${total_cost_usd:.4f}",
        "avg_cost_per_shot": f"${avg_cost_per_shot:.4f}",
        "total_prompt_tokens": total_prompt_tokens,
        "total_candidates_tokens": total_candidates_tokens,
        "total_cached_tokens": total_cached_tokens,
        "total_tokens": total_tokens,
        "total_skus": sku_count,
        "total_moodboards": moodboard_count,
        "resolution_counts": res_counts,
        "activity_log": admin_stats.get("activity_log", [])[:30]
    })

@app.route("/api/admin/reset", methods=["POST"])
def reset_admin_analytics():
    """Resets generation click count and activity logs."""
    stats = {"generate_click_count": 0, "refine_click_count": 0, "activity_log": []}
    save_admin_stats(stats)
    return jsonify({"status": "SUCCESS", "message": "Admin metrics reset successfully"})

@app.route("/api/generate", methods=["POST"])
def trigger_generation():
    """Triggers generation for a specific SKU with 1-to-1 moodboard mapping and selective transfer controls."""
    data = request.json or {}
    target_sku = data.get("sku_id")
    requested_num_shots = int(data.get("num_shots", 3))
    selected_moodboard_filenames = data.get("moodboards", [])
    
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
    
    # Moodboard selection validation:
    # If user selected specific moodboards, ensure count is sufficient or guide them
    if selected_moodboard_filenames and len(selected_moodboard_filenames) > 0:
        if len(selected_moodboard_filenames) < requested_num_shots:
            return jsonify({
                "error": f"You selected {len(selected_moodboard_filenames)} moodboard(s) for {requested_num_shots} requested shots. Please select at least {requested_num_shots} moodboards, or deselect all to sample from the full library."
            }), 400
        
        moodboard_images = [
            moodboard_dir / fname for fname in selected_moodboard_filenames
            if (moodboard_dir / fname).exists()
        ]
    else:
        moodboard_images = sorted([
            p for p in moodboard_dir.glob("*")
            if allowed_file(p.name)
        ])
    
    if not moodboard_images:
        return jsonify({"error": "No moodboard reference images found in studio repository."}), 400

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
            
        logger.info(f"UI Triggered Generation for SKU {sku_id} ({requested_num_shots} shots, 1-to-1 Moodboard)...")
        results = pipeline.process_sku_multi_pose(
            sku_id=sku_id,
            product_image_paths=product_images,
            moodboard_image_paths=moodboard_images,
            requested_num_shots=requested_num_shots,
            controls=controls
        )
        new_results.extend(results)

    final_summary_list = new_results + existing_summary
    summary_path.write_text(json.dumps(final_summary_list, indent=2), encoding="utf-8")
    
    # Log activity entry for admin analytics
    log_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sku_id": target_sku or "ALL_SKUS",
        "requested_shots": requested_num_shots,
        "generated_shots": len(new_results),
        "resolution": controls.resolution,
        "custom_override": controls.custom_override,
        "status": "SUCCESS"
    }
    if "activity_log" not in admin_stats or not isinstance(admin_stats["activity_log"], list):
        admin_stats["activity_log"] = []
    admin_stats["activity_log"].insert(0, log_entry)
    save_admin_stats(admin_stats)
    
    return jsonify({"status": "SUCCESS", "results": final_summary_list})

@app.route("/api/refine", methods=["POST"])
def trigger_refinement():
    """Triggers 2-pass self-correcting Visual Critic refinement for a specific output asset."""
    data = request.json or {}
    sku_id = data.get("sku_id")
    image_path = data.get("image_path")
    user_feedback = data.get("user_feedback", "").strip()
    max_iterations = int(data.get("max_iterations", 2))

    if not sku_id or not image_path:
        return jsonify({"error": "Missing 'sku_id' or 'image_path' for refinement."}), 400

    admin_stats = get_admin_stats()
    admin_stats["refine_click_count"] = admin_stats.get("refine_click_count", 0) + 1

    try:
        logger.info(f"Triggering 2-pass Visual Critic refinement for SKU {sku_id} on {image_path}...")
        updated_asset = pipeline.refine_output_shot(
            sku_id=sku_id,
            target_image_path=image_path,
            user_feedback=user_feedback,
            max_iterations=max_iterations
        )

        # Reload updated summary
        summary_path = settings.OUTPUT_DIR / "batch_execution_summary.json"
        all_summary = []
        if summary_path.exists():
            try:
                all_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                all_summary = []

        # Log admin activity
        log_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sku_id": sku_id,
            "requested_shots": 1,
            "generated_shots": 1,
            "resolution": "2-Pass Refined (4K)",
            "custom_override": f"Refined: {user_feedback}" if user_feedback else "Critic 2-Pass Refinement",
            "status": "REFINED_APPROVED"
        }
        if "activity_log" not in admin_stats or not isinstance(admin_stats["activity_log"], list):
            admin_stats["activity_log"] = []
        admin_stats["activity_log"].insert(0, log_entry)
        save_admin_stats(admin_stats)

        return jsonify({
            "status": "SUCCESS",
            "updated_asset": updated_asset,
            "summary": all_summary
        })
    except Exception as e:
        logger.error(f"Refinement error for {sku_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

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
