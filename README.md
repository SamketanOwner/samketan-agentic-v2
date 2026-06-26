Samketan Marketing Factory — Business Marketing Kit
Generate a complete online marketing package from your business details, logo, and product/warehouse photos:
•	Business Profile: Collect business name, product details, category, audience, tone, event info, achievements, and social media links
•	AI-Powered Campaign: Gemini generates tailored copy for LinkedIn, Instagram, Facebook, and WhatsApp
•	Poster: Downloadable branded poster with logo overlay
•	Video: Short social media video with optional Google Cloud Text-to-Speech narration
•	Event Invitation Card: Beautiful invitation with venue and date/time
•	Event Proceedings: Structured event highlights document
•	Achievements Showcase: Branded card for recent milestones
•	Social Promotion: One-click links to Instagram, Facebook, LinkedIn, and WhatsApp with pre-written copy
•	Google Drive Upload: Save the full package to Drive
Live app: https://samketan-agentic-v2-6cfdnhfupbhcrcha6vyfmt.streamlit.app/
What’s New
v2 — Business Marketing Kit
•	Multi-photo upload: Upload logo + 3-4 product/warehouse photos
•	Event support: Create invitation cards and proceedings documents
•	Achievements: Showcase recent milestones with branded cards
•	Social links: Store Instagram, Facebook, LinkedIn, and WhatsApp URLs
•	One-click social buttons: Open your social pages instantly with pre-written copy
•	Logo overlay: Logo appears on posters and videos automatically
•	Updated to google-genai SDK with gemini-3.5-flash default
Important Fix
The old app could auto-select retired preview models such as models/gemini-robotics-er-1.5-preview, which causes:
Error: 404 This model models/gemini-robotics-er-1.5-preview is no longer available.
This version uses the official google-genai SDK and defaults to:
gemini-3.5-flash
You can override the model in Streamlit Secrets with GEMINI_MODEL, but do not use robotics preview models for marketing copy.
Streamlit Cloud Secrets
Open the app in Streamlit Cloud, then go to:
Settings -> Secrets
Add:
GEMINI_API_KEY = "your-gemini-api-key"
GEMINI_MODEL = "gemini-3.5-flash"
Optional Google Drive upload and Google Cloud Text-to-Speech:
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
For Drive upload, share the target Google Drive folder with the service account email, or use the link created by the app’s service-account Drive space.
Local Run
git clone https://github.com/SamketanOwner/samketan-agentic-v2.git
cd samketan-agentic-v2
pip install -r requirements.txt
streamlit run app.py
For local secrets, create .streamlit/secrets.toml with the same values shown above.
Deployment Files
Streamlit Cloud reads these files:
•	app.py — main Streamlit application
•	requirements.txt — Python dependencies
•	packages.txt — system packages, including ffmpeg for video rendering
Workflow
1.	Add your Gemini API key in Streamlit Secrets.
2.	Go to the Business Profile tab.
3.	Enter business name, product name, category, audience, and tone.
4.	Upload your logo (optional) and 3-4 product/warehouse photos.
5.	Fill in Event Details and Achievements (optional).
6.	Add your Social Media Links (optional).
7.	Click Generate Marketing Kit.
8.	Create poster, video, invitation, proceedings, and achievement cards.
9.	Use Social & Drive tab to download the full package or upload to Google Drive.
Social Media Posting
This app provides one-click open links to your social media pages with pre-written copy ready to paste. True background auto-posting requires official API credentials for each platform:
Platform	API Required	Notes
Instagram	Meta Graph API + Business Account	Needs app review
Facebook	Meta Graph API + Page Access Token	Needs app review
LinkedIn	LinkedIn Marketing API + OAuth 2.0	Needs partner program
WhatsApp	WhatsApp Business API	Needs Meta Business verification
For most Indian MSMEs, the one-click open + copy-paste workflow is the fastest practical approach today.
Notes
•	Use stable Gemini models for production.
•	Preview and robotics models can be retired and should not be used for this app.
•	Video generation needs ffmpeg; Streamlit Cloud installs it from packages.txt.
•	The video generator renders text with Pillow, so it does not require ImageMagick.
•	Upload 3-4 photos for the best AI analysis and campaign quality.
