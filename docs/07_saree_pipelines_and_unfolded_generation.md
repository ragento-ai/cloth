# Ragento Visual Studio - Saree Generation Problem Space & Multi-Step Pipelines (v2 vs v3)

This document provides an in-depth technical breakdown of the **Saree Generation Challenge**, the architectural failure modes encountered with early pipelines, and the engineering design of the **Cumulative Multi-Reference Saree Pipeline (v3)**.

---

## 1. The Core Saree Problem Space

Generating photorealistic, high-fidelity e-commerce catalog photography for Indian Ethnic Saris presents unique AI synthesis challenges that do not exist in Western cut-and-sewn apparel (shirts, dresses, jackets):

1. **Continuous 5.5m–6m Unstitched Textile**:
   - A saree is a single continuous length of fabric consisting of three distinct functional zones:
     - **The Running Body**: Consistent ground weave, base color, and repetitive micro-motifs (*butis*).
     - **Horizontal Running Borders (*Zari* / Embroidery)**: Continuous top and bottom bands that must follow cloth curvature seamlessly without breaking or changing thickness.
     - **The Pallu / Anchal**: High-density decorative end piece featuring ornate motifs, tassels, and intricate border transitions.
2. **Complex 3D Dynamic Draping (Nivi Style)**:
   - In traditional draping, the fabric is folded into 6–8 crisp vertical waist pleats, wrapped around the hips, and then cast diagonally across the torso over the left shoulder.
   - A single-shot diffusion model attempting to simultaneously solve **fabric fidelity**, **complex cloth physics**, **pleat geometry**, and **model pose/lighting fusion** suffers from severe hallucination, motif drift, and border warping.
3. **Macro vs. Micro Feature Preservation**:
   - The model must preserve both the micro-weave (silk texture, gold zari sheen) and macro-composition (where the pallu begins and ends relative to the borders).

---

## 2. Evolution of Saree Pipelines

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           PIPELINE EVOLUTION                           │
  └────────────────────────────────────────────────────────────────────────┘

  [ v1 Direct Fusion ]
  Raw Photos + Moodboard ────────► Single-Shot Prompt ────► DRIFT & HALLUCINATION
                                                             (Warped borders, fake motifs)

  [ v2 3-Step Isolated Swatches ]
  Raw Photos ──► Step 1: Isolated Swatches ──► Step 2: 3D Drape ──► Step 3: Model Fusion
                               ▲                                      │
                               └────── Fragmented tiles break ────────┘
                                       macro-continuity & borders

  [ v3 Cumulative Multi-Reference Pipeline ] (Current State of the Art)
  Raw Photos ──► Step 1: Unified Continuous Flat-Lay Canvas
                       │
                       ├────────────────────────────┐
                       ▼                            │
  Raw Photos ──► Step 2: 3D Drape Blueprint         │ (Cumulative Context)
                       │                            │
                       ├────────────────────────────┤
                       ▼                            ▼
  Raw Photos ──► Step 3: Model & Moodboard Fusion ◄─┘
                       │
                       ▼
                 Pass 4: Visual QC Gate (Automated Inspector)
```

---

## 3. Failure Analysis: Why v1 and v2 Failed

### The v1 Direct Single-Shot Failure
* **Mechanism**: Feeding raw flat/folded product photos directly alongside a moodboard model reference.
* **Failure Modes**:
  - The model treated the folded garment photos as abstract color inspiration rather than strict spatial boundaries.
  - Borders disappeared in waist pleats or appeared on random sections of the torso.
  - Pallu motifs were replaced with generic AI floral patterns.

### The v2 Swatch-Based Failure ([`pipeline_v2_3step_saree.py`](file:///home/amrit-lal-singh/Experimentation/cloth/pipeline_v2_3step_saree.py))
* **Mechanism**: Step 1 cropped and unwrapped the saree into isolated swatch panels (e.g., body swatch box + border swatch box + pallu swatch box in a collage).
* **Failure Modes**:
  - **Loss of Global Continuity**: Because the swatches were cropped into disjoint rectangles, downstream Step 2 had no concept of how the top and bottom borders physically connected to the running body over a 6-meter span.
  - **Scale Distortion**: The model enlarged small border swatches to fit the whole canvas, causing giant borders or broken pleat alignments.
  - **Step-to-Step Error Compounding**: As each step only received the output of the previous step, weave texture and authentic color fidelity degraded exponentially by Step 3.

---

## 4. The v3 Cumulative Multi-Reference Architecture

Implemented in [`run_saree_unfolded_v3_cumulative.py`](file:///home/amrit-lal-singh/Experimentation/cloth/run_saree_unfolded_v3_cumulative.py), the v3 pipeline introduces two key paradigm shifts:
1. **Unified Continuous 2D Flat-Lay Canvas** in Step 1.
2. **Cumulative Ground-Truth Context Passing** across all steps (every step has access to all previous blueprints *plus* the original raw photos).

```
   ┌────────────────────────────────────────────────────────────────────────┐
   │                  CUMULATIVE CONTEXT PASSING GRAPH                      │
   └────────────────────────────────────────────────────────────────────────┘

   [Raw Photos] ───────────────┬─────────────────────────┬────────────────────────┐
                               │                         │                        │
                               ▼                         ▼                        ▼
                       ┌───────────────┐         ┌───────────────┐        ┌───────────────┐
                       │    STEP 1     │         │    STEP 2     │        │    STEP 3     │
                       │ Unified 2D    │────────►│ 3D CAD Drape  │───────►│ Commercial    │
                       │ Flat-Lay      │         │ Blueprint     │        │ Model Fusion  │
                       └───────────────┘         └───────────────┘        └───────────────┘
                                                         │                        ▲
                                                         └────────────────────────┤
   [Moodboard Ref] ───────────────────────────────────────────────────────────────┘
