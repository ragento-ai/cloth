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

### 3. Run via CLI (Optional)
```bash
python main.py --num-shots 3
```

---

## 🛡️ Identity & Quality Control Guardrails

Ragento Visual Studio implements a 2-Layer Quality Control System:
- **Layer 1 (Binary Sanity Gate)**: Checks whether the generated output represents the same garment SKU or a valid piece of the ensemble (e.g., kurta/dupatta/blouse piece).
- **Layer 2 (Multi-Metric Quality Inspection)**: Verifies anatomical correctness, base color fidelity, drape realism, and pattern match confidence before auto-approving assets.
