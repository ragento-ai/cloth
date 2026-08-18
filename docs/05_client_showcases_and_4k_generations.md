# 05. Client Showcase Suite & Native 4K Engine

To demonstrate the full versatility and quality of Ragento Visual Studio to Mirchi Fashion and potential enterprise clients, a comprehensive suite of **15 Client Showcase Examples** was engineered and rendered in Native 4K Ultra-High Definition.

---

## 🌟 The 15 Client Showcase Cases ([`example_generations/`](file:///home/amrit-lal-singh/Experimentation/cloth/example_generations))

Each showcase case demonstrates a specific combination of Garment SKU, Moodboard Reference, Selective Transfer Controls, Creative Directives, and QC Guardrails:

| Ex # | Case ID | SKU & Garment Type | Moodboard Ref | Control Settings | Highlight / Creative Directive |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **01** | `example_01_garment1_full_moodboard_transfer` | **Garment 1** (Lilac Saree) | `K10048G.jpg` | Model: `Moodboard`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Full aesthetic, model face, pose, and rustic arch courtyard backdrop. |
| **02** | `example_02_garment1_input_model_moodboard_pose` | **Garment 1** (Lilac Saree) | `K10043I.jpg` | Model: `Input`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Anchors original Saree model facial identity; pose & garden water environment transferred. Directives: *"Must be an authentic Indian Saree with pleats..."* |
| **03** | `example_03_garment1_moodboard_bg_golden_hour` | **Garment 1** (Lilac Saree) | `K10048M1.jpg` | Model: `Auto`<br>Pose: `Auto`<br>BG: `Moodboard` | Creative Directive: *"Soft afternoon golden hour sunlight with warm amber reflections and gentle bokeh"*. |
| **04** | `example_04_garment2_full_moodboard_garden` | **Garment 2** (Blue Tie-Dye Saree) | `K10043G.jpg` | Model: `Moodboard`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Full environmental and mood transfer from tropical garden reference onto tie-dye saree. |
| **05** | `example_05_garment2_input_model_moodboard_bg` | **Garment 2** (Blue Tie-Dye Saree) | `K10044J.jpg` | Model: `Input`<br>Pose: `Auto`<br>BG: `Moodboard` | Preserved original tie-dye saree model's facial features while placing her in lush outdoor backdrop. |
| **06** | `example_06_garment2_moodboard_model_studio_bg` | **Garment 2** (Blue Tie-Dye Saree) | `K10046G.jpg` | Model: `Moodboard`<br>Pose: `Auto`<br>BG: `Input` | Transferred model features from reference while maintaining crisp indoor studio backdrop + gold temple jewelry directive. |
| **07** | `example_07_garment3_full_moodboard_heritage` | **Garment 3** (Navy Kurta Set) | `K10048I.jpg` | Model: `Moodboard`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Complete transfer of model identity, pose, and heritage palace courtyard backdrop onto Kurta Set. |
| **08** | `example_08_garment3_input_model_moodboard_courtyard` | **Garment 3** (Navy Kurta Set) | `K10049R.jpg` | Model: `Input`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Preserved input Kurta model face; outdoor arched palace hallway backdrop. |
| **09** | `example_09_garment3_moodboard_pose_studio_shadows` | **Garment 3** (Navy Kurta Set) | `K10048M2.jpg` | Model: `Auto`<br>Pose: `Moodboard`<br>BG: `Input` | Dynamic seated pose from moodboard with studio window shadow lighting directive. |
| **10** | `example_10_garment4_full_moodboard_carved_relief` | **Garment 4** (Maroon Zari Saree) | `K10048N.jpg` | Model: `Moodboard`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Carved temple stone relief backdrop with rich sari zari motif preservation. |
| **11** | `example_11_garment4_input_garment_lush_garden` | **Garment 4** (Maroon Zari Saree) | `K10043G.jpg` | Model: `Input`<br>Pose: `Auto`<br>BG: `Moodboard` | Input Saree model face anchored in tropical garden environment. |
| **12** | `example_12_garment4_moodboard_model_festive_urlis` | **Garment 4** (Maroon Zari Saree) | `K10049Q.jpg` | Model: `Moodboard`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Festive marigold flowers and brass urlis creative directive for Diwali commercial campaign. |
| **13** | `example_13_garment1_input_pose_moodboard_lighting` | **Garment 1** (Lilac Saree) | `K10044J.jpg` | Model: `Input`<br>Pose: `Input`<br>BG: `Moodboard` | Original pose retained; backdrop swapped to morning garden terrace with soft fog directive. |
| **14** | `example_14_garment3_moodboard_model_temple_courtyard` | **Garment 3** (Navy Kurta Set) | `K10048O.jpg` | Model: `Moodboard`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Rajasthani temple courtyard architecture with brass lanterns directive. |
| **15** | `example_15_garment2_full_moodboard_arch_shadows` | **Garment 2** (Blue Tie-Dye Saree) | `K10048P.jpg` | Model: `Moodboard`<br>Pose: `Moodboard`<br>BG: `Moodboard` | Heritage sandstone corridor archways with geometric shadows directive. |

---

## 💎 Native 4K Rendering Engine

The generation engine ([`src/generator.py`](file:///home/amrit-lal-singh/Experimentation/cloth/src/generator.py)) requests native 4K output directly from Vertex AI Gemini 3 Pro Image:

```python
image_config = types.ImageConfig(
    image_size="4K",
    aspect_ratio="3:4"
)
```

- **Output Dimensions**: Up to `3072x4096` pixels.
- **Visual Benefits**:
  - Razor-sharp thread weave, embroidery detail, and lace texture.
  - Zero loss of micro-print patterns across saree borders and pallus.
  - High anatomical resolution for hands, facial features, and hair follicles.

---

## 📜 Automation & Batch Regeneration Scripts

The repository contains scripts for batch processing and generating showcase packages:

1. **[`batch_regenerate_all_native_4k.py`](file:///home/amrit-lal-singh/Experimentation/cloth/batch_regenerate_all_native_4k.py)**:
   - Script that executes all 15 client showcase cases sequentially directly through Gemini 3 Pro Image in Native 4K.
   - Saves final images, metadata JSON files, prompt logs, and QC reports into `example_generations/`.

2. **[`create_showcase_package.py`](file:///home/amrit-lal-singh/Experimentation/cloth/create_showcase_package.py)**:
   - Packages all 15 showcase examples along with a structured client delivery summary (`example_generations.zip`).

3. **[`run_4k_enhancement_showcase.py`](file:///home/amrit-lal-singh/Experimentation/cloth/run_4k_enhancement_showcase.py)**:
   - Demonstrates resolution comparisons and 4K quality enhancements.
