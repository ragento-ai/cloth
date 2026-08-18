# Ragento Visual Studio - Saree Pipeline Evolution & Critique Mode

## Executive Summary & Best Performing Architecture

Across extensive experimentation on unstitched 5.5m Indian ethnic sarees with intricate continuous borders, sheer weaves, and complex pallu end-caps, **Critique Mode (v5)** powered by **`gemini-3.1-flash-image` (Generator)** and **`gemini-3.6-flash` (Visual Critic)** is the **best performing, most reliable, and highest-fidelity pipeline** in the Ragento architecture.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               CRITIQUE MODE (v5) - THE BEST PERFORMING ARCHITECTURE                    │
└────────────────────────────────────────────────────────────────────────────────────────┘

  [Raw Unfolded Photos] ──┐
  [Moodboard Reference] ──┼──► [Generator: Gemini 3.1 Flash (Native 4K)]
                          │                    │
                          │                    ▼
                          │            [Draft Generation]
                          │                    │
                          │                    ▼
                          └──────────► [Critic: Gemini 3.6 Flash]
                                               │
                           ┌───────────────────┴───────────────────┐
                           ▼                                       ▼
                   [Approved == True]                      [Approved == False]
                           │                                       │
                           ▼                                       ▼
                   [Finalize Asset]                    [Visual Diff Refinement]
                                                                   │
                                                                   ▼
                                                      [Loop to Generator (Max 3)]
```

---

## 1. Evolution & Comparative Analysis of Saree Pipeline Versions

| Version | Architecture | Engine | Hallucination Risk | Speed / Latency | Overall Verdict |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **v1 (Swatches)** | Swatch Cropping &rarr; Direct Draping | Gemini 3 Pro | Very High | ~45s | ❌ Broken pattern continuity; seam boundaries. |
| **v2 (CAD Drape)** | Ghost Mannequin Blueprint &rarr; Model | Gemini 3 Pro | Medium | ~75s | ⚠️ Good geometry, but rigid CAD lighting leaks into model skin. |
| **v3 (Cumulative)** | 2D Flat-Lay &rarr; 3D Drape &rarr; Fusion | Flash / Pro | High (Step 1) | ~110s | ⚠️ High fidelity IF Step 1 succeeds, but Step 1 often forces fake borders. |
| **v4 (Direct 1-Step)** | Unfolded Photos &rarr; Model Fusion | Flash 3.1 4K | Moderate | **~25s** | ⚡ Fast and natural fabric drape, but vulnerable to model priors (e.g. fake borders). |
| **v5 (Critique Mode)** | **Generator &larr;&rarr; Critic Reflection Loop** | **Flash 3.1 + Flash 3.6** | **Near Zero** | **~50–70s** | 🏆 **BEST PERFORMING**: Catches and eliminates all hallucinations autonomously. |

---

## 2. Why Critique Mode (v5) Outperforms All Other Modes

1. **Eliminates Model Priors & Hallucinations**:
   Generative models have an inductive bias assuming all sarees have top/bottom borders. On borderless sarees (e.g. Saree 3), v3 and v4 slapped red Ajrakh borders onto the chest and skirt hem. The Gemini 3.6 Flash Critic immediately flagged this structural hallucination and provided exact refinement instructions to remove it.
2. **Eliminates Micro-Motif Morphing**:
   On delicate organza sarees (e.g. Saree 1), single-pass generation can blend peacock heads and tree foliage into mutated diamond blobs. The Critic enforces authentic booti geometry.
3. **No Fragile Coordinate Cropping**:
   Operates on complete multi-modal visual tokens without brittle bounding-box regressions.
4. **Native 4K Commercial Fidelity**:
   Generates at `3584 × 4800` pixels (~17.2 MP) with zero loss of weave resolution.

---

## 3. Storage & Directory Layout (Local Filesystem)

All input photos and generated assets are stored locally and excluded from Git commits via `.gitignore`:

```
cloth/
├── saree_unfolded/                      # Ground truth unfolded warehouse photos
│   ├── 1/                               # Saree 1: Sage green organza peacock saree
│   │   ├── IMG_20260813_133926.jpg.jpeg
│   │   └── IMG_20260813_133929.jpg.jpeg
│   ├── 2/                               # Saree 2: Pink/yellow geometric zari saree
│   │   ├── IMG_20260813_134235.jpg.jpeg
│   │   └── IMG_20260813_134241.jpg.jpeg
│   └── 3/                               # Saree 3: Monochrome striped with Ajrakh pallu
│       ├── IMG_20260813_134554.jpg.jpeg
│       └── IMG_20260813_134602.jpg.jpeg
├── moodboard_2/                         # Studio aesthetic references
│   └── 1000221736.jpg                   # Terracotta arch studio background reference
└── output_sari/                         # Generated outputs by pipeline version
    ├── <id>/critic_loop/                # [v5 Critique Mode Assets]
    │   ├── iteration_1.png              # Initial draft generated by Gemini 3.1 Flash
    │   ├── critique_1.json              # Gemini 3.6 Flash structured evaluation
    │   ├── iteration_2.png              # Refined draft based on visual diff
    │   ├── critique_2.json              # Second evaluation
    │   └── final_approved_saree_<id>.png # Final Critic-approved 4K catalog image
    ├── <id>/v4/                         # [v4 Direct 1-Step Assets]
    │   ├── final_on_model_v4_<id>.png
    │   └── qc_report_v4_<id>.json
    └── <id>/v3/                         # [v3 Cumulative 3-Step Assets]
        ├── step1_unified_flatlay_<id>.png
        ├── step2_3d_draped_<id>.png
        ├── step3_final_on_model_<id>.png
        └── qc_report_<id>.json
```

---

## 4. Execution Guide for AI Agents & Developers

### Environment Setup
```bash
cd /home/amrit-lal-singh/Experimentation/cloth
source venv/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS="vertex-cred.json"
```

### Running Pipelines

#### 1. Run Critique Mode (Recommended Best Method)
```bash
# Run on Saree 3 with max 3 critique loops
./venv/bin/python run_saree_critic_loop.py --saree 3 --max_iter 3

# Run on Saree 1
./venv/bin/python run_saree_critic_loop.py --saree 1 --max_iter 3

# Run on Saree 2
./venv/bin/python run_saree_critic_loop.py --saree 2 --max_iter 3
```

#### 2. Run Direct 1-Step Pipeline (v4)
```bash
# Run single saree
./venv/bin/python run_saree_v4_direct.py --saree 1

# Run batch for all sarees
./venv/bin/python run_saree_v4_direct.py --saree all
```

#### 3. Run Cumulative 3-Step Pipeline (v3)
```bash
# Run 3-step pipeline (Step 1 Flat-Lay -> Step 2 3D Drape -> Step 3 Model Fusion)
./venv/bin/python run_saree_unfolded_v3_cumulative.py --saree 2
```

#### 4. Run Automated QC Audit on Any Existing Image
```bash
./venv/bin/python test_critic_detection.py
```
