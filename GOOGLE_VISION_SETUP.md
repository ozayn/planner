# Google Cloud Vision API Setup Guide

This guide will help you set up Google Cloud Vision API as a backup OCR option for the Planner app.

## 🎯 Why Use Google Vision API?

- **Better accuracy** for complex images
- **Handles multiple languages** automatically
- **Works in cloud environments** where Tesseract might not be available
- **Automatic fallback** - app uses Tesseract first, Vision as backup

## 📋 Prerequisites

1. **Google Cloud Platform account** (free tier available)
2. **Billing enabled** (required for API access, but free tier covers most usage)

## 🚀 Step-by-Step Setup

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `planner-ocr` (or any name you prefer)
4. Click "Create"

### Step 2: Enable the Vision API

1. In your new project, go to **APIs & Services** → **Library**
2. Search for "Vision API"
3. Click on "Cloud Vision API"
4. Click **"Enable"**

### Step 3: Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **"Create Service Account"**
3. Fill in details:
   - **Name**: `planner-vision-api`
   - **Description**: `Service account for Planner OCR functionality`
4. Click **"Create and Continue"**
5. **Skip** adding roles for now (Vision API doesn't require specific roles)
6. Click **"Done"**

### Step 4: Generate Service Account Key

1. Find your service account in the list
2. Click on the service account name
3. Go to **"Keys"** tab
4. Click **"Add Key"** → **"Create new key"**
5. Choose **"JSON"** format
6. Click **"Create"**
7. **Download the JSON file** (keep it secure!)

### Step 5: Configure Environment Variables

#### Option A: Local Development (.env file)

Create or update your `.env` file:

```bash
# Google Cloud Vision API
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

**Example:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=/Users/oz/Dropbox/2025/planner/config/planner-vision-api-key.json
```

#### Option B: Railway Deployment

1. Go to your Railway project dashboard
2. Click on your service
3. Go to **"Variables"** tab
4. Add new variable:
   - **Key**: `GOOGLE_APPLICATION_CREDENTIALS`
   - **Value**: Paste the entire JSON content of your service account key

**⚠️ Important**: For Railway, you need to paste the JSON content directly as the value, not a file path.

### Step 6: Test the Setup

1. **Restart your application** to load the new environment variables
2. **Upload an image** through the admin panel
3. **Check the logs** for OCR engine selection:
   ```
   INFO: Using Google Cloud Vision OCR engine
   ```
   or
   ```
   INFO: Using Tesseract OCR engine
   ```

## 🔧 Alternative Setup Methods

### Method 1: Application Default Credentials (Local)

If you have the Google Cloud CLI installed:

```bash
# Install Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### Method 2: Environment Variable with JSON Content

Instead of a file path, you can set the JSON content directly:

```bash
export GOOGLE_APPLICATION_CREDENTIALS='{"type": "service_account", "project_id": "your-project", ...}'
```

## 💰 Pricing & Limits

### Free Tier
- **1,000 requests per month** for Vision API
- **No cost** for first 1,000 requests

### Paid Usage
- **$1.50 per 1,000 requests** after free tier
- Very affordable for typical usage

## 🛠️ Troubleshooting

### Common Issues

#### 1. "Credentials not found"
```
ERROR: Google Vision API error: Your default credentials were not found
```

**Solution:**
- Check `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON file
- Verify the JSON file contains valid service account key
- Restart the application after setting environment variables

#### 2. "Permission denied"
```
ERROR: Google Vision API error: Permission denied
```

**Solution:**
- Ensure Vision API is enabled in your Google Cloud project
- Verify service account has access to the project
- Check billing is enabled on your Google Cloud project

#### 3. "Quota exceeded"
```
ERROR: Google Vision API error: Quota exceeded
```

**Solution:**
- Check your Google Cloud Console for API quotas
- Consider upgrading your billing plan
- Monitor usage in Google Cloud Console

### Testing Credentials

You can test your setup with this simple Python script:

```python
from google.cloud import vision

try:
    client = vision.ImageAnnotatorClient()
    print("✅ Google Vision API credentials working!")
except Exception as e:
    print(f"❌ Error: {e}")
```

## 🔄 OCR Engine Priority

The app uses this priority order:

1. **Tesseract** (if installed) - Fast, free, local
2. **Google Vision** (if credentials available) - Accurate, cloud-based
3. **Fallback error** - If neither available

## 📝 Environment Variables Summary

Add these to your `.env` file:

```bash
# Google Cloud Vision API (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Alternative: JSON content directly (for Railway)
# GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}
```

## 🎉 You're Done!

Once configured, the app will automatically:
- Use Google Vision API when available
- Fall back to Tesseract if Vision fails
- Provide better OCR accuracy for complex images
- Work in both local and deployed environments

The OCR functionality will be more robust and accurate! 🚀
