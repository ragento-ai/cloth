"""
Flask Web Server for Ragento Visual Studio - Studio Grade AI Catalog & Workflow Management.
"""

import os
import io
import json
import hashlib
import logging
import datetime
import fcntl
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

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
THUMB_CACHE_DIR = settings.BASE_DIR / ".thumb-cache"
THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
AUTH_STATE_PATH = settings.OUTPUT_DIR / "auth_state.json"
STUDIO_PASSWORD = os.getenv("STUDIO_PASSWORD", "ragento.ai")
ADMIN_PASSWORD = os.getenv("STUDIO_ADMIN_PASSWORD", "AdminKSSLA@ragento.ai")
AUTH_PROFILES = {
    "viewer": {
        "password": STUDIO_PASSWORD,
        "role": "viewer",
        "label": "Studio User",
        "default_limit": 100,
    },
    "admin": {
        "password": ADMIN_PASSWORD,
        "role": "admin",
        "label": "Admin",
        "default_limit": None,
    },
}
SESSION_SERIALIZER = URLSafeTimedSerializer(
    os.getenv("STUDIO_SESSION_SECRET", f"ragento-studio::{settings.CODE_DIR.resolve()}"),
    salt="studio-session",
)


def get_pipeline():
    global pipeline
    if pipeline is None:
        pipeline = PipelineManager()
    return pipeline

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _password_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _default_auth_state() -> dict:
    return {
        "profiles": {
            "viewer": {
                "label": AUTH_PROFILES["viewer"]["label"],
                "role": "viewer",
                "password_hash": _password_hash(AUTH_PROFILES["viewer"]["password"]),
                "limit": AUTH_PROFILES["viewer"]["default_limit"],
                "generated_count": 0,
                "reserved_count": 0,
            },
            "admin": {
                "label": AUTH_PROFILES["admin"]["label"],
                "role": "admin",
                "password_hash": _password_hash(AUTH_PROFILES["admin"]["password"]),
                "limit": AUTH_PROFILES["admin"]["default_limit"],
                "generated_count": 0,
                "reserved_count": 0,
            },
        }
    }


def _normalize_auth_state(state: dict | None) -> dict:
    normalized = state if isinstance(state, dict) else {}
    profiles = normalized.setdefault("profiles", {})
    defaults = _default_auth_state()["profiles"]
    for key, default_profile in defaults.items():
        profile = profiles.setdefault(key, {})
        for field, default_value in default_profile.items():
            profile.setdefault(field, default_value)
    return normalized


class LockedJSONState:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None
        self.state = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "a+", encoding="utf-8")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        self.handle.seek(0)
        raw = self.handle.read()
        parsed = {}
        if raw.strip():
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {}
        self.state = _normalize_auth_state(parsed)
        return self.state

    def __exit__(self, exc_type, exc, tb):
        if self.handle is None:
            return
        if exc_type is None:
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.write(json.dumps(self.state, indent=2))
            self.handle.flush()
            os.fsync(self.handle.fileno())
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
        self.handle = None


def _get_profile_by_password(password: str):
    for profile_key, profile in AUTH_PROFILES.items():
        if password == profile["password"]:
            return profile_key, profile
    return None, None


def _issue_session_token(profile_key: str, role: str) -> str:
    return SESSION_SERIALIZER.dumps({"profile_key": profile_key, "role": role})


def _read_session():
    token = request.headers.get("X-Studio-Session", "").strip()
    if not token:
        return None
    try:
        return SESSION_SERIALIZER.loads(token, max_age=60 * 60 * 12)
    except (BadSignature, SignatureExpired):
        return None


def _unauthorized(message: str = "Authentication required"):
    return jsonify({"error": message}), 401


def _forbidden(message: str = "Admin access required"):
    return jsonify({"error": message}), 403


def _require_session():
    session = _read_session()
    if not session:
        return None, _unauthorized("Please unlock the studio again.")
    return session, None


def _require_admin_session():
    session, error = _require_session()
    if error:
        return None, error
    if session.get("role") != "admin":
        return None, _forbidden("Admin password required.")
    return session, None


def _get_profile_usage(profile_key: str) -> dict:
    with LockedJSONState(AUTH_STATE_PATH) as state:
        profile = dict(state["profiles"][profile_key])
    remaining = None if profile.get("limit") is None else max(
        0,
        int(profile.get("limit", 0)) - int(profile.get("generated_count", 0)) - int(profile.get("reserved_count", 0)),
    )
    profile["remaining_count"] = remaining
    return profile


def _get_auth_state_snapshot() -> dict:
    with LockedJSONState(AUTH_STATE_PATH) as state:
        return json.loads(json.dumps(state))


