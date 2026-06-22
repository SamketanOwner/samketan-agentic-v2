# 🎬 Samketan Marketing Factory

> **Transform any product image into a complete multi-channel marketing campaign in seconds**

[![Deployed on Hugging Face](https://img.shields.io/badge/Deployed%20on-Hugging%20Face-FFD700?logo=huggingface)](https://huggingface.co/spaces)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

---

## ✨ What It Does

Samketan Marketing Factory is an **AI-powered marketing automation platform** that generates professional marketing content from product photos in minutes:

- 📱 **AI-Generated Social Posts** (LinkedIn, Instagram, Facebook, WhatsApp)
- 🎬 **AI-Narrated Videos** (15-120 seconds, multiple formats)
- 🎨 **AI-Designed Posters** (Optimized for each platform)
- ☁️ **Auto-Upload to Google Drive** (All campaigns saved automatically)
- 🚀 **One-Click Social Sharing** (Direct links to share)

### The Problem It Solves

```
❌ Before: Product photo → Hire freelancer → Pay $50-200 → Wait 2-5 days → Get 1 version
✅ After: Product photo → Upload to app → 2 minutes → Get: Video + Poster + Posts + Drive upload
```

---

## 🎯 Key Features

### 1. Campaign Generator
- Upload product photo
- Describe your product (name, category, details)
- Select target audience (B2B/B2C/Corporate)
- AI generates complete marketing copy for all platforms

### 2. Video Composer
- Generates AI narration using Google Cloud Text-to-Speech (Indian English accent)
- Composes video with product image + narration
- Multiple format outputs (Instagram Reels, YouTube, Facebook, WhatsApp)
- Optional captions and background music support

### 3. Poster Designer
- AI analyzes product and generates design brief
- Creates poster with smart text placement
- Multiple resolutions (Instagram, Facebook, WhatsApp optimized)
- Color customization options

### 4. Social Sharing Hub
- Ready-to-publish captions for each platform
- Download all assets as ZIP package
- Auto-upload to Google Drive (if configured)
- Direct sharing links for each platform

---

## 🚀 Quick Start

### Option 1: Use Online (No Installation)

**Live at:** [Samketan Marketing Factory on Hugging Face](https://huggingface.co/spaces/yourusername/samketan-marketing-factory)

1. Click the link above
2. Add your API keys in Settings
3. Upload product photo
4. Generate campaign
5. Download or share!

### Option 2: Run Locally

```bash
# Clone repository
git clone https://github.com/yourusername/samketan-marketing-factory.git
cd samketan-marketing-factory

# Install dependencies
pip install -r requirements.txt

# Create secrets file
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
GEMINI_API_KEY = "your-api-key-here"

[GOOGLE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "your-project"
# ... (paste full JSON)
EOF

# Run app
streamlit run app.py
```

Visit `http://localhost:8501`

---

## 📋 Requirements

### API Keys (All Free!)
- **Gemini API Key** (free tier: 60 req/min) → [Get here](https://makersuite.google.com/app/apikey)
- **Google Cloud Service Account** (free tier) → [Setup guide](SETUP_GUIDE.md)

### System Requirements
- Python 3.9+
- 4GB RAM
- Internet connection
- ffmpeg (for video processing)

```bash
# Install ffmpeg
# macOS: brew install ffmpeg
# Ubuntu: sudo apt-get install ffmpeg
# Windows: choco install ffmpeg
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Streamlit 1.28+ | Web UI |
| **AI/LLM** | Google Gemini API | Content generation |
| **TTS** | Google Cloud Text-to-Speech | AI narration |
| **Video** | MoviePy 1.0.3 | Video composition |
| **Images** | Pillow 10.0+ | Poster design |
| **Storage** | Google Drive API | Auto-upload |
| **Search** | DuckDuckGo (future) | Market research |

---

## 📁 Project Structure

```
samketan-marketing-factory/
├── app.py                       # Main Streamlit application
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── QUICKSTART.md               # 30-minute setup guide
├── SETUP_GUIDE.md              # Comprehensive setup
├── FAQ.md                       # Common questions & fixes
├── IMPLEMENTATION_SUMMARY.md   # Executive overview
├── FILE_GUIDE.md               # File navigation
├── .streamlit/
│   └── secrets.toml            # API keys (do NOT commit!)
└── docs/                        # Additional documentation
    ├── ARCHITECTURE.md
    ├── API_REFERENCE.md
    └── TROUBLESHOOTING.md
```

---

## 🎯 Use Cases

### E-Commerce Sellers
```
Upload dal pack → Generate Instagram video + poster
→ Post to social media → Get sales
```

### Warehouse Operators
```
Upload warehouse photo → Generate 10 variations
→ Send to corporate clients → Win contracts
```

### Agricultural FPOs
```
Upload pulse product → Auto-generate seasonal campaigns
→ Drive retail distribution
```

### B2B Companies
```
Upload solution screenshot → Generate LinkedIn posts + email copy
→ Auto-share with prospects
```

---

## 📊 Features by Tab

### Tab 1: 🎬 Campaign Generator
- Product name & category input
- Target audience selection
- AI-generated copy for all platforms
- Output: LinkedIn, Instagram, Facebook, WhatsApp posts

### Tab 2: 📹 Video Composer
- Video format selection (Instagram/YouTube/Facebook/WhatsApp)
- Narration speed control
- Caption generation
- Output: MP4 video with AI narration

### Tab 3: 🎨 Poster Designer
- Multiple resolution options
- Color customization
- AI-designed layouts
- Output: PNG poster (ready to post)

### Tab 4: 📤 Social Sharing
- Copy-paste ready posts
- Direct platform links
- Batch download (ZIP)
- Google Drive auto-upload

---

## 🔐 Security & Privacy

### API Keys
- ✅ Stored in encrypted Streamlit Secrets
- ✅ Never logged or exposed
- ✅ Never sent to frontend
- ✅ Server-side only

### User Data
- ✅ Product photos: Deleted after processing
- ✅ Generated content: Stored in YOUR Google Drive
- ✅ No user registration needed
- ✅ No tracking or cookies

### Compliance
- ✅ GDPR compliant (no personal data stored)
- ✅ India-PDPL compliant
- ✅ Open source (audit code yourself)

---

## 💰 Cost

| Item | Cost | Notes |
|------|------|-------|
| Gemini API | $0 | Free tier: 60 req/min |
| Google Cloud TTS | $0 | Free tier: 1M chars/month |
| Google Drive | $0 | 15GB storage |
| Hugging Face Spaces | $0 | Free tier: 24/7, 50GB |
| Total | **$0/month** | Unlimited campaigns! |

---

## 🚀 Deployment

### Deploy to Hugging Face Spaces (Recommended)

1. Create Space: https://huggingface.co/new-space
2. Clone: `git clone https://huggingface.co/spaces/USERNAME/SPACENAME`
3. Copy files and push: `git push`
4. Add secrets in Settings
5. Done! ✅

**Full guide:** [QUICKSTART.md](QUICKSTART.md)

### Deploy Locally

```bash
streamlit run app.py
```

### Deploy to Streamlit Cloud

```bash
streamlit login
streamlit deploy
```

---

## 📖 Documentation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [QUICKSTART.md](QUICKSTART.md) | 30-minute launch guide | 30 min |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Comprehensive reference | 60 min |
| [FAQ.md](FAQ.md) | 50+ Q&A & troubleshooting | 15 min |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Executive overview | 10 min |
| [FILE_GUIDE.md](FILE_GUIDE.md) | File navigation | 5 min |

---

## 🎓 How It Works

### Architecture Flow

```
User uploads product photo
        ↓
[Gemini Vision] Analyzes image → Extracts product details
        ↓
[Campaign Generator] Creates copy for all platforms
        ↓
[Google Cloud TTS] Converts text to speech (Indian accent)
        ↓
[MoviePy] Composes video (image + audio + captions)
        ↓
[Pillow] Generates poster with AI design recommendations
        ↓
[Google Drive API] Auto-uploads all files to user's Drive
        ↓
User downloads or shares directly to social media
```

### AI Models Used
- **Gemini 1.5 Flash**: Fast content generation (default)
- **Gemini 1.5 Pro**: High-quality when needed
- **Google Cloud TTS**: Indian English narration
- **Vision Model**: Product analysis

---

## 🔧 Configuration

### Environment Variables / Secrets

```toml
# .streamlit/secrets.toml

GEMINI_API_KEY = "AIza..."

[GOOGLE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "..."
client_email = "..."
# ... (paste entire JSON)
```

### Settings

All settings are adjustable in the app:
- Video duration (15-120 sec)
- Narration speed (0.8x - 1.5x)
- Caption color
- Poster dimensions
- Audio quality

---

## 📈 Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Campaign generation | 1-2 min | Includes copy + design |
| Video generation | 2-3 min | 1080p quality |
| Poster generation | 30 sec | Multiple resolutions |
| Auto-upload | < 1 min | Google Drive |
| **Total time** | **3-5 min** | From upload to download |

---

## 🐛 Common Issues

### Issue: `ffmpeg not found`
**Solution:** Install ffmpeg (see Requirements section)

### Issue: `API Key not found`
**Solution:** Add `GEMINI_API_KEY` to Streamlit Secrets

### Issue: `Google Drive unavailable`
**Solution:** Add `GOOGLE_SERVICE_ACCOUNT` JSON to Secrets

### Issue: Video generation times out
**Solution:** Reduce video duration or upgrade Hugging Face (Pro)

**More help:** [FAQ.md](FAQ.md)

---

## 🚀 Roadmap

### Phase 1: MVP (Current) ✅
- ✅ AI copy generation
- ✅ Video composition
- ✅ Poster design
- ✅ Google Drive auto-upload
- ✅ Hugging Face deployment

### Phase 2: Direct Posting (2 weeks)
- ⏳ Instagram direct posting (Meta API)
- ⏳ Facebook direct posting
- ⏳ LinkedIn direct posting
- ⏳ WhatsApp Cloud API

### Phase 3: Monetization (4 weeks)
- ⏳ Freemium pricing model
- ⏳ Stripe/Razorpay integration
- ⏳ User analytics
- ⏳ Campaign history

### Phase 4: Scale (8 weeks)
- ⏳ Multi-language support (Hindi, Kannada)
- ⏳ Template library
- ⏳ Bulk campaign generation
- ⏳ White-label version

---

## 🤝 Contributing

Contributions welcome! Areas to help:

1. **Feature requests**: Open an Issue
2. **Bug reports**: Open an Issue with reproduction steps
3. **Code contributions**: Fork → Create branch → Pull request
4. **Documentation**: Improve existing docs or add new guides

---

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

Built for MSMEs in Tier-2 & Tier-3 cities, especially farmers and warehouse operators.

Powered by:
- Google Gemini API
- Google Cloud Text-to-Speech
- MoviePy & Pillow
- Streamlit
- Hugging Face

---

## 📞 Support

### For Issues
1. Check [FAQ.md](FAQ.md)
2. Check [SETUP_GUIDE.md](SETUP_GUIDE.md)
3. Open a GitHub Issue

### For Questions
- Email: support@samketan.ai
- LinkedIn: /in/niketan-samketan-ai/
- GitHub Discussions: (if enabled)

---

## 🌍 About Samketan

Samketan builds **enterprise-grade AI tools for MSMEs in India**.

Our mission:
- 🚀 Democratize AI for Tier-2 & Tier-3 cities
- 👨‍🌾 Empower farmers & agricultural businesses
- 📈 Enable B2B growth for small businesses
- 💰 Create economic opportunities

**Made in India. For India.** 🇮🇳

---

## 🎬 Ready to Get Started?

1. **Try Online**: [Samketan Marketing Factory](https://huggingface.co/spaces/yourusername/samketan-marketing-factory)
2. **Read Guide**: [QUICKSTART.md](QUICKSTART.md)
3. **Local Setup**: `pip install -r requirements.txt && streamlit run app.py`

**Questions?** Check [FILE_GUIDE.md](FILE_GUIDE.md) to navigate all docs!

---

**Happy marketing! 🎉**

*Transform your products into campaigns. Scale your marketing. Grow your business.*

---

**Last updated:** June 2024  
**Status:** Active Development  
**Latest version:** 2.0 (MVP)
