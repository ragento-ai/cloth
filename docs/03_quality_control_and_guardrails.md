# 03. 2-Layer Quality Control & Guardrails

To prevent hallucinated garments, pattern drift, color shifts, or anatomical artifacts from entering storefront catalogs, Ragento Visual Studio features an automated **2-Layer Visual Quality Control (QC)** inspection engine powered by **Gemini 3.6 Flash**.

---

## 🛡️ Decoupled 2-Layer Evaluation Protocol

```
                        ┌──────────────────────────────┐
                        │    AI-Generated Output Asset │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ LAYER 1: BINARY IDENTITY & PIECE SANITY CHECK                           │
 │ (is_same_garment_or_valid_piece)                                        │
 │  - Is output the exact same SKU or a valid ensemble piece/styling?      │
 └─────────────────────────────────────┬────────────────────────────────────┘
                                       │
                       ┌───────────────┴───────────────┐
                       │                               │
                       ▼ (FALSE)                       ▼ (TRUE)
            [ REJECT & FLAG ]              ┌──────────────────────────────┐
         Defect: LAYER_1_MISMATCH          │ LAYER 2: GRANULAR METRICS    │
                                           │  - Category Match >= 0.80    │
                                           │  - Color Fidelity >= 0.80    │
                                           │  - Pattern Match >= 0.80     │
                                           │  - Anatomical Accuracy      │
                                           │  - Drape Realism             │
                                           │  - Transformation Verification│
                                           └──────────────┬───────────────┘
                                                          │
                                          ┌───────────────┴───────────────┐
                                          │                               │
                                          ▼ (ALL METRICS MET)             ▼ (ANY METRIC FAILS)
                                    [ AUTO-APPROVE ]            [ FLAG FOR HUMAN REVIEW ]
```

---

## 🔍 Detailed Metric Specifications

### Layer 1: Binary Identity Sanity Gate
- **Field**: `is_same_garment_or_valid_piece` (`bool`)
- **Evaluates**: Disregarding model pose and background, does the generated image show the **exact same garment SKU**, OR a valid individual piece/styling of the SKU (e.g. full saree set vs unstitched blouse piece)?
- **Hard Rule**: If `is_same_garment_or_valid_piece` is `False`, the asset **immediately fails** the quality gate and is flagged with `LAYER_1_IDENTITY_MISMATCH`.

### Layer 2: Granular Feature Quality Checks (0.0 to 1.0)

| Metric Field | Threshold | Description | Defect Code on Failure |
| :--- | :---: | :--- | :--- |
| **`garment_type_match`** | `>= 0.80` | Verification that generated output matches product category or valid ensemble styling. | `CATEGORY_MISMATCH` |
| **`base_color_fidelity`** | `>= 0.80` | Fidelity of primary & secondary color palette versus original product shots under studio lighting. | `COLOR_PALETTE_MISMATCH` |
| **`pattern_match_confidence`**| `>= 0.80` | Preservation of pattern, weave, print scale, tie-dye motifs, or zari embroidery. | `PATTERN_DEVIATION` |
| **`anatomical_correctness`** | `>= 0.80` | Model anatomy, hands, fingers, limb proportions, and skin texture realism. | `ANATOMICAL_ARTIFACT` |
| **`garment_drape_realism`** | `>= 0.80` | Natural gravity, fabric weight, fold physics, and drape physics. | `DRAPE_UNREALISTIC` |
| **`transformation_verification`**| `>= 0.70` | Verification that model/pose/background transfer actually occurred (prevents zero-change raw copies). | `UNTRANSFORMED_COPY` |

---

## 📁 Automatic Asset Routing

Based on the inspection output from Gemini 3.6 Flash:

- **`AUTO_APPROVED`**:
  - Saved to `output/approved/<SKU_NAME>/<SKU_ID>_shot_<N>_<TIMESTAMP>_final.png`
  - Instantly ready for publishing to storefront catalog or ad channels.
- **`FLAGGED_FOR_HUMAN_REVIEW`**:
  - Saved to `output/human_review/<SKU_NAME>/<SKU_ID>_shot_<N>_<TIMESTAMP>_flagged.png`
  - Detailed reason logged in `qc_report.json` under `human_review_reason` and `detected_defects`.

---

## 📄 Example `qc_report.json` Payload

```json
{
  "is_same_garment_or_valid_piece": true,
  "garment_type_match": 0.95,
  "base_color_fidelity": 0.92,
  "pattern_match_confidence": 0.91,
  "anatomical_correctness": 0.94,
  "garment_drape_realism": 0.90,
  "transformation_verification": 0.88,
  "composite_quality_score": 0.92,
  "pass_quality_gate": true,
  "detected_defects": [],
  "human_review_reason": null
}
```