def _reserve_generation_quota(profile_key: str, requested_count: int):
    if requested_count <= 0:
        return None
    with LockedJSONState(AUTH_STATE_PATH) as state:
        profile = state["profiles"][profile_key]
        limit = profile.get("limit")
        generated_count = int(profile.get("generated_count", 0))
        reserved_count = int(profile.get("reserved_count", 0))
        if limit is not None and (generated_count + reserved_count + requested_count) > int(limit):
            remaining = max(0, int(limit) - generated_count - reserved_count)
            return {
                "allowed": False,
                "limit": int(limit),
                "generated_count": generated_count,
                "reserved_count": reserved_count,
                "remaining_count": remaining,
                "requested_count": requested_count,
            }
        profile["reserved_count"] = reserved_count + requested_count
        return {
            "allowed": True,
            "limit": None if limit is None else int(limit),
            "generated_count": generated_count,
            "reserved_count": profile["reserved_count"],
            "remaining_count": None if limit is None else max(0, int(limit) - generated_count - profile["reserved_count"]),
            "requested_count": requested_count,
        }


def _finalize_generation_quota(profile_key: str, reserved_count: int, actual_count: int):
    with LockedJSONState(AUTH_STATE_PATH) as state:
        profile = state["profiles"][profile_key]
        current_reserved = int(profile.get("reserved_count", 0))
        profile["reserved_count"] = max(0, current_reserved - max(0, reserved_count))
        profile["generated_count"] = int(profile.get("generated_count", 0)) + max(0, actual_count)


def _release_generation_quota(profile_key: str, reserved_count: int):
    with LockedJSONState(AUTH_STATE_PATH) as state:
        profile = state["profiles"][profile_key]
        current_reserved = int(profile.get("reserved_count", 0))
        profile["reserved_count"] = max(0, current_reserved - max(0, reserved_count))


def _count_requested_outputs(target_sku: str | None, requested_num_shots: int) -> int:
    if requested_num_shots <= 0 or not settings.INPUT_DIR.exists():
        return 0
    total = 0
    for garment_dir in sorted(settings.INPUT_DIR.iterdir()):
        if not garment_dir.is_dir():
            continue
        sku_id = garment_dir.name.replace(" ", "_")
        if target_sku and target_sku != sku_id:
            continue
        product_images = [p for p in garment_dir.glob("*") if allowed_file(p.name)]
        if product_images:
            total += requested_num_shots
    return total


def _normalize_thumb_format(fmt: str | None) -> str:
    normalized = (fmt or "webp").strip().lower()
    if normalized not in {"webp", "jpeg", "png"}:
        return "webp"
    return normalized


def _variant_suffix(fmt: str) -> str:
    return "jpg" if fmt == "jpeg" else fmt


def _thumbnail_cache_path(source_path: Path, width: int, fmt: str, quality: int) -> Path:
    stat = source_path.stat()
    signature = f"{source_path}:{stat.st_mtime_ns}:{stat.st_size}:{width}:{fmt}:{quality}"
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()
    return THUMB_CACHE_DIR / f"{digest}.{_variant_suffix(fmt)}"


def _generate_thumbnail(source_path: Path, width: int, fmt: str, quality: int) -> Path:
    cached_path = _thumbnail_cache_path(source_path, width, fmt, quality)
    if cached_path.exists():
        return cached_path

    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((width, width), Image.Resampling.LANCZOS)
        save_image = image
        save_kwargs = {"optimize": True}

        if fmt == "webp":
            if image.mode not in ("RGB", "RGBA"):
                save_image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            save_kwargs.update({"format": "WEBP", "quality": quality, "method": 6})
        elif fmt == "jpeg":
            if image.mode not in ("RGB", "L"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                alpha = image.getchannel("A") if "A" in image.getbands() else None
                background.paste(image.convert("RGBA"), mask=alpha)
                save_image = background
            elif image.mode != "RGB":
                save_image = image.convert("RGB")
            save_kwargs.update({"format": "JPEG", "quality": quality, "progressive": True})
        else:
            if image.mode not in ("RGB", "RGBA"):
                save_image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            save_kwargs.update({"format": "PNG"})

        cached_path.parent.mkdir(parents=True, exist_ok=True)
        save_image.save(cached_path, **save_kwargs)

    return cached_path


def _send_image_variant(source_path: Path):
    if not source_path.exists():
        return jsonify({"error": "Image not found"}), 404

    width = request.args.get("w", type=int)
    fmt = _normalize_thumb_format(request.args.get("fmt"))
    quality = max(40, min(90, request.args.get("q", default=72, type=int)))

    if not width or width <= 0:
        return send_file(source_path, conditional=True)

    width = max(80, min(width, 1600))
    cached_path = _generate_thumbnail(source_path, width, fmt, quality)
    mimetype = f"image/{fmt}"
    return send_file(cached_path, mimetype=mimetype, conditional=True, max_age=86400)


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

@app.route("/api/auth/verify", methods=["POST"])
def verify_auth():
    data = request.json or {}
    password = (data.get("password") or "").strip()
    profile_key, profile = _get_profile_by_password(password)
    if not profile:
        return jsonify({"error": "Incorrect password"}), 401
    usage = _get_profile_usage(profile_key)
    return jsonify({
        "status": "SUCCESS",
        "session_token": _issue_session_token(profile_key, profile["role"]),
        "role": profile["role"],
        "profile_key": profile_key,
        "quota": {
            "limit": usage.get("limit"),
            "generated_count": usage.get("generated_count", 0),
            "reserved_count": usage.get("reserved_count", 0),
            "remaining_count": usage.get("remaining_count"),
        },
    })


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
    _, error = _require_admin_session()
    if error:
        return error
    admin_stats = get_admin_stats()
    auth_state = _get_auth_state_snapshot()
    
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
        "activity_log": admin_stats.get("activity_log", [])[:30],
        "quota_profiles": auth_state.get("profiles", {}),
    })

