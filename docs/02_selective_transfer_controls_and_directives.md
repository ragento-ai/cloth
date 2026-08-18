# 02. Selective Transfer Controls & Creative Directives

Ragento Visual Studio provides high-precision art direction controls that empower fashion teams to customize generative outputs without writing complex manual prompts.

---

## 🎛️ 3-State Transfer Control Matrix

Each attribute—**Model Identity**, **Body Pose & Gesture**, and **Background / Environment**—can be independently assigned to one of three transfer modes:

| Transfer Mode | Button Label | Behavior |
| :--- | :--- | :--- |
| **`Input`** | `Input` | Anchors feature directly to the **Input Product Photo**. Preserves original model's face, original product pose, or indoor studio background. |
| **`Auto`** | `Model Decides` | Allows Gemini 3.6 Flash and Gemini 3 Pro to intelligently determine optimal model identity, pose, or background suited for the garment. |
| **`Moodboard`** | `Moodboard` | Clones feature directly from the selected **Moodboard Reference Image** (facial features, pose/gesture, or outdoor architecture/lighting). |

---

## 🛠️ Feature Toggle Breakdown

### 1. Model Identity (`model`)
- **`Input`**: Retains facial structure, skin tone, hairstyle, and identity of the model present in the original product shot.
- **`Model Decides`**: Synthesizes a fresh, diverse Indian fashion model matching commercial e-commerce aesthetic.
- **`Moodboard`**: Transfers model facial features and hair styling from the moodboard reference image.

### 2. Body Pose & Gesture (`pose`)
- **`Input`**: Keeps the original static catalog pose of the garment input photo.
- **`Model Decides`**: Generates a natural dynamic pose tailored to the garment framing.
- **`Moodboard`**: Mirrors the body pose, hand placement, and gesture from the moodboard reference photo.

### 3. Background & Environment (`background`)
- **`Input`**: Replicates the clean indoor studio backdrop from the original product shot.
- **`Model Decides`**: Generates a clean minimalist studio backdrop optimized for catalog presentation.
- **`Moodboard`**: Clones the full environment (e.g. heritage palace courtyard, water garden, stone archways) and lighting atmosphere from the moodboard reference.

---

## 🎨 Special Creative Directives (`custom_override`)

The **Special Creative Directives** text input allows art directors to pass high-priority text directives that take precedence over standard toggles.

### Common Creative Directives & Use Cases

1. **Specific Garment Silhouette Directives**:
   > *"Must be an authentic Indian Saree with pleats, draped pallu, and high neck blouse. Strictly no dupatta or suit."*
   - **Effect**: Ensures strict adherence to traditional saree draping when generating complex Indian ethnic wear.

2. **Custom Lighting & Atmosphere**:
   > *"Soft afternoon golden hour sunlight with warm amber reflections and gentle bokeh"*
   - **Effect**: Injects golden hour sunbeams and warm lighting across outdoor courtyard environments.

3. **Styling & Accessories Directives**:
   > *"Wearing traditional gold bangles, jhumkas, and temple jewelry"*
   - **Effect**: Enhances festive or bridal garments with authentic traditional gold jewelry.

4. **Background Architectural Directives**:
   > *"Rajasthani heritage palace courtyard with intricate carved stone arches and soft sunlight"*
   - **Effect**: Guides environment generation toward specific heritage motifs.

---

## 📐 Resolution Selector (`resolution`)

Art directors can choose the target rendering resolution:
- **`1024x1024`**: Fast draft rendering.
- **`2048x2048`**: Standard catalog resolution.
- **`4096x4096`**: Native 4K ultra-high-definition resolution for high-res catalog printing and billboard-scale digital displays.
