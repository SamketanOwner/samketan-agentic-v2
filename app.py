"""
Samketan Marketing Factory

Streamlit app for creating product marketing campaigns from one image:
campaign copy, social posts, posters, optional video, and optional Drive upload.
"""

import io
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import streamlit as st
from google import genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


APP_NAME = "Samketan Marketing Factory"
DEFAULT_MODEL = "gemini-3.5-flash"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CATEGORIES = [
    "Pulses / grains",
    "Warehouse space",
    "Grocery",
    "Spices",
    "Organic products",
    "B2B service",
    "Other",
]

TARGET_AUDIENCES = [
    "B2B buyers: wholesalers, supermarkets, distributors",
    "B2C consumers: families and direct buyers",
    "Corporate buyers: warehouse and logistics teams",
    "Retailers and small shops",
]

VIDEO_FORMATS = {
    "Instagram Reels / YouTube Shorts - 9:16": {"size": (1080, 1920), "duration": 30},
    "WhatsApp Status - 9:16": {"size": (1080, 1920), "duration": 20},
    "Instagram Square - 1:1": {"size": (1080, 1080), "duration": 20},
    "Facebook Feed - 16:9": {"size": (1280, 720), "duration": 30},
}

POSTER_FORMATS = {
    "Instagram Square - 1080x1080": (1080, 1080),
    "Instagram Story / WhatsApp Status - 1080x1920": (1080, 1920),
    "Facebook Feed - 1200x628": (1200, 628),
    "LinkedIn Feed - 1200x1200": (1200, 1200),
}


