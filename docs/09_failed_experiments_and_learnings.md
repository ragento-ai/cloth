# 09. Failed Experiments & Architectural Learnings

This document logs tested architectural approaches, models, and workflows that did **not** yield acceptable commercial fashion results, along with the technical root causes.

---

## ❌ Experiment 1: Two-Stage Hybrid (Google `virtual-try-on-001` + `gemini-3.1-flash-image` 4K Upscale)

### **Concept**
Use Google's dedicated recontextualization model (`virtual-try-on-001`) in Stage 1 to fit the garment onto a target model photo, then pass the resulting try-on image alongside the ground truth product shot and moodboard to `gemini-3.1-flash-image` in Stage 2 to upscale to native 4K.

### **Why It Failed**
1. **Low-Resolution Base Degrades Micro-Motifs**:
   - `virtual-try-on-001` operates on an internal 1-Megapixel (`~1024px`) diffusion grid.
   - Intricate micro-details—such as Schiffli eyelet lace hem perforations, leaf/paisley chikankari embroidery, and fine zari threads—become blurry, smudged, or completely lost in the 1024px try-on output.
2. **Generative Model Inherits Low-Res Artifacts**:
   - When `gemini-3.1-flash-image` was given the `virtual-try-on-001` image as a pose/fit anchor, it attempted to align with the degraded geometry of the low-res image.
   - Instead of synthesizing fresh high-res embroidery from the ground truth product shot, it hallucinated smoothed-over or distorted pant hem lace, missing the leaf motifs and zig-zag perforations entirely.

### **Key Takeaway**
> **Do not use `virtual-try-on-001` for garments with fine micro-embroidery, eyelet lace, or delicate zari work.** 
> Direct native 4K synthesis (`gemini-3.1-flash-image`) conditioned directly on high-res ground truth product shots (`K9301L.jpg`) delivers far superior textile fidelity.
