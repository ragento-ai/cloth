# 06. Installation, Authentication & Deployment

This guide covers setting up, authenticating, running, and operating **Ragento Visual Studio** in local development or production server environments.

---

## 📋 System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended) or macOS / Windows (WSL2).
- **Python**: Python 3.10+
- **Google Cloud Account**: Access to **Vertex AI** with `gemini-3-pro-image` and `gemini-3.6-flash` enabled.

---

## 🔑 Authentication Options

Ragento Visual Studio supports three flexible authentication methods configured via [`config.py`](file:///home/amrit-lal-singh/Experimentation/cloth/config.py) / `.env`:

### Option A: Service Account Key File (Recommended)
Place your Google Cloud Vertex AI service account JSON key file at the project root as `vertex-cred.json`.

```env
VERTEX_PROJECT_ID=silicon-cocoa-476407-n3
VERTEX_LOCATION=global
VERTEX_CREDENTIALS_PATH=vertex-cred.json
```

### Option B: Base64 Encoded Environment Variable
For cloud deployments (Heroku, Render, AWS Lambda, Docker) where mounting credential files is restricted:
1. Encode your JSON service account key: `base64 -w 0 vertex-cred.json`
2. Set the `VERTEX_CREDENTIALS_BASE64` environment variable in `.env`.

```env
VERTEX_CREDENTIALS_BASE64=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50Ii...
```

### Option C: Gemini API Key Fallback
Alternatively, specify `GEMINI_API_KEY` for standard Gemini Developer API authentication.

```env
GEMINI_API_KEY=AIzaSy...
```

---

## ⚡ Quick Start: One-Command Bootstrap ([`setup.sh`](file:///home/amrit-lal-singh/Experimentation/cloth/setup.sh))

The repository includes an automated setup script that creates the virtual environment, installs dependencies, verifies credential availability, creates target folders, and launches the server:

```bash
chmod +x setup.sh
./setup.sh
```

---

## 🛠️ Manual Installation & Execution

### 1. Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Verify Project Directory Structure
```
cloth/
├── 1  INPUT/                       <-- Place input SKU photos here (e.g. 1 INPUT/GARMENT_1/)
├── 3  MOODBOARD REFERENCE/         <-- Place pose/lighting reference photos here
├── output/                         <-- Generated catalog assets & QC reports will be saved here
├── docs/                           <-- System documentation directory
├── vertex-cred.json                <-- Google Cloud service account key
├── server.py                       <-- Flask server entrypoint
└── main.py                         <-- CLI entrypoint
```

---

## 🚀 Running the Application

### Mode A: Launch Web Studio UI Dashboard
```bash
python server.py
```
- Open browser at **`http://localhost:5000`** (or server IP on port `5000`).
- Access Garment Division, Moodboard Gallery, Controls Workbench, and Admin Analytics.

### Mode B: CLI Batch Execution
To trigger catalog generation directly from the command line:

```bash
# Run multi-pose catalog generation for SKUs in 1 INPUT/ (3 shots per SKU)
python main.py --num-shots 3

# Run for a specific SKU with custom output directory
python main.py --sku GARMENT_1 --num-shots 3 --output-dir ./output/custom_run
```

### Mode C: Regenerate Full 15 Client Showcase Cases in Native 4K
```bash
python batch_regenerate_all_native_4k.py
```
This regenerates all 15 showcase examples directly in Native 4K into `example_generations/`.

---

## 🛡️ Production Deployment Recommendations

1. **Gunicorn / WSGI Application Server**:
   For production deployments, run Flask using Gunicorn with multiple worker processes:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 server:app
   ```

2. **Reverse Proxy (Nginx / Cloudflare)**:
   Place Nginx in front of Gunicorn to handle HTTPS termination, static asset caching, and request rate-limiting.