st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
        .main .block-container { padding-top: 2rem; max-width: 1180px; }
        .stButton > button { border-radius: 6px; font-weight: 700; }
        .metric-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            background: #ffffff;
        }
        .small-muted { color: #6b7280; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def secret_value(name: str, default: Any = None) -> Any:
    """Read from Streamlit secrets first, then environment variables."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


def resolve_model_name(raw_model: Any) -> Tuple[str, str]:
    model = str(raw_model or DEFAULT_MODEL).strip()
    if model.startswith("models/"):
        model = model.split("/", 1)[1]

    if "robotics" in model.lower():
        return DEFAULT_MODEL, (
            "Robotics models are not suitable for this marketing app. "
            f"Using {DEFAULT_MODEL} instead."
        )

    if not model:
        return DEFAULT_MODEL, ""

    return model, ""


def normalize_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    else:
        value = dict(value)
    if "private_key" in value and isinstance(value["private_key"], str):
        value["private_key"] = value["private_key"].replace("\\n", "\n")
    return value


def get_service_account_info() -> Dict[str, Any]:
    try:
        if "GOOGLE_SERVICE_ACCOUNT" in st.secrets:
            return normalize_mapping(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    except Exception:
        pass

    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        return normalize_mapping(raw_json)

    return {}


def build_drive_service(service_account_info: Dict[str, Any]):
    if not service_account_info:
        return None
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=credentials)


def prepare_image(image: Image.Image, max_side: int = 1600) -> Image.Image:
    prepared = ImageOps.exif_transpose(image).convert("RGB")
    prepared.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return prepared


def build_prompt(product_name: str, category: str, audience: str, details: str) -> str:
    return f"""
You are a senior social media marketer for Indian MSME, warehouse, grocery,
agriculture, and B2B product brands.

Analyze the uploaded product or warehouse image and create a practical campaign
that can be posted today.

Product name: {product_name}
Category: {category}
Target audience: {audience}
Additional details: {details or "None"}

Return only valid JSON with these exact keys:
headline, narration_script, poster_main_text, poster_tagline, poster_cta,
linkedin_post, instagram_caption, facebook_post, whatsapp_message,
hashtags, image_observations.

Rules:
- Keep claims believable and do not invent certifications, prices, or stock.
- Use clear Indian English.
- Make LinkedIn B2B focused.
- Make Instagram short, energetic, and hashtag ready.
- Make WhatsApp direct and sales oriented.
- Keep poster_main_text under 9 words and poster_cta under 3 words.
- hashtags must be an array of 8 to 12 strings.
"""


def parse_campaign(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            data = {}

    defaults = {
        "headline": "Fresh quality, ready for your market",
        "narration_script": raw_text[:900] or "Promote your product with Samketan.",
        "poster_main_text": "Premium quality",
        "poster_tagline": "Trusted supply",
        "poster_cta": "Order now",
        "linkedin_post": raw_text,
        "instagram_caption": raw_text,
        "facebook_post": raw_text,
        "whatsapp_message": raw_text[:240],
        "hashtags": ["#Samketan", "#IndianBusiness", "#QualityProducts"],
        "image_observations": "Generated from the uploaded image.",
    }

    if not isinstance(data, dict):
        data = {}

    for key, value in defaults.items():
        if not data.get(key):
            data[key] = value

    if isinstance(data["hashtags"], str):
        data["hashtags"] = [tag.strip() for tag in data["hashtags"].split() if tag.strip()]

    return data


def generate_campaign(
    api_key: str,
    model_name: str,
    product_name: str,
    category: str,
    audience: str,
    details: str,
    image: Image.Image,
) -> Dict[str, Any]:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=[build_prompt(product_name, category, audience, details), prepare_image(image)],
    )
    text = getattr(response, "text", "") or ""
    if not text:
        raise RuntimeError("Gemini returned an empty response. Try again with a clearer image.")
    data = parse_campaign(text)
    data["_raw"] = text
    data["_model"] = model_name
    return data


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "samketan_campaign"


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    words = str(text).split()
    if not words:
        return ""

    lines = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        if text_size(draw, test, font)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines)


def draw_centered_multiline(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    max_width: int,
    line_gap: int = 10,
) -> int:
    wrapped = wrap_text(draw, text, font, max_width)
    lines = wrapped.splitlines() or [""]
    x, y = xy
    total_height = sum(text_size(draw, line, font)[1] for line in lines) + line_gap * (len(lines) - 1)
    cursor = y - total_height // 2
    for line in lines:
        width, height = text_size(draw, line, font)
        draw.text((x - width // 2, cursor), line, font=font, fill=fill)
        cursor += height + line_gap
    return cursor


def make_poster(
    image: Image.Image,
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    accent: str,
    text_color: str,
) -> Image.Image:
    width, height = size
    base = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), size, method=Image.Resampling.LANCZOS)
    base = ImageEnhance.Contrast(base).enhance(1.05)

    overlay = Image.new("RGBA", size, (0, 0, 0, 110))
    poster = Image.alpha_composite(base.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(poster)

    accent_rgb = tuple(int(accent.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    text_rgb = tuple(int(text_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    margin = max(40, width // 18)
    title_font = get_font(max(44, width // 12), bold=True)
    tagline_font = get_font(max(28, width // 28))
    cta_font = get_font(max(24, width // 32), bold=True)
    brand_font = get_font(max(20, width // 44), bold=True)

    draw.rounded_rectangle(
        (margin, margin, margin + max(220, width // 4), margin + 54),
        radius=8,
        fill=(255, 255, 255, 225),
    )
    draw.text((margin + 20, margin + 16), "SAMKETAN", font=brand_font, fill=(20, 25, 35))

    draw_centered_multiline(
        draw,
        (width // 2, height // 2 - height // 12),
        campaign["poster_main_text"],
        title_font,
        text_rgb,
        width - margin * 2,
        line_gap=max(8, width // 90),
    )

    tagline = campaign.get("poster_tagline", "")
    tag_w, tag_h = text_size(draw, tagline, tagline_font)
    tag_y = height // 2 + height // 10
    draw.rounded_rectangle(
        (
            width // 2 - tag_w // 2 - 28,
            tag_y - 14,
            width // 2 + tag_w // 2 + 28,
            tag_y + tag_h + 18,
        ),
        radius=8,
        fill=accent_rgb + (230,),
    )
    draw.text((width // 2 - tag_w // 2, tag_y), tagline, font=tagline_font, fill=(255, 255, 255))

    cta = campaign.get("poster_cta", "Order now")
    cta_w, cta_h = text_size(draw, cta, cta_font)
    cta_y = height - margin - 78
    draw.rounded_rectangle(
        (
            width // 2 - cta_w // 2 - 42,
            cta_y,
            width // 2 + cta_w // 2 + 42,
            cta_y + cta_h + 34,
        ),
        radius=8,
        fill=(255, 255, 255, 238),
    )
    draw.text((width // 2 - cta_w // 2, cta_y + 17), cta, font=cta_font, fill=accent_rgb)

    return poster.convert("RGB")


def make_video_frame(
    image: Image.Image,
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    accent: str,
) -> Image.Image:
    width, height = size
    frame = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), size, method=Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", size, (0, 0, 0, 70))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(frame)

    accent_rgb = tuple(int(accent.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    title_font = get_font(max(42, width // 16), bold=True)
    small_font = get_font(max(22, width // 45), bold=True)
    margin = max(36, width // 22)

    band_height = max(250, height // 5)
    draw.rectangle((0, height - band_height, width, height), fill=(0, 0, 0, 178))
    draw.rectangle((0, height - band_height, 12, height), fill=accent_rgb + (255,))

    headline = campaign.get("headline") or campaign.get("poster_main_text") or "Samketan"
    draw_centered_multiline(
        draw,
        (width // 2, height - band_height // 2 - 10),
        headline,
        title_font,
        (255, 255, 255),
        width - margin * 2,
        line_gap=8,
    )

    footer = "Samketan Marketing Factory"
    footer_w, footer_h = text_size(draw, footer, small_font)
    draw.rounded_rectangle((margin, margin, margin + footer_w + 30, margin + footer_h + 22), radius=8, fill=(255, 255, 255, 220))
    draw.text((margin + 15, margin + 11), footer, font=small_font, fill=(20, 25, 35))
    return frame.convert("RGB")


def create_tts_audio(narration: str, service_account_info: Dict[str, Any], speed: float) -> Optional[str]:
    if not service_account_info:
        return None

    from google.cloud import texttospeech

    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    client = texttospeech.TextToSpeechClient(credentials=credentials)

    synthesis_input = texttospeech.SynthesisInput(text=narration[:4500])
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-IN",
        name="en-IN-Neural2-A",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=float(speed),
    )

    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    audio_file.write(response.audio_content)
    audio_file.close()
    return audio_file.name


def create_video(
    image: Image.Image,
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    duration: int,
    accent: str,
    audio_path: Optional[str],
) -> str:
    from moviepy.editor import AudioFileClip, ImageClip

    frame = make_video_frame(image, campaign, size, accent)
    frame_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    frame_path = frame_file.name
    frame_file.close()
    frame.save(frame_path)

    clip_duration = duration
    audio_clip = None
    if audio_path:
        audio_clip = AudioFileClip(audio_path)
        clip_duration = max(4, audio_clip.duration)

    video_clip = ImageClip(frame_path).set_duration(clip_duration)
    if audio_clip:
        video_clip = video_clip.set_audio(audio_clip)

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    output.close()
    video_clip.write_videofile(
        output.name,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        verbose=False,
        logger=None,
    )

    video_clip.close()
    if audio_clip:
        audio_clip.close()
    return output.name


def campaign_text(campaign: Dict[str, Any], product_name: str) -> str:
    hashtags = " ".join(campaign.get("hashtags", []))
    return f"""Campaign: {product_name}
Model: {campaign.get("_model", DEFAULT_MODEL)}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Headline:
{campaign.get("headline", "")}

Narration Script:
{campaign.get("narration_script", "")}

Poster:
Main text: {campaign.get("poster_main_text", "")}
Tagline: {campaign.get("poster_tagline", "")}
CTA: {campaign.get("poster_cta", "")}

LinkedIn:
{campaign.get("linkedin_post", "")}

Instagram:
{campaign.get("instagram_caption", "")}

Facebook:
{campaign.get("facebook_post", "")}

WhatsApp:
{campaign.get("whatsapp_message", "")}

Hashtags:
{hashtags}

Image observations:
{campaign.get("image_observations", "")}
"""


def upload_text_file(drive_service, folder_id: str, name: str, text: str) -> None:
    temp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8")
    temp.write(text)
    temp.close()
    metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(temp.name, mimetype="text/plain")
    drive_service.files().create(body=metadata, media_body=media, fields="id").execute()


def upload_binary_file(drive_service, folder_id: str, name: str, path: str, mimetype: str) -> None:
    metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(path, mimetype=mimetype)
    drive_service.files().create(body=metadata, media_body=media, fields="id").execute()


def social_text_area(label: str, value: str, height: int = 170) -> None:
    st.text_area(label, value=value, height=height, disabled=True)


gemini_key = secret_value("GEMINI_API_KEY", "")
model_name, model_warning = resolve_model_name(secret_value("GEMINI_MODEL", DEFAULT_MODEL))
service_account_info = get_service_account_info()

try:
    drive_service = build_drive_service(service_account_info)
    drive_error = ""
except Exception as exc:
    drive_service = None
    drive_error = str(exc)


with st.sidebar:
    st.header("Configuration")

    if gemini_key:
        st.success("Gemini API key loaded")
    else:
        gemini_key = st.text_input("Gemini API key", type="password")

    requested_model = st.text_input("Gemini model", value=model_name, help="Default: gemini-3.5-flash")
    model_name, sidebar_model_warning = resolve_model_name(requested_model)
    if model_warning or sidebar_model_warning:
        st.warning(model_warning or sidebar_model_warning)
    st.caption("Avoid robotics preview models for marketing copy. Use a stable Gemini text/vision model.")

    st.divider()
    st.subheader("Google services")
    if drive_service:
        st.success("Google Drive upload ready")
        st.caption("The same service account can be used for Google Cloud Text-to-Speech.")
    elif drive_error:
        st.warning(f"Google service setup failed: {drive_error[:140]}")
    else:
        st.info("Add GOOGLE_SERVICE_ACCOUNT in Streamlit Secrets for Drive upload and narration.")

    st.divider()
    st.subheader("Image")
    uploaded_file = st.file_uploader(
        "Upload product or warehouse photo",
        type=["jpg", "jpeg", "png", "webp"],
        help="Use a clear, well-lit image for best output.",
    )

    uploaded_image = None
    if uploaded_file:
        uploaded_image = Image.open(uploaded_file)
        st.image(uploaded_image, caption="Preview", use_container_width=True)


st.title(APP_NAME)
st.caption("Upload one image, generate ready-to-post campaigns for LinkedIn, Instagram, Facebook, and WhatsApp.")

tabs = st.tabs(["Campaign", "Video", "Poster", "Social and Drive"])

with tabs[0]:
    st.header("Create Campaign")

    col_a, col_b = st.columns(2)
    with col_a:
        product_name = st.text_input("Product name", placeholder="Example: Premium Toor Dal from Kalaburagi")
        category = st.selectbox("Product category", CATEGORIES)
    with col_b:
        audience = st.selectbox("Target audience", TARGET_AUDIENCES)
        tone = st.selectbox("Campaign tone", ["Trust-building", "Premium", "Festival sale", "Bulk order", "Local brand"])

    details = st.text_area(
        "Extra details",
        placeholder="Add quality points, location, offer, minimum order, delivery area, phone number, or website.",
        height=110,
    )

    if tone and tone not in details:
        details_for_prompt = f"{details}\nPreferred tone: {tone}".strip()
    else:
        details_for_prompt = details

    can_generate = bool(gemini_key and uploaded_image and product_name)
    if st.button("Generate marketing campaign", type="primary", use_container_width=True, disabled=not can_generate):
        with st.spinner("Generating campaign with Gemini..."):
            try:
                campaign = generate_campaign(
                    api_key=gemini_key,
                    model_name=model_name,
                    product_name=product_name,
                    category=category,
                    audience=audience,
                    details=details_for_prompt,
                    image=uploaded_image,
                )
                st.session_state.campaign = campaign
                st.session_state.product_name = product_name
                st.session_state.uploaded_image = uploaded_image.copy()
                st.success("Campaign generated.")
            except Exception as exc:
                st.error(f"Campaign generation failed: {exc}")
                st.info("Use a current model such as gemini-3.5-flash and confirm your GEMINI_API_KEY is valid.")

    if not can_generate:
        missing = []
        if not gemini_key:
            missing.append("Gemini API key")
        if not uploaded_image:
            missing.append("product image")
        if not product_name:
            missing.append("product name")
        st.info("Add " + ", ".join(missing) + " to generate a campaign.")

    if "campaign" in st.session_state:
        campaign = st.session_state.campaign
        st.subheader(campaign.get("headline", "Campaign"))
        st.write(campaign.get("image_observations", ""))

        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-card'><b>Model</b><br>{campaign.get('_model', model_name)}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><b>Poster CTA</b><br>{campaign.get('poster_cta', '')}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><b>Hashtags</b><br>{len(campaign.get('hashtags', []))}</div>", unsafe_allow_html=True)

        st.subheader("Narration Script")
        st.write(campaign.get("narration_script", ""))

with tabs[1]:
    st.header("Create Video")

    if "campaign" not in st.session_state:
        st.info("Generate a campaign first.")
    else:
        campaign = st.session_state.campaign
        image = st.session_state.uploaded_image

        col_a, col_b = st.columns(2)
        with col_a:
            video_choice = st.selectbox("Video format", list(VIDEO_FORMATS.keys()))
            speed = st.slider("Narration speed", 0.85, 1.25, 1.0, 0.05)
        with col_b:
            accent = st.color_picker("Accent color", "#0f766e")
            include_tts = st.checkbox("Add Google Cloud narration when service account is available", value=True)

        if st.button("Generate video", type="primary", use_container_width=True):
            with st.spinner("Building video..."):
                try:
                    config = VIDEO_FORMATS[video_choice]
                    audio_path = None
                    if include_tts:
                        try:
                            audio_path = create_tts_audio(campaign["narration_script"], service_account_info, speed)
                            if audio_path:
                                st.success("Narration audio generated.")
                            else:
                                st.warning("No service account found, so a silent video will be created.")
                        except Exception as exc:
                            st.warning(f"Narration unavailable, creating silent video: {exc}")

                    video_path = create_video(
                        image=image,
                        campaign=campaign,
                        size=config["size"],
                        duration=config["duration"],
                        accent=accent,
                        audio_path=audio_path,
                    )
                    st.session_state.video_path = video_path
                    with open(video_path, "rb") as handle:
                        video_bytes = handle.read()
                    st.video(video_bytes)
                    st.download_button(
                        "Download video",
                        data=video_bytes,
                        file_name=f"{safe_filename(st.session_state.product_name)}_video.mp4",
                        mime="video/mp4",
                    )
                except Exception as exc:
                    st.error(f"Video generation failed: {exc}")
                    st.info("Streamlit Cloud needs ffmpeg in packages.txt and moviepy in requirements.txt.")

with tabs[2]:
    st.header("Create Poster")

    if "campaign" not in st.session_state:
        st.info("Generate a campaign first.")
    else:
        campaign = st.session_state.campaign
        image = st.session_state.uploaded_image

        col_a, col_b = st.columns(2)
        with col_a:
            poster_choice = st.selectbox("Poster format", list(POSTER_FORMATS.keys()))
        with col_b:
            accent = st.color_picker("Poster accent", "#0f766e")
            text_color = st.color_picker("Poster text", "#ffffff")

        if st.button("Generate poster", type="primary", use_container_width=True):
            with st.spinner("Designing poster..."):
                try:
                    poster = make_poster(image, campaign, POSTER_FORMATS[poster_choice], accent, text_color)
                    st.session_state.poster = poster
                    st.image(poster, use_container_width=True)

                    poster_buffer = io.BytesIO()
                    poster.save(poster_buffer, format="PNG")
                    poster_buffer.seek(0)
                    st.download_button(
                        "Download poster",
                        data=poster_buffer,
                        file_name=f"{safe_filename(st.session_state.product_name)}_poster.png",
                        mime="image/png",
                    )
                except Exception as exc:
                    st.error(f"Poster generation failed: {exc}")

with tabs[3]:
    st.header("Social Copy and Drive")

    if "campaign" not in st.session_state:
        st.info("Generate a campaign first.")
    else:
        campaign = st.session_state.campaign
        product_name = st.session_state.product_name
        full_text = campaign_text(campaign, product_name)

        col_a, col_b = st.columns(2)
        with col_a:
            social_text_area("LinkedIn", campaign.get("linkedin_post", ""))
            linkedin_url = "https://www.linkedin.com/feed/"
            st.link_button("Open LinkedIn", linkedin_url)
        with col_b:
            instagram_caption = campaign.get("instagram_caption", "")
            hashtags = " ".join(campaign.get("hashtags", []))
            social_text_area("Instagram", f"{instagram_caption}\n\n{hashtags}")
            st.link_button("Open Instagram", "https://www.instagram.com/")

        col_c, col_d = st.columns(2)
        with col_c:
            social_text_area("Facebook", campaign.get("facebook_post", ""))
            st.link_button("Open Facebook", "https://www.facebook.com/")
        with col_d:
            whatsapp_message = campaign.get("whatsapp_message", "")
            social_text_area("WhatsApp", whatsapp_message)
            st.link_button("Open WhatsApp", f"https://wa.me/?text={quote(whatsapp_message)}")

        st.download_button(
            "Download campaign text",
            data=full_text.encode("utf-8"),
            file_name=f"{safe_filename(product_name)}_campaign.txt",
            mime="text/plain",
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as package:
            package.writestr(f"{safe_filename(product_name)}_campaign.txt", full_text)
            if "poster" in st.session_state:
                poster_buffer = io.BytesIO()
                st.session_state.poster.save(poster_buffer, format="PNG")
                package.writestr(f"{safe_filename(product_name)}_poster.png", poster_buffer.getvalue())
            if "video_path" in st.session_state:
                with open(st.session_state.video_path, "rb") as handle:
                    package.writestr(f"{safe_filename(product_name)}_video.mp4", handle.read())
        zip_buffer.seek(0)

        st.download_button(
            "Download full package",
            data=zip_buffer,
            file_name=f"{safe_filename(product_name)}_package.zip",
            mime="application/zip",
            type="primary",
        )

        st.divider()
        st.subheader("Upload to Google Drive")

        if not drive_service:
            st.info("Add GOOGLE_SERVICE_ACCOUNT to Streamlit Secrets to enable Drive upload.")
        else:
            folder_name = st.text_input("Drive folder name", value=f"{safe_filename(product_name)}_{datetime.now().strftime('%Y%m%d')}")
            if st.button("Upload campaign package to Drive", use_container_width=True):
                with st.spinner("Uploading to Google Drive..."):
                    try:
                        folder_metadata = {
                            "name": folder_name,
                            "mimeType": "application/vnd.google-apps.folder",
                        }
                        folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
                        folder_id = folder["id"]

                        upload_text_file(drive_service, folder_id, f"{folder_name}_campaign.txt", full_text)

                        uploaded = ["campaign text"]
                        if "poster" in st.session_state:
                            poster_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            poster_temp_path = poster_temp.name
                            poster_temp.close()
                            st.session_state.poster.save(poster_temp_path)
                            upload_binary_file(drive_service, folder_id, f"{folder_name}_poster.png", poster_temp_path, "image/png")
                            uploaded.append("poster")

                        if "video_path" in st.session_state:
                            upload_binary_file(drive_service, folder_id, f"{folder_name}_video.mp4", st.session_state.video_path, "video/mp4")
                            uploaded.append("video")

                        st.success(f"Uploaded: {', '.join(uploaded)}")
                        st.link_button("Open Drive folder", f"https://drive.google.com/drive/folders/{folder_id}")
                    except Exception as exc:
                        st.error(f"Drive upload failed: {exc}")

st.divider()
st.caption("Built for Samketan. Use stable Gemini models for production; preview and robotics models can be retired without long notice.")