```

### Step 1: Unified Continuous 2D Flat-Lay Canvas
* **Purpose**: De-fold and orthographically flatten the entire 6-meter saree into a single, continuous horizontal layout on a clean matte white background.
* **Requirements**:
  - Full horizontal layout with unbroken top/bottom running borders.
  - Distinct pallu array at one end transitioning into the running body.
  - Zero folds, zero wrinkles, zero perspective distortion.

### Step 2: 3D CAD Drape Blueprint (Ghost Mannequin)
* **Inputs**:
  1. `Reference 1`: Step 1 Unified Continuous Flat-Lay (for 2D geometry and border flow).
  2. `References 2+`: Original Raw Product Photos (for true weave texture, color tones, and zari sheen).
* **Directives**:
  - Drape the garment onto an invisible ghost mannequin in classic Nivi style (6–8 center waist pleats, smooth hip wrap, diagonal pallu over left shoulder).
  - Flat, diffuse CAD studio lighting to ensure maximum visibility of all folds and motifs without shadow occlusion.
  - Zero human body parts or faces.

### Step 3: Human Model & Environment Fusion
* **Inputs (Full Cumulative Context)**:
  1. `Image 1`: Step 2 3D Draped Blueprint (source for drape silhouette, pleat positions, pallu fall).
  2. `Image 2`: Step 1 Unified Flat-Lay Canvas (source for 2D border continuity).
  3. `Images 3-4`: Original Raw Product Photos (absolute ground truth for color and weave).
  4. `Image 5`: Moodboard Reference Photo (source *only* for model pose, expression, camera angle, and lighting; clothing ignored).
* **Directives**:
  - Replicate model pose and atmospheric lighting from the moodboard.
  - Render an aesthetically complementary blouse matching the saree palette.
  - Maintain 100% garment identity across all folds.

### Pass 4: Automated Visual QC Inspector
* Evaluates the Step 3 output against original product photos across 5 key dimensions:
  - Base Color Fidelity ($\ge 85\%$)
  - Pattern & Motif Retention ($\ge 85\%$)
  - Anatomical & Drape Realism ($\ge 90\%$)
  - Transformation Verification
  - Final Quality Gate Pass / Fail decision with composite score.

---

## 5. Execution Reference & Output Assets

### Running the Cumulative Saree Pipeline

```bash
# Run Saree 1 with default moodboard
python run_saree_unfolded_v3_cumulative.py --saree 1 --moodboard 1000221736.jpg

# Run Saree 2
python run_saree_unfolded_v3_cumulative.py --saree 2 --moodboard 1000221736.jpg

# Run Saree 3
python run_saree_unfolded_v3_cumulative.py --saree 3 --moodboard 1000221736.jpg
```

### Output Directory Structure
Outputs are segregated cleanly per garment SKU and pipeline version under [`output_sari/`](file:///home/amrit-lal-singh/Experimentation/cloth/output_sari):

```
output_sari/
├── 1/
│   ├── v2/                                   # Legacy Swatch-based generation
│   │   ├── step1_flat_swatch_1.png
│   │   ├── step2_3d_draped_1.png
│   │   ├── step3_final_on_model_1.png
│   │   └── qc_report_1.json
│   └── v3/                                   # Cumulative Multi-Reference generation
│       ├── step1_unified_flatlay_1.png       # Continuous 2D flat-lay canvas
│       ├── step2_3d_draped_1.png             # 3D Ghost mannequin drape blueprint
│       ├── step3_final_on_model_1.png        # Commercial model catalog shot
│       └── qc_report_1.json                  # Automated QC audit report
└── 2/
    └── v3/
        ├── step1_unified_flatlay_2.png
        ├── step2_3d_draped_2.png
        ├── step3_final_on_model_2.png
        └── qc_report_2.json
```

---

## 6. Saree Problem Troubleshooting & Next Steps

| Current Issue | Root Cause | Recommended Action |
| :--- | :--- | :--- |
| **Border Discontinuity in Draping** | Step 1 flat-lay was truncated or cropped | Verify Step 1 generated a complete horizontal continuous band from end to end before running Step 2. |
| **Color Temperature Drift in Step 3** | Moodboard reference lighting overrode fabric color | Ensure cumulative prompt explicitly anchors fabric color to Original Input Photos (`Images 3 & 4`), keeping the moodboard strictly for lighting ambiance. |
| **Blouse Texture Mismatch** | Unspecified blouse instructions | Add explicit prompt directives defining whether the blouse should use running body fabric or border contrast fabric. |
| **Pallu Back-View Catalogs** | Front-only drape blueprint | Generate secondary Step 2 drape Blueprint capturing the 180° back view of the draped pallu. |
