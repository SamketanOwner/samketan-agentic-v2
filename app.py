"""
🎬 Samketan AI: Marketing Factory MVP
Auto-generate videos, posters, and social campaigns in 1 click
"""

import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import os
import json
from pathlib import Path
from datetime import datetime
import subprocess
import io
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile
import shutil

# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================
st.set_page_config(
    page_title="Samketan Marketing Factory",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { padding: 2rem; }
    .stTabs [data-baseweb="tab-list"] button { font-size: 1.1rem; }
    .success-box { background: #d4edda; padding: 1rem; border-radius: 8px; }
    .info-box { background: #d1ecf1; padding: 1rem; border-radius: 8px; }
    .warning-box { background: #fff3cd; padding: 1rem; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🎬 Samketan Marketing Factory")
st.caption("Upload photo → Generate video + poster + social campaigns → Share to all platforms")

# ============================================================================
# SIDEBAR: SETTINGS & UPLOAD
# ============================================================================
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Keys
    if "GEMINI_API_KEY" in st.secrets:
        gemini_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Gemini API Key Loaded")
    else:
        gemini_key = st.text_input("Enter Gemini API Key", type="password", key="gemini_input")
    
    # Google Drive Setup
    st.markdown("---")
    st.subheader("☁️ Google Drive Setup")
    
    drive_enabled = False
    drive_service = None
    
    try:
        if "GOOGLE_SERVICE_ACCOUNT" in st.secrets:
            creds_dict = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            drive_service = build('drive', 'v3', credentials=credentials)
            drive_enabled = True
            st.success("✅ Google Drive Connected")
        else:
            st.info("📌 Paste Google Service Account JSON in Streamlit Secrets to enable auto-upload")
    except Exception as e:
        st.warning(f"⚠️ Drive unavailable: {str(e)[:50]}")
    
    # Product Upload
    st.markdown("---")
    st.subheader("📸 Visual Input")
    
    uploaded_file = st.file_uploader(
        "Upload Product/Warehouse Photo",
        type=["jpg", "jpeg", "png"],
        help="Use high-quality images for best results"
    )
    
    image = None
    image_path = None
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Product Preview", use_container_width=True)
        
        # Save temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            image.save(tmp.name)
            image_path = tmp.name


# ============================================================================
# MAIN INTERFACE: TABS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🎬 Campaign Generator",
    "📹 Video Composer",
    "🎨 Poster Designer",
    "📤 Social Sharing"
])

# ============================================================================
# TAB 1: CAMPAIGN GENERATOR
# ============================================================================
with tab1:
    st.header("Step 1: Define Your Campaign")
    
    col1, col2 = st.columns(2)
    
    with col1:
        product_name = st.text_input(
            "Product Name",
            placeholder="e.g., Premium Toor Dal from Kalaburagi",
            key="product_name"
        )
    
    with col2:
        product_category = st.selectbox(
            "Product Category",
            ["Pulses/Grains", "Warehouse Space", "Grocery", "Spices", "Organic", "Other"],
            key="category"
        )
    
    target_audience = st.selectbox(
        "Target Audience",
        [
            "B2B (Wholesalers, Supermarkets)",
            "B2C (Direct Consumers)",
            "Corporate (For Warehouse Space)",
            "Retailers & Small Shops"
        ],
        key="audience"
    )
    
    additional_details = st.text_area(
        "Additional Details (Optional)",
        placeholder="e.g., Organic certification, bulk discounts, fast delivery...",
        key="details"
    )
    
    if st.button("🚀 Generate Full Campaign", type="primary", use_container_width=True):
        if not gemini_key:
            st.error("❌ Please enter Gemini API Key")
        elif not image:
            st.error("❌ Please upload a product photo")
        elif not product_name:
            st.error("❌ Please enter product name")
        else:
            with st.spinner("🤖 Creative Director analyzing image..."):
                try:
                    genai.configure(api_key=gemini_key)
                    
                    # Find best available vision model
                    active_model = "gemini-1.5-flash-latest"
                    try:
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods and ('1.5' in m.name or 'vision' in m.name):
                                active_model = m.name
                                break
                    except:
                        pass
                    
                    model = genai.GenerativeModel(active_model)
                    
                    prompt = f"""
You are an expert Social Media Manager, Creative Director, and Marketing Strategist.

Analyze this product image carefully. Your job is to create a complete marketing campaign package.

**PRODUCT DETAILS:**
- Product Name: {product_name}
- Category: {product_category}
- Target Audience: {target_audience}
- Additional Info: {additional_details if additional_details else "None provided"}

**CREATE A COMPLETE MARKETING CAMPAIGN WITH THESE EXACT SECTIONS:**

---

### 📌 CAMPAIGN HEADLINE
[One powerful headline that sells the product in 10 words max]

---

### 🎬 NARRATION SCRIPT (For Video)
[60-90 seconds of engaging narration for a video. Make it exciting, conversational, benefit-focused]
[Start with a hook, explain 3 key benefits, end with CTA]
[Write as if being spoken aloud - natural, energetic tone]

---

### 🎨 POSTER DESIGN BRIEF
**Background Color:** [Suggest primary color]
**Typography Style:** [Modern/Classic/Bold/Elegant]
**Main Text:** [Headline for poster - max 3 lines]
**Tagline:** [2-word catchy phrase]
**Call to Action:** [Button text - max 3 words]

---

### 📱 LINKEDIN POST
[Professional, B2B-focused post with business value emphasis]
[Include supply chain, quality, or batch ordering benefits]
[2-3 relevant hashtags max]

---

### 📸 INSTAGRAM REELS CAPTION
[Catchy, emoji-rich, highly engaging 1-2 lines]
[Viral hashtags: 8-10 trending ones for this category]

---

### 👍 FACEBOOK POST
[Conversational, community-focused post]
[Emphasis on local/trusted brand]
[3-5 relevant hashtags]

---

### 💬 WHATSAPP BROADCAST MESSAGE
[Short, direct, urgency-driven message]
[Max 2 sentences + clear CTA button text]

---

**IMPORTANT:** Be specific to the product shown. Make it compelling, authentic, and ready-to-publish immediately.
"""
                    
                    response = model.generate_content([prompt, image])
                    
                    # Store campaign in session state
                    st.session_state.campaign_content = response.text
                    st.session_state.product_name = product_name
                    st.session_state.product_category = product_category
                    st.session_state.image = image
                    st.session_state.image_path = image_path
                    st.session_state.gemini_key = gemini_key
                    st.session_state.drive_service = drive_service
                    st.session_state.drive_enabled = drive_enabled
                    
                    st.success("✅ Campaign Generated Successfully!")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


# ============================================================================
# TAB 2: VIDEO COMPOSER
# ============================================================================
with tab2:
    st.header("Step 2: Generate Video with AI Narration")
    
    if "campaign_content" not in st.session_state:
        st.info("👈 Please generate a campaign first (Tab 1)")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Video Settings")
            
            video_format = st.selectbox(
                "Select Video Format",
                {
                    "Instagram Reels (9:16)": {"res": (1080, 1920), "duration": 30},
                    "YouTube Short (9:16)": {"res": (1080, 1920), "duration": 60},
                    "Facebook Feed (16:9)": {"res": (1280, 720), "duration": 30},
                    "WhatsApp (1:1)": {"res": (1080, 1080), "duration": 15}
                },
                format_func=lambda x: x
            )
            
            video_speed = st.slider("Narration Speed", 0.8, 1.5, 1.0, step=0.1)
            background_music = st.checkbox("Add Royalty-Free Background Music", value=False)
        
        with col2:
            st.subheader("Preview Settings")
            show_captions = st.checkbox("Add Captions to Video", value=True)
            caption_color = st.color_picker("Caption Color", "#FFFFFF")
        
        if st.button("🎬 Generate Video", type="primary", use_container_width=True):
            st.warning("⏳ Video generation in progress (2-3 minutes)...")
            
            with st.spinner("🎙️ Generating AI narration..."):
                try:
                    # Extract narration script from campaign
                    campaign = st.session_state.campaign_content
                    
                    # Parse narration from campaign
                    if "NARRATION SCRIPT" in campaign:
                        narration_start = campaign.find("NARRATION SCRIPT") + len("NARRATION SCRIPT")
                        narration_end = campaign.find("---", narration_start)
                        narration = campaign[narration_start:narration_end].strip()
                    else:
                        narration = "Check out our amazing product!"
                    
                    st.info(f"📝 Narration: {narration[:100]}...")
                    
                    # Step 1: Generate audio using Google Cloud TTS (free tier)
                    try:
                        from google.cloud import texttospeech
                        
                        tts_client = texttospeech.TextToSpeechClient(
                            credentials=service_account.Credentials.from_service_account_info(
                                st.secrets.get("GOOGLE_SERVICE_ACCOUNT", {})
                            )
                        )
                        
                        synthesis_input = texttospeech.SynthesisInput(text=narration)
                        voice = texttospeech.VoiceSelectionParams(
                            language_code="en-IN",
                            name="en-IN-Neural2-A",
                            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
                        )
                        audio_config = texttospeech.AudioConfig(
                            audio_encoding=texttospeech.AudioEncoding.MP3,
                            speaking_rate=video_speed
                        )
                        
                        response = tts_client.synthesize_speech(
                            input=synthesis_input,
                            voice=voice,
                            audio_config=audio_config
                        )
                        
                        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        audio_file.write(response.audio_content)
                        audio_file.close()
                        audio_path = audio_file.name
                        
                        st.success("✅ Narration generated (English - India accent)")
                    
                    except:
                        # Fallback: Use pyttsx3 for offline TTS
                        st.info("📌 Using offline text-to-speech (pyttsx3)")
                        import pyttsx3
                        
                        engine = pyttsx3.init()
                        engine.setProperty('rate', int(150 * video_speed))
                        
                        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                        audio_path = audio_file.name
                        audio_file.close()
                        
                        engine.save_to_file(narration, audio_path)
                        engine.runAndWait()
                        
                        st.success("✅ Narration generated (offline)")
                    
                    # Step 2: Generate video using MoviePy
                    with st.spinner("🎬 Composing video..."):
                        try:
                            from moviepy.editor import (
                                ImageClip, AudioFileClip, CompositeVideoClip,
                                TextClip, ColorClip, concatenate_videoclips
                            )
                            from moviepy.video.fx.resize import resize
                            
                            format_config = video_format.split("(")[1].rstrip(")")
                            width, height = video_format["res"]
                            
                            # Load image and audio
                            image_clip = ImageClip(st.session_state.image_path)
                            image_clip = resize(image_clip, width=width, height=height)
                            
                            audio_clip = AudioFileClip(audio_path)
                            duration = audio_clip.duration
                            
                            image_clip = image_clip.set_duration(duration)
                            
                            # Add captions if enabled
                            if show_captions:
                                headline = st.session_state.campaign_content.split("CAMPAIGN HEADLINE")[1].split("---")[0].strip()[:60]
                                
                                txt_clip = TextClip(
                                    headline,
                                    fontsize=50,
                                    color=caption_color.lstrip("#"),
                                    font="Arial-Bold",
                                    method="caption",
                                    size=(width - 100, None)
                                )
                                txt_clip = txt_clip.set_duration(duration)
                                txt_clip = txt_clip.set_position(("center", "bottom"))
                                
                                final_clip = CompositeVideoClip([image_clip, txt_clip])
                            else:
                                final_clip = image_clip
                            
                            # Add audio
                            final_clip = final_clip.set_audio(audio_clip)
                            
                            # Save video
                            video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                            video_path.close()
                            
                            final_clip.write_videofile(
                                video_path.name,
                                fps=24,
                                codec='libx264',
                                audio_codec='aac',
                                verbose=False,
                                logger=None
                            )
                            
                            st.session_state.video_path = video_path.name
                            st.success("✅ Video generated successfully!")
                            
                            # Display video
                            with open(video_path.name, "rb") as f:
                                video_bytes = f.read()
                            
                            st.video(video_bytes)
                            
                            # Download button
                            st.download_button(
                                label="⬇️ Download Video",
                                data=video_bytes,
                                file_name=f"{st.session_state.product_name}_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                                mime="video/mp4"
                            )
                        
                        except Exception as e:
                            st.error(f"❌ Video generation error: {str(e)}")
                            st.info("💡 Ensure ffmpeg is installed: `pip install moviepy imageio`")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


# ============================================================================
# TAB 3: POSTER DESIGNER
# ============================================================================
with tab3:
    st.header("Step 3: AI-Designed Poster")
    
    if "campaign_content" not in st.session_state:
        st.info("👈 Please generate a campaign first (Tab 1)")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Poster Settings")
            
            poster_format = st.selectbox(
                "Select Poster Format",
                {
                    "Instagram Square (1080x1080)": (1080, 1080),
                    "Instagram Story (1080x1920)": (1080, 1920),
                    "Facebook (1200x628)": (1200, 628),
                    "WhatsApp Status (1080x1920)": (1080, 1920),
                    "Custom": None
                },
                format_func=lambda x: x
            )
            
            if poster_format == "Custom":
                w, h = st.columns(2)
                with w:
                    custom_width = st.number_input("Width", 800, 2000, 1080)
                with h:
                    custom_height = st.number_input("Height", 600, 2000, 1080)
                poster_format = (custom_width, custom_height)
        
        with col2:
            st.subheader("Design Settings")
            bg_color = st.color_picker("Background Color", "#003366")
            text_color = st.color_picker("Text Color", "#FFFFFF")
        
        if st.button("🎨 Generate Poster", type="primary", use_container_width=True):
            with st.spinner("🎨 Designing poster..."):
                try:
                    from PIL import ImageFilter, ImageEnhance
                    
                    campaign = st.session_state.campaign_content
                    
                    # Extract design brief
                    if "POSTER DESIGN BRIEF" in campaign:
                        brief_start = campaign.find("POSTER DESIGN BRIEF") + len("POSTER DESIGN BRIEF")
                        brief_end = campaign.find("---", brief_start)
                        design_brief = campaign[brief_start:brief_end].strip()
                    else:
                        design_brief = "Amazing Product!"
                    
                    # Parse design elements
                    lines = [l.strip() for l in design_brief.split("\n") if l.strip()]
                    main_text = st.session_state.product_name
                    tagline = "Premium Quality | Best Price"
                    cta = "Order Now"
                    
                    for line in lines:
                        if "Main Text:" in line:
                            main_text = line.split("Main Text:")[-1].strip()
                        elif "Tagline:" in line:
                            tagline = line.split("Tagline:")[-1].strip()
                        elif "Call to Action:" in line:
                            cta = line.split("Call to Action:")[-1].strip()
                    
                    # Create poster
                    width, height = poster_format
                    
                    # Load and resize image as background
                    bg_image = st.session_state.image.copy()
                    bg_image = bg_image.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Create semi-transparent overlay
                    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 180))
                    bg_image.paste(overlay, (0, 0), overlay)
                    
                    # Add text
                    draw = ImageDraw.Draw(bg_image)
                    
                    # Estimate font sizes
                    title_size = max(30, int(width / 15))
                    tagline_size = max(20, int(width / 25))
                    cta_size = max(18, int(width / 28))
                    
                    try:
                        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_size)
                        tagline_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", tagline_size)
                        cta_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", cta_size)
                    except:
                        title_font = ImageFont.load_default()
                        tagline_font = ImageFont.load_default()
                        cta_font = ImageFont.load_default()
                    
                    # Draw main text
                    title_color = tuple(int(text_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (255,)
                    y_position = height // 3
                    
                    draw.text((width // 2, y_position), main_text, fill=title_color, font=title_font, anchor="mm", align="center")
                    
                    # Draw tagline
                    y_position += title_size + 20
                    draw.text((width // 2, y_position), tagline, fill=title_color, font=tagline_font, anchor="mm", align="center")
                    
                    # Draw CTA button
                    y_position = height - 80
                    button_width = 200
                    button_height = 50
                    button_x = (width - button_width) // 2
                    button_y = y_position - button_height // 2
                    
                    # Draw button background
                    draw.rectangle(
                        [(button_x, button_y), (button_x + button_width, button_y + button_height)],
                        fill=tuple(int(text_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
                    )
                    
                    # Draw button text
                    draw.text(
                        (width // 2, button_y + button_height // 2),
                        cta,
                        fill=(0, 0, 0, 255),
                        font=cta_font,
                        anchor="mm",
                        align="center"
                    )
                    
                    st.session_state.poster = bg_image
                    
                    st.success("✅ Poster generated!")
                    st.image(bg_image, use_container_width=True)
                    
                    # Download button
                    poster_bytes = io.BytesIO()
                    bg_image.save(poster_bytes, format="PNG")
                    poster_bytes.seek(0)
                    
                    st.download_button(
                        label="⬇️ Download Poster",
                        data=poster_bytes,
                        file_name=f"{st.session_state.product_name}_poster_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        mime="image/png"
                    )
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


# ============================================================================
# TAB 4: SOCIAL SHARING
# ============================================================================
with tab4:
    st.header("Step 4: Share to Social Media")
    
    if "campaign_content" not in st.session_state:
        st.info("👈 Please generate a campaign first (Tab 1)")
    else:
        st.subheader("📤 Share Your Campaign")
        
        # Extract social content from campaign
        campaign = st.session_state.campaign_content
        
        linkedin_post = ""
        instagram_caption = ""
        facebook_post = ""
        whatsapp_message = ""
        
        if "LINKEDIN POST" in campaign:
            linkedin_start = campaign.find("LINKEDIN POST") + len("LINKEDIN POST")
            linkedin_end = campaign.find("---", linkedin_start)
            linkedin_post = campaign[linkedin_start:linkedin_end].strip()
        
        if "INSTAGRAM REELS CAPTION" in campaign:
            instagram_start = campaign.find("INSTAGRAM REELS CAPTION") + len("INSTAGRAM REELS CAPTION")
            instagram_end = campaign.find("---", instagram_start)
            instagram_caption = campaign[instagram_start:instagram_end].strip()
        
        if "FACEBOOK POST" in campaign:
            facebook_start = campaign.find("FACEBOOK POST") + len("FACEBOOK POST")
            facebook_end = campaign.find("---", facebook_start)
            facebook_post = campaign[facebook_start:facebook_end].strip()
        
        if "WHATSAPP BROADCAST MESSAGE" in campaign:
            whatsapp_start = campaign.find("WHATSAPP BROADCAST MESSAGE") + len("WHATSAPP BROADCAST MESSAGE")
            whatsapp_end = campaign.find("---", whatsapp_start)
            whatsapp_message = campaign[whatsapp_start:whatsapp_end].strip()
        
        # Social Media Options
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔗 LinkedIn")
            st.text_area("LinkedIn Post", value=linkedin_post, height=150, key="linkedin_textarea", disabled=True)
            
            linkedin_url = f"https://www.linkedin.com/feed/?feedUpdate=urn%3Ali%3AactivityId%3A0"
            st.markdown(f"[✏️ Edit & Post on LinkedIn]({linkedin_url})", unsafe_allow_html=True)
            
            st.info("Steps:\n1. Click link above\n2. Copy-paste the text\n3. Add video/image\n4. Post!")
        
        with col2:
            st.subheader("📸 Instagram Reels")
            st.text_area("Instagram Caption", value=instagram_caption, height=150, key="instagram_textarea", disabled=True)
            
            instagram_url = "https://www.instagram.com/"
            st.markdown(f"[📱 Post on Instagram]({instagram_url})", unsafe_allow_html=True)
        
        st.markdown("---")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("👍 Facebook")
            st.text_area("Facebook Post", value=facebook_post, height=150, key="facebook_textarea", disabled=True)
            
            facebook_url = "https://www.facebook.com/"
            st.markdown(f"[📘 Post on Facebook]({facebook_url})", unsafe_allow_html=True)
        
        with col4:
            st.subheader("💬 WhatsApp")
            st.text_area("WhatsApp Message", value=whatsapp_message, height=150, key="whatsapp_textarea", disabled=True)
            
            whatsapp_url = f"https://wa.me/?text={whatsapp_message.replace(' ', '%20')}"
            st.markdown(f"[💬 Send on WhatsApp]({whatsapp_url})", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Google Drive Upload
        if st.session_state.drive_enabled:
            st.subheader("☁️ Save to Google Drive")
            
            folder_name = st.text_input("Campaign Folder Name", value=f"{st.session_state.product_name}_{datetime.now().strftime('%Y%m%d')}")
            
            if st.button("📁 Upload to Google Drive", type="primary", use_container_width=True):
                with st.spinner("Uploading files..."):
                    try:
                        # Create folder
                        folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                        folder = st.session_state.drive_service.files().create(body=folder_metadata, fields='id').execute()
                        folder_id = folder.get('id')
                        
                        uploaded_files = []
                        
                        # Upload poster
                        if "poster" in st.session_state:
                            poster_bytes = io.BytesIO()
                            st.session_state.poster.save(poster_bytes, format="PNG")
                            poster_bytes.seek(0)
                            
                            poster_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            poster_temp.write(poster_bytes.getvalue())
                            poster_temp.close()
                            
                            file_metadata = {'name': f'{folder_name}_poster.png', 'parents': [folder_id]}
                            media = MediaFileUpload(poster_temp.name, mimetype='image/png')
                            st.session_state.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                            uploaded_files.append("Poster")
                        
                        # Upload video
                        if "video_path" in st.session_state:
                            file_metadata = {'name': f'{folder_name}_video.mp4', 'parents': [folder_id]}
                            media = MediaFileUpload(st.session_state.video_path, mimetype='video/mp4')
                            st.session_state.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                            uploaded_files.append("Video")
                        
                        # Upload campaign text
                        campaign_text = f"""
CAMPAIGN: {st.session_state.product_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{campaign}
"""
                        campaign_temp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt")
                        campaign_temp.write(campaign_text)
                        campaign_temp.close()
                        
                        file_metadata = {'name': f'{folder_name}_campaign.txt', 'parents': [folder_id]}
                        media = MediaFileUpload(campaign_temp.name, mimetype='text/plain')
                        st.session_state.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                        uploaded_files.append("Campaign Brief")
                        
                        st.success(f"✅ Uploaded to Google Drive: {', '.join(uploaded_files)}")
                        st.markdown(f"📁 [Open Folder in Google Drive](https://drive.google.com/drive/folders/{folder_id})")
                    
                    except Exception as e:
                        st.error(f"❌ Upload failed: {str(e)}")
        else:
            st.warning("⚠️ Google Drive not connected. Set up Google Service Account in Streamlit Secrets to enable auto-upload.")
        
        # Download All
        st.markdown("---")
        st.subheader("📦 Download Package")
        
        if st.button("📥 Download All Files (ZIP)", type="primary", use_container_width=True):
            import zipfile
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add campaign text
                campaign_text = st.session_state.campaign_content
                zf.writestr(f"{st.session_state.product_name}_campaign.txt", campaign_text)
                
                # Add social posts
                social_posts = f"""
LINKEDIN:
{linkedin_post}

---

INSTAGRAM:
{instagram_caption}

---

FACEBOOK:
{facebook_post}

---

WHATSAPP:
{whatsapp_message}
"""
                zf.writestr(f"{st.session_state.product_name}_social_posts.txt", social_posts)
                
                # Add poster
                if "poster" in st.session_state:
                    poster_bytes = io.BytesIO()
                    st.session_state.poster.save(poster_bytes, format="PNG")
                    zf.writestr(f"{st.session_state.product_name}_poster.png", poster_bytes.getvalue())
                
                # Add video
                if "video_path" in st.session_state:
                    with open(st.session_state.video_path, 'rb') as f:
                        zf.writestr(f"{st.session_state.product_name}_video.mp4", f.read())
            
            zip_buffer.seek(0)
            
            st.download_button(
                label="📥 Download Complete Campaign Package",
                data=zip_buffer,
                file_name=f"{st.session_state.product_name}_campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                type="primary"
            )


# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: #f0f2f6; border-radius: 10px;">
    <p><strong>Samketan AI Marketing Factory</strong></p>
    <p>Turn any product image into a complete multi-channel marketing campaign in minutes</p>
    <p style="font-size: 0.9rem; color: #666;">
        Built for MSMEs in Tier-2 & Tier-3 cities | Powered by Gemini AI
    </p>
</div>
""", unsafe_allow_html=True)
