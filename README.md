# Samketan Marketing Factory

Generate a complete online marketing package from one product or warehouse photo:

- Gemini-powered campaign copy
- LinkedIn, Instagram, Facebook, and WhatsApp posts
- Downloadable poster
- Downloadable short video
- Optional Google Drive upload
- Optional Google Cloud Text-to-Speech narration

Live app:
https://samketan-agentic-v2-6cfdnhfupbhcrcha6vyfmt.streamlit.app/

## Important Fix

The old app could auto-select retired preview models such as
`models/gemini-robotics-er-1.5-preview`, which causes:

```text
Error: 404 This model models/gemini-robotics-er-1.5-preview is no longer available.
```

This version uses the official `google-genai` SDK and defaults to:

```text
gemini-3.5-flash
```

You can override the model in Streamlit Secrets with `GEMINI_MODEL`, but do not use
robotics preview models for marketing copy.

## Streamlit Cloud Secrets

Open the app in Streamlit Cloud, then go to:

```text
Settings -> Secrets
```

Add:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
GEMINI_MODEL = "gemini-3.5-flash"
```

Optional Google Drive upload and Google Cloud Text-to-Speech:

```toml
[GOOGLE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

For Drive upload, share the target Google Drive folder with the service account
email, or use the link created by the app's service-account Drive space.

## Local Run

```bash
git clone https://github.com/SamketanOwner/samketan-agentic-v2.git
cd samketan-agentic-v2
pip install -r requirements.txt
streamlit run app.py
```

For local secrets, create `.streamlit/secrets.toml` with the same values shown
above.

## Deployment Files

Streamlit Cloud reads these files:

- `app.py` - main Streamlit application
- `requirements.txt` - Python dependencies
- `packages.txt` - system packages, including `ffmpeg` for video rendering

## Workflow

1. Add your Gemini API key in Streamlit Secrets.
2. Upload a product or warehouse image.
3. Enter the product name, category, target audience, and any offer details.
4. Generate the campaign.
5. Create a poster and video.
6. Download the package or upload it to Google Drive.

## Notes

- Use stable Gemini models for production.
- Preview and robotics models can be retired and should not be used for this app.
- Video generation needs `ffmpeg`; Streamlit Cloud installs it from
  `packages.txt`.
- The video generator renders text with Pillow, so it does not require
  ImageMagick.
