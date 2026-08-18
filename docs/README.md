# Ragento Visual Studio - Documentation Hub

Welcome to the comprehensive technical documentation for **Ragento Visual Studio**, an enterprise-grade AI Visual Generation Platform for D2C Fashion E-Commerce (custom-built for Mirchi Fashion).

Ragento Visual Studio leverages a dual-engine architecture combining **Gemini 3.6 Flash** (for visual analysis, moodboard shot planning, and automated quality control) and **Gemini 3 Pro Image** (on Google Cloud Vertex AI for native 4K multi-reference image synthesis).

---

## 📚 Documentation Index

| Module | Title | Description |
| :--- | :--- | :--- |
| **[01_system_architecture_and_pipeline.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/01_system_architecture_and_pipeline.md)** | **System Architecture & Core Pipeline** | Dual-model pipeline design, Pass 1 Orchestration, Pass 2 Generation & Inspection flow. |
| **[02_selective_transfer_controls_and_directives.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/02_selective_transfer_controls_and_directives.md)** | **Selective Transfer & Creative Directives** | 3-State Transfer Controls (Model, Pose, Background), Resolution Engine, and High-Priority Overrides. |
| **[03_quality_control_and_guardrails.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/03_quality_control_and_guardrails.md)** | **2-Layer Quality Control & Guardrails** | Layer 1 Binary Sanity Gate, Layer 2 Multi-Metric Inspection, and Auto-Approval vs Human Review Routing. |
| **[04_web_studio_dashboard_and_api.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/04_web_studio_dashboard_and_api.md)** | **Studio Web UI & REST API Specification** | Dashboard user interface, Admin Analytics, Security Passcode Overlay, and REST API reference. |
| **[05_client_showcases_and_4k_generations.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/05_client_showcases_and_4k_generations.md)** | **15 Client Showcase Cases & Native 4K Engine** | Deep-dive into the 15 Mirchi Fashion showcase examples, batch regeneration, and 4K output pipeline. |
| **[06_installation_and_deployment.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/06_installation_and_deployment.md)** | **Setup, Authentication & Operations** | One-command setup (`setup.sh`), Vertex AI service account / Base64 auth, CLI & Web execution modes. |
| **[07_saree_pipelines_and_unfolded_generation.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/07_saree_pipelines_and_unfolded_generation.md)** | **Saree Pipelines & Cumulative Multi-Reference Architecture** | 6-meter continuous textile problem space, v1/v2 swatch breakdown failure analysis, and v3 cumulative flat-lay & drape pipelines. |
| **[08_critique_mode_and_pipeline_evolution.md](file:///home/amrit-lal-singh/Experimentation/cloth/docs/08_critique_mode_and_pipeline_evolution.md)** | **Critique Mode & Saree Pipeline Evolution (Best Method)** | Complete evolution from v1 to v5, autonomous reflection loop (Gemini 3.1 Flash Generator + Gemini 3.6 Flash Critic), and AI agent execution guide. |

---

## 🚀 Key Features Overview

1. **Exact Pattern & Texture Preservation**: Prevents fabric drift, pattern warping, or weave distortion by isolating target garment product shots as the absolute ground truth.
2. **Moodboard-Driven Aesthetics**: Dynamically extracts poses, camera framings, lighting conditions, and environment backdrops from high-converting reference photography.
3. **Selective Transfer Control Matrix**: Granular toggles (`Input`, `Model Decides / Auto`, `Moodboard`) allowing art directors to independently control Model Facial Identity, Body Pose, and Background Environment.
4. **Special Creative Directives**: High-priority text overrides for custom lighting (e.g. golden hour sunbeams), specific accessories (e.g. gold temple jewelry), or garment drape styling.
5. **2-Layer Visual Quality Control (QC)**:
   - **Layer 1 (Binary Sanity Gate)**: Verifies product category retention (Saree / Kurta / Ensemble piece).
   - **Layer 2 (Multi-Metric Inspection)**: Evaluates base color fidelity, pattern match confidence, anatomical correctness, drape realism, and transformation verification.
6. **Native 4K Ultra-High-Definition Rendering**: Synthesizes studio-grade 4K images (`3072x4096` / `4096x4096`) directly from Gemini 3 Pro on Google Cloud Vertex AI.
7. **Enterprise Studio Dashboard**: Full web interface featuring Garment SKU Management, Moodboard Gallery, Interactive Generation Workbench, History Gallery with Human-Readable Metadata, and Admin Analytics.
