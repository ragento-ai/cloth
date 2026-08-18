# 01. System Architecture & Core Pipeline

Ragento Visual Studio addresses a primary challenge in D2C fashion e-commerce: **maintaining 100% fabric pattern, weave, and garment silhouette fidelity while dynamically swapping models, poses, and backgrounds based on high-converting moodboard reference photos.**

---

## 🏗️ High-Level System Architecture

The platform uses a decoupled, dual-model architecture to split reasoning and high-resolution visual synthesis:

```
                               ┌───────────────────────────┐
                               │   Input Garment Photos    │
                               │  (1 INPUT/<SKU_NAME>/*)   │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   Moodboard References    │
                               │ (3 MOODBOARD REFERENCE/*) │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ PASS 1: ORCHESTRATION & SHOT PLANNING (Gemini 3.6 Flash)                              │
 │  - Analyzes fabric texture anchor & garment composition                                │
 │  - Plans N distinct catalog shots (framing, pose pairing, camera angle)                │
 │  - Applies Selective Transfer Controls & Creative Directives                           │
 │  - Emits Structured JSONPromptPayload                                                  │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ PASS 2: MULTI-REFERENCE GENERATION ENGINE (Gemini 3 Pro Image on Vertex AI)           │
 │  - Role Disambiguation: Garment Shots = Garment Truth, Moodboards = Pose/Env Truth     │
 │  - Renders ultra-high-definition catalog master in Native 4K                           │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ PASS 3: AUTOMATED VISUAL QC INSPECTOR (Gemini 3.6 Flash)                               │
 │  - Layer 1: Binary Identity & Garment Category Sanity Gate                             │
 │  - Layer 2: Granular Multi-Metric Inspection (Pattern, Color, Drape, Anatomy)          │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
                       ▼                                           ▼
             [ PASS: AUTO-APPROVED ]                    [ FAIL: HUMAN REVIEW ]
          (output/approved/<SKU_NAME>/)               (output/human_review/<SKU_NAME>/)
```

---

## ⚙️ Core Pipeline Phases

### Phase 1: Pass 1 Prompt Orchestration
- **Module**: [`src/orchestrator.py`](file:///home/amrit-lal-singh/Experimentation/cloth/src/orchestrator.py)
- **Model**: **Gemini 3.6 Flash** (`gemini-3.6-flash`)
- **Key Functions**:
  1. **Fabric Anchor Selection**: Automatically detects high-resolution close-ups (`detail`, `fabric`, `weave`, `pattern`) to serve as the visual anchor.
  2. **Multi-Shot Planning**: Scans available moodboard reference photos and formulates shot plans containing distinct framings (e.g. `full_body_catalog`, `3_4_lifestyle`, `close_up_drape_detail`).
  3. **Visual Analysis Query**: Queries Gemini 3.6 Flash to extract garment type, ensemble pieces, base fabric color palette, and pattern/weave details into visual rules.
  4. **Structured JSON Serialization**: Constructs a `JSONPromptPayload` matching schema in [`models.py`](file:///home/amrit-lal-singh/Experimentation/cloth/models.py).

### Phase 2: Role-Disambiguated Generation Engine
- **Module**: [`src/generator.py`](file:///home/amrit-lal-singh/Experimentation/cloth/src/generator.py)
- **Model**: **Gemini 3 Pro Image** (`gemini-3-pro-image`) on Vertex AI
- **Role Tagging Protocol**:
  To prevent "clothing bleed" (where the model accidentally draws clothes worn in the moodboard image), inputs are sent with explicit role tags:
  - `=== TARGET GARMENT PRODUCT SHOTS (SOURCE OF TRUTH FOR CLOTHING) ===`: Strictly controls garment category, texture, weave, motifs, and colors.
  - `=== MOODBOARD REFERENCE SHOTS (SOURCE OF TRUTH FOR MODEL POSE & STUDIO ENVIRONMENT ONLY - IGNORE MOODBOARD CLOTHING!) ===`: Strictly controls pose, body gestures, lighting, and background.

### Phase 3: Pass 2 Automated Visual Quality Control
- **Module**: [`src/inspector.py`](file:///home/amrit-lal-singh/Experimentation/cloth/src/inspector.py)
- **Model**: **Gemini 3.6 Flash** (`gemini-3.6-flash`) in JSON Schema Mode
- **Function**: Performs 2-layer automated evaluation against original product shots to determine whether the image passes quality threshold or requires human review.

---

## 📊 Summary of Core Data Models ([models.py](file:///home/amrit-lal-singh/Experimentation/cloth/models.py))

- **`TransferControls`**: User selections for selective feature transfer (`model`, `pose`, `background`, `resolution`, `custom_override`).
- **`ShotPlan`**: Framing, pose source, lighting source, camera angle, and rationale for a single shot.
- **`JSONPromptPayload`**: Complete structured JSON prompt wrapping garment identity, composition spec, and aesthetic rules.
- **`VisualQCReport`**: Structured quality control evaluation with binary sanity flag, granular scores, and detected defects list.
