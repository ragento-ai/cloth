# Ragento Visual Studio - AI Fashion Generation Platform

A multi-shot identity-verified fashion visual generation system powered by **Gemini 3.6 Flash** and **Gemini 3 Pro Image**. Ragento Visual Studio automates multi-pose model shot planning, high-fidelity garment synthesis, and automated quality control inspection.

---

## Workspace Directory Structure & Assets Guide

To run the pipeline and server, organize your local project directory as follows:

```
cloth/
├── 1  INPUT/                           <-- PLACE TARGET GARMENT INPUT PHOTOS HERE
│   ├── GARMENT_1/
│   │   ├── front.jpg
│   │   └── detail.jpg
│   └── GARMENT_2/
│       └── photo.jpg
├── 3  MOODBOARD REFERENCE/             <-- PLACE POSE / LIGHTING / STUDIO REFERENCES HERE
│   ├── pose_ref_1.jpg
│   └── background_ref_2.jpg
├── output/                             <-- GENERATED CATALOG ASSETS & QC REPORTS
│   ├── approved/                       <-- Auto-approved high-fidelity catalog images
│   └── batch_execution_summary.json
├── vertex-cred.json                    <-- PLACE YOUR VERTEX AI SERVICE ACCOUNT CREDS HERE
├── config.py                           <-- Pipeline & model settings
├── main.py                             <-- CLI generation entrypoint
├── server.py                           <-- Flask web server for Studio UI
├── static/                             <-- Dashboard Web Interface
│   └── index.html
└── requirements.txt                    <-- Python dependencies
```

---

## 📁 Directory Setup & Instructions

### 1. Target Garments: `1  INPUT/`
Create folders for each garment SKU inside `1  INPUT/` (e.g. `1  INPUT/GARMENT_1/`).
- Place high-resolution flatlays or ghost mannequin product photos of the garment inside.
- The pipeline will treat images in this folder as the **ground truth** for clothing identity, color, weave, and pattern.

### 2. Moodboard References: `3  MOODBOARD REFERENCE/`
Place model poses, body gestures, studio lighting, or background style reference photos directly in `3  MOODBOARD REFERENCE/`.
- **Gemini 3.6 Flash** analyzes these references to plan realistic model poses and camera framings (`full_body_catalog`, `3_4_lifestyle`, `close_up_drape_detail`).

### 3. Generated Catalog Outputs: `output/`
- All synthesized images, quality inspection reports, and auto-approval results are saved in `output/`.
- Approved images are organized by SKU in `output/approved/<SKU_NAME>/`.

### 4. Credentials: `vertex-cred.json`
Place your Google Cloud Vertex AI service account JSON key file at the root directory (`vertex-cred.json`).

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch Studio Web UI Dashboard
```bash
python server.py
```
Open **`http://localhost:5000`** in your web browser to manage garment SKUs, select moodboards, and trigger catalog generation runs.

### 3. Run Production 4K Batch (Gemini 3.0 Pro Image)
```bash
python run_pro_batch_production.py
```

### 4. Run Fast 4K Batch (Gemini 3.1 Flash Image)
```bash
python run_vtransfer_batch.py
```

---

## 🛡️ Identity & Quality Control Guardrails

Ragento Visual Studio implements an automated Quality Control & Patch Inspection System:
- **Autonomous Micro-Patch Extraction (`SemanticPatchExtractor`)**: Dynamically extracts high-zoom regions (trouser cutwork lace, embroidered bibs, tassels) with uncompressed `MEDIA_RESOLUTION_ULTRA_HIGH`.
- **Master Canvas Template Sequencing**: Uses the assigned Moodboard Reference as Image Part 1 to anchor camera depth, natural scene scale, and lighting while treating 2–4 product shots strictly as invariant apparel swatches.
- **Visual Critic Reflection Loop (`VisualCritic`)**: Audits generated 4K masters against ground-truth patches and triggers targeted single-pass refinement if pattern deviations occur.

For in-depth architectural details and production batch results across 56 Native 4K masters, see **[docs/10_production_vtransfer_pipeline_4k.md](docs/10_production_vtransfer_pipeline_4k.md)**.