@app.route("/api/admin/reset", methods=["POST"])
def reset_admin_analytics():
    """Resets generation click count and activity logs."""
    _, error = _require_admin_session()
    if error:
        return error
    stats = {"generate_click_count": 0, "activity_log": []}
    save_admin_stats(stats)
    return jsonify({"status": "SUCCESS", "message": "Admin metrics reset successfully"})


@app.route("/api/admin/limits", methods=["POST"])
def update_admin_limits():
    _, error = _require_admin_session()
    if error:
        return error

    data = request.json or {}
    profile_key = data.get("profile_key", "viewer")
    limit = data.get("limit")
    if profile_key not in AUTH_PROFILES:
        return jsonify({"error": "Unknown profile"}), 400
    if profile_key == "admin":
        return jsonify({"error": "Admin limit is fixed and cannot be edited here."}), 400
    if limit is None:
        return jsonify({"error": "Limit is required"}), 400
    try:
        parsed_limit = int(limit)
    except (TypeError, ValueError):
        return jsonify({"error": "Limit must be a whole number"}), 400
    if parsed_limit < 0:
        return jsonify({"error": "Limit must be 0 or more"}), 400

    with LockedJSONState(AUTH_STATE_PATH) as state:
        state["profiles"][profile_key]["limit"] = parsed_limit
        profile = dict(state["profiles"][profile_key])

    return jsonify({
        "status": "SUCCESS",
        "profile_key": profile_key,
        "quota": {
            "limit": profile.get("limit"),
            "generated_count": profile.get("generated_count", 0),
            "reserved_count": profile.get("reserved_count", 0),
            "remaining_count": max(
                0,
                int(profile.get("limit", 0)) - int(profile.get("generated_count", 0)) - int(profile.get("reserved_count", 0)),
            ),
        },
    })

@app.route("/api/generate", methods=["POST"])
def trigger_generation():
    """Triggers generation for a specific SKU with optional moodboard selections and transfer controls."""
    session, error = _require_session()
    if error:
        return error

    data = request.json or {}
    target_sku = data.get("sku_id")
    requested_num_shots = int(data.get("num_shots", 3))
    selected_moodboard_filenames = data.get("moodboards", [])
    batch_started_at = datetime.datetime.now()
    batch_id = batch_started_at.strftime("BATCH_%Y%m%d_%H%M%S")
    profile_key = session.get("profile_key", "viewer")
    
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
    requested_output_count = _count_requested_outputs(target_sku, requested_num_shots)
    quota_reservation = _reserve_generation_quota(profile_key, requested_output_count)
    if quota_reservation and not quota_reservation.get("allowed"):
        return jsonify({
            "error": "Generation limit reached. Contact admin to increase your quota.",
            "code": "GENERATION_LIMIT_REACHED",
            "quota": quota_reservation,
        }), 429
    
    garment_dirs = sorted([d for d in input_base_dir.iterdir() if d.is_dir()])
    
    summary_path = output_dir / "batch_execution_summary.json"
    existing_summary = []
    if summary_path.exists():
        try:
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            existing_summary = []

    new_results = []
    try:
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
        _finalize_generation_quota(profile_key, requested_output_count, len(new_results))

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
            "status": "SUCCESS",
            "profile_key": profile_key,
        }
        if "activity_log" not in admin_stats or not isinstance(admin_stats["activity_log"], list):
            admin_stats["activity_log"] = []
        admin_stats["activity_log"].insert(0, log_entry)
        save_admin_stats(admin_stats)

        enriched_results = _enrich_summary_items(final_summary_list)
        enriched_new_results = _enrich_summary_items(new_results)
        quota_usage = _get_profile_usage(profile_key)

        return jsonify({
            "status": "SUCCESS",
            "batch_id": batch_id,
            "batch_label": batch_label,
            "results": enriched_results,
            "new_results": enriched_new_results,
            "quota": {
                "limit": quota_usage.get("limit"),
                "generated_count": quota_usage.get("generated_count", 0),
                "reserved_count": quota_usage.get("reserved_count", 0),
                "remaining_count": quota_usage.get("remaining_count"),
            },
        })
    except Exception:
        _release_generation_quota(profile_key, requested_output_count)
        raise

# Image Static Routes
@app.route("/api/image/input/<garment_dir>/<filename>")
def serve_input_image(garment_dir, filename):
    folder = settings.INPUT_DIR / garment_dir
    return _send_image_variant(folder / filename)

@app.route("/api/image/moodboard/<filename>")
def serve_moodboard_image(filename):
    return _send_image_variant(settings.MOODBOARD_DIR / filename)

@app.route("/api/image/output/<path:filename>")
def serve_output_image(filename):
    return _send_image_variant(settings.OUTPUT_DIR / filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
