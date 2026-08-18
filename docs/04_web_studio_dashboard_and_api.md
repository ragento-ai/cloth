# 04. Web Studio Dashboard & REST API Specification

Ragento Visual Studio includes an intuitive, production-ready Web Dashboard built with standard web technologies (HTML5, Vanilla CSS with custom theme variables, JavaScript, Glassmorphism aesthetics) backed by a Flask web server ([`server.py`](file:///home/amrit-lal-singh/Experimentation/cloth/server.py)).

---

## 🖥️ Web Interface Features ([`static/index.html`](file:///home/amrit-lal-singh/Experimentation/cloth/static/index.html))

### 1. Garment Division Gallery
- Displays all loaded SKU product folders (e.g. `GARMENT_1`, `GARMENT_2`, `GARMENT_3`, `GARMENT_4`, `saree`).
- Shows thumbnail grid of product photos for each SKU.
- Supports drag-and-drop uploading of new target garment product shots.

### 2. Moodboard Reference Library
- Visual gallery displaying all pose, lighting, and environment reference images.
- Allows multi-select checkmarking to assign reference photos for generation runs.
- Includes photo upload modal for expanding moodboard catalogs.

### 3. Interactive Generation Workbench & Collapsible Transfer Controls
- **Shot Count Selector**: 1 to 5 catalog shots.
- **Collapsible Advanced Controls Panel**:
  - 3-State Transfer Control Matrix (`Model`, `Pose`, `Background`).
  - Target Resolution Selector (`1024x1024`, `2048x2048`, `4096x4096`).
  - Special Creative Directives text input for high-priority prompt overrides.
- **Generate AI Catalog Button**: Triggers asynchronous generation pipeline with real-time progress notification.

### 4. Studio Summary & QC History Gallery
- Displays live cards for all generated assets.
- **Human-Readable Parameters**: Shows exact source parameters (`Pose Source`, `Lighting Source`, `Framing`, `Controls Used`, `Creative Directives`).
- **QC Inspection Details**: Shows status pill (`AUTO APPROVED` / `FLAGGED`), composite quality score, base color score, pattern match score, and detected defects.
- **Cache-Busting Image Previews**: Ensures refreshed renders update immediately in browser.

### 5. Admin Analytics Dashboard & Security Overlay
- Protected by a passcode modal overlay (`Passcode: admin123`).
- **Metrics Tracked**:
  - `Generate AI Catalog` button click count.
  - Total catalog images generated.
  - Auto-approved vs Flagged for Human Review split.
  - Active SKUs and Moodboard count.
  - Resolution distribution (`1024x1024`, `2048x2048`, `4096x4096`).
  - Persistent activity execution log.

---

## 🔌 REST API Specification

### 1. Catalog & Asset Queries

#### `GET /api/skus`
- **Description**: Returns all available garment SKU folders and their input photos.
- **Response**:
```json
[
  {
    "id": "GARMENT_1",
    "name": "GARMENT 1",
    "image_count": 2,
    "images": [
      { "filename": "front.jpg", "url": "/api/image/input/GARMENT%201/front.jpg" }
    ],
    "sample_image": "/api/image/input/GARMENT%201/front.jpg"
  }
]
```

#### `GET /api/moodboards`
- **Description**: Returns all moodboard reference images.
- **Response**:
```json
[
  { "filename": "K10043G.jpg", "url": "/api/image/moodboard/K10043G.jpg" }
]
```

#### `GET /api/summary`
- **Description**: Returns complete list of historical generation outputs and QC reports from `output/batch_execution_summary.json`.

---

### 2. Asset Upload & Deletion

#### `POST /api/upload/garment`
- **Form Data**: `sku_name` (string), `files` (file array)
- **Description**: Uploads new target garment images to SKU folder.

#### `POST /api/upload/moodboard`
- **Form Data**: `files` (file array)
- **Description**: Uploads new reference photos to moodboard library.

#### `POST /api/delete/garment_photo`
- **JSON Payload**: `{ "sku_id": "GARMENT_1", "filename": "photo.jpg" }`

#### `POST /api/delete/moodboard_photo`
- **JSON Payload**: `{ "filename": "ref.jpg" }`

---

### 3. Generation Engine Trigger

#### `POST /api/generate`
- **JSON Payload**:
```json
{
  "sku_id": "GARMENT_1",
  "num_shots": 3,
  "moodboards": ["K10043G.jpg", "K10048G.jpg"],
  "controls": {
    "model": "moodboard",
    "pose": "moodboard",
    "background": "moodboard",
    "resolution": "4096x4096",
    "custom_override": "Must be an authentic Indian Saree with pleats"
  }
}
```
- **Response**: Returns array of executed shot results, image URLs, QC scores, and routing status.

---

### 4. Admin Analytics Endpoints

#### `GET /api/admin/stats`
- **Description**: Returns aggregated metrics, click counts, resolution breakdown, and activity log.

#### `POST /api/admin/reset`
- **Description**: Resets admin statistics and activity logs.
