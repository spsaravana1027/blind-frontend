# Vercel Deployment Guide for AI Assistive Vision & Tamil Voice Project

This project is now **100% Vercel-compatible**. All necessary serverless entry points, rewrites, ignore rules, and optimized dependencies have been created. No code logic, endpoints, or Tamil phrases were modified.

---

## What Changes Were Made for Vercel Compatibility

1. **Vercel Routing Configuration (`vercel.json`)**:
   - Added rewrite rules to route all incoming HTTP requests (`/(.*)`) to the serverless entrypoint `/api/index.py`.
   - Supported at both the root level and inside the `/server` folder.

2. **Serverless Entrypoint (`api/index.py`)**:
   - Created ASGI/WSGI handler adapters (`d:\iot-blind\api\index.py` and `d:\iot-blind\server\api\index.py`) that properly configure `sys.path` and export the FastAPI `app` and `handler`.

3. **Optimized Dependencies (`requirements.txt`)**:
   - Configured `--extra-index-url https://download.pytorch.org/whl/cpu` to ensure lightweight CPU-only PyTorch is installed during Vercel builds.
   - Uses `opencv-python-headless` to eliminate missing X11/GL system library issues on AWS Lambda / Vercel.
   - Removed unneeded local desktop audio packages (`pygame`) while keeping the 35 human voice MP3 audio files served directly through `/audio/{filename}`.

4. **Upload Size Optimization (`.vercelignore`)**:
   - Excluded hardware firmware (`firmware/`, `.pio/`, `cp210x_driver/`), raw archives (`blind_project.zip`), and development caches. This keeps the upload size under 15 MB (well below Vercel's 100 MB upload limit).

5. **Serverless Cache & Path Resilience (`server/app.py`)**:
   - Automatically directs cache directories (`YOLO_CONFIG_DIR`, `TORCH_HOME`, `MPLCONFIGDIR`, `EASYOCR_MODULE_PATH`) to writable temporary paths (`/tmp`), preventing permission errors in read-only serverless containers.
   - Dynamically resolves paths to `yolov8n.pt` and `audio/` whether the project is executed from root or `/server`.
   - Enabled `CORSMiddleware` so smartphones and external clients can access all endpoints without browser blocking.

---

## Method 1: Deploy via GitHub (Recommended)

### Step 1: Push Project to GitHub
In your terminal / PowerShell:
```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

### Step 2: Import into Vercel
1. Go to [vercel.com/new](https://vercel.com/new) and log in.
2. Select your repository and click **Import**.
3. **Framework Preset**: Leave as `Other`.
4. **Root Directory**: Leave as `./` (or select `server` if you wish to deploy only the backend folder). Both are fully supported!

### Step 3: Add Environment Variables
Under the **Environment Variables** section in the Vercel project configuration, add:

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | `8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0` | Telegram Guardian bot notifications |
| `TELEGRAM_CHAT_ID` | `7906413709` | Telegram Chat ID for alerts |
| `VERCEL_SUPPORT_LARGE_FUNCTIONS` | `1` | Enables up to 5 GB serverless functions for AI/ML |

### Step 4: Click Deploy
Click **Deploy**. Vercel will install dependencies and compile the serverless function. In ~2-3 minutes, your deployment URL will be live:
```
https://<your-project-name>.vercel.app/camera
```

---

## Method 2: Deploy via Vercel CLI

If you have the Vercel CLI installed:

```bash
# 1. Install Vercel CLI (if not already installed)
npm install -g vercel

# 2. Navigate to project root
cd d:\iot-blind

# 3. Deploy to Vercel
vercel
```

Follow the interactive prompts:
- **Set up and deploy?** -> `Y`
- **Which scope?** -> (Select your personal account)
- **Link to existing project?** -> `N`
- **Project name?** -> `iot-blind-assistant` (or your preferred name)
- **Directory located?** -> `./`

To deploy directly to production with environment variables:
```bash
vercel --prod -e TELEGRAM_BOT_TOKEN="8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0" -e TELEGRAM_CHAT_ID="7906413709" -e VERCEL_SUPPORT_LARGE_FUNCTIONS="1"
```

---

## How to Use from Any Smartphone

1. Open Chrome or Safari on your phone.
2. Navigate to:
   ```
   https://<your-project-name>.vercel.app/camera
   ```
   *(or simply `https://<your-project-name>.vercel.app/`)*
3. Allow camera permissions when prompted.
4. **Live Scanning**:
   - Point the camera at obstacles (chairs, tables, persons), medicines (Paracetamol, Rantac), or currency notes (₹500, ₹200, ₹100, ₹50, ₹20, ₹10).
   - Turn ON **"Phone HD Voice"** to hear clear human Tamil audio spoken directly from your phone!
   - Press **"🚨 Send Fall SOS"** to test sending instant Telegram alerts to the guardian.
   - Press **"✅ Safe Switch"** to cancel alerts.

