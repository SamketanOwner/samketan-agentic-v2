"""
Samketan Marketing Factory — Business Marketing Kit

Streamlit app for creating a complete marketing kit from business details:
- Logo + 3-4 product/warehouse photos
- Campaign poster
- Social media video
- Event invitation & proceedings
- Achievements showcase
- Social promotion links (Instagram, Facebook, LinkedIn, WhatsApp)
- Optional Google Drive upload
"""

import io
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
    "Pulses / Grains",
    "Warehouse Space",
    "Grocery",
    "Spices",
    "Organic Products",
    "B2B Service",
    "Manufacturing",
    "Logistics",
    "Other",
]

TARGET_AUDIENCES = [
    "B2B buyers: wholesalers, supermarkets, distributors",
    "B2C consumers: families and direct buyers",
    "Corporate buyers: warehouse and logistics teams",
    "Retailers and small shops",
    "Export / International buyers",
]

EVENT_TYPES = [
    "Product Launch",
    "Warehouse Opening",
    "Annual Meet",
    "Festival Sale",
    "B2B Expo / Trade Fair",
    "Achievement Celebration",
    "Other",
]

VIDEO_FORMATS = {
    "Instagram Reels / YouTube Shorts - 9:16": {"size": (1080, 1920), "duration": 30},
    "WhatsApp Status - 9:16": {"size": (1080, 1920), "duration": 20},
    "Instagram Square - 1:1": {"size": (1080, 1080), "duration": 20},
    "Facebook Feed - 16:9": {"size": (1280, 720), "duration": 30},
    "LinkedIn Feed - 1:1": {"size": (1080, 1080), "duration": 25},
}

POSTER_FORMATS = {
    "Instagram Square - 1080x1080": (1080, 1080),
    "Instagram Story / WhatsApp Status - 1080x1920": (1080, 1920),
    "Facebook Feed - 1200x628": (1200, 628),
    "LinkedIn Feed - 1200x1200": (1200, 1200),
}

INVITATION_FORMATS = {
    "Instagram Square - 1080x1080": (1080, 1080),
    "Instagram Story / WhatsApp Status - 1080x1920": (1080, 1920),
    "Print A5 - 148x210mm (1748x2480)": (1748, 2480),
}

st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
        .main .block-container { padding-top: 2rem; max-width: 1280px; }
        .stButton > button { border-radius: 6px; font-weight: 700; }
        .metric-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            background: #ffffff;
        }
        .small-muted { color: #6b7280; font-size: 0.9rem; }
        .social-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin: 4px;
            transition: opacity 0.2s;
        }
        .social-btn:hover { opacity: 0.85; }
        .instagram { background: #E4405F; color: white; }
        .facebook { background: #1877F2; color: white; }
        .linkedin { background: #0A66C2; color: white; }
        .whatsapp { background: #25D366; color: white; }
        .info-box {
            background: #f0f9ff;
            border-left: 4px solid #0ea5e9;
            padding: 12px 16px;
            border-radius: 4px;
            margin: 8px 0;
        }
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


def build_prompt(
    business_name: str,
    product_name: str,
    category: str,
    audience: str,
    details: str,
    tone: str,
    event_type: str,
    event_details: str,
    achievements: str,
) -> str:
    return f"""You are a senior social media marketer for Indian MSME, warehouse, grocery, agriculture, and B2B product brands.

Analyze the uploaded product/warehouse photos and logo to create a practical, ready-to-post marketing campaign.

Business name: {business_name}
Product name: {product_name}
Category: {category}
Target audience: {audience}
Campaign tone: {tone}
Additional details: {details or "None"}

Event type: {event_type or "None"}
Event details: {event_details or "None"}

Recent achievements: {achievements or "None"}

Return only valid JSON with these exact keys:
headline, narration_script, poster_main_text, poster_tagline, poster_cta,
linkedin_post, instagram_caption, facebook_post, whatsapp_message,
invitation_title, invitation_body, invitation_venue, invitation_date_time,
proceedings_intro, proceedings_highlights, proceedings_closing,
achievement_summary, achievement_social_post,
hashtags, image_observations.

Rules:
- Keep claims believable and do not invent certifications, prices, or stock.
- Use clear Indian English.
- Make LinkedIn B2B focused.
- Make Instagram short, energetic, and hashtag ready.
- Make WhatsApp direct and sales oriented.
- Keep poster_main_text under 9 words and poster_cta under 3 words.
- invitation_title under 6 words, invitation_body under 40 words.
- proceedings_highlights should be a list of 3-5 short strings.
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
        "invitation_title": "You are invited",
        "invitation_body": "Join us for an exclusive event.",
        "invitation_venue": "",
        "invitation_date_time": "",
        "proceedings_intro": "Welcome to our event proceedings.",
        "proceedings_highlights": ["Keynote speech", "Product showcase", "Networking"],
        "proceedings_closing": "Thank you for joining us.",
        "achievement_summary": "We are proud of our recent milestones.",
        "achievement_social_post": "Exciting news from our team!",
        "hashtags": ["#Samketan", "#IndianBusiness", "#QualityProducts"],
        "image_observations": "Generated from the uploaded images.",
    }

    if not isinstance(data, dict):
        data = {}

    for key, value in defaults.items():
        if not data.get(key):
            data[key] = value

    if isinstance(data["hashtags"], str):
        data["hashtags"] = [tag.strip() for tag in data["hashtags"].split() if tag.strip()]

    if isinstance(data["proceedings_highlights"], str):
        data["proceedings_highlights"] = [h.strip() for h in data["proceedings_highlights"].split("\n") if h.strip()]

    return data


def generate_campaign(
    api_key: str,
    model_name: str,
    business_name: str,
    product_name: str,
    category: str,
    audience: str,
    details: str,
    tone: str,
    event_type: str,
    event_details: str,
    achievements: str,
    images: List[Image.Image],
) -> Dict[str, Any]:
    client = genai.Client(api_key=api_key)
    prompt = build_prompt(business_name, product_name, category, audience, details, tone, event_type, event_details, achievements)
    contents = [prompt] + [prepare_image(img) for img in images]
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
    )
    text = getattr(response, "text", "") or ""
    if not text:
        raise RuntimeError("Gemini returned an empty response. Try again with clearer images.")
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


def overlay_logo(base_image: Image.Image, logo: Optional[Image.Image], position: str = "top-left") -> Image.Image:
    if logo is None:
        return base_image

    img = base_image.copy().convert("RGBA")
    logo_rgba = ImageOps.exif_transpose(logo).convert("RGBA")

    # Resize logo to max 15% of image width
    max_logo_width = max(80, img.width // 7)
    ratio = max_logo_width / logo_rgba.width
    new_size = (max_logo_width, int(logo_rgba.height * ratio))
    logo_rgba = logo_rgba.resize(new_size, Image.Resampling.LANCZOS)

    margin = max(20, img.width // 40)

    if position == "top-left":
        pos = (margin, margin)
    elif position == "top-right":
        pos = (img.width - logo_rgba.width - margin, margin)
    elif position == "bottom-left":
        pos = (margin, img.height - logo_rgba.height - margin)
    else:  # bottom-right
        pos = (img.width - logo_rgba.width - margin, img.height - logo_rgba.height - margin)

    img.paste(logo_rgba, pos, logo_rgba)
    return img


def make_poster(
    image: Image.Image,
    logo: Optional[Image.Image],
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

    # Add logo
    poster = overlay_logo(poster, logo, position="top-right")

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


def make_invitation(
    image: Image.Image,
    logo: Optional[Image.Image],
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    accent: str,
    text_color: str,
) -> Image.Image:
    width, height = size
    base = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), size, method=Image.Resampling.LANCZOS)
    base = ImageEnhance.Brightness(base).enhance(0.6)

    overlay = Image.new("RGBA", size, (0, 0, 0, 140))
    card = Image.alpha_composite(base.convert("RGBA"), overlay)

    # Add logo
    card = overlay_logo(card, logo, position="top-left")

    draw = ImageDraw.Draw(card)

    accent_rgb = tuple(int(accent.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    text_rgb = tuple(int(text_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    margin = max(50, width // 14)
    title_font = get_font(max(52, width // 10), bold=True)
    body_font = get_font(max(26, width // 32))
    detail_font = get_font(max(22, width // 40))
    small_font = get_font(max(18, width // 50))

    # Decorative top line
    draw.rectangle((margin, margin + 80, width - margin, margin + 84), fill=accent_rgb + (255,))

    # Title
    title = campaign.get("invitation_title", "You are invited")
    draw_centered_multiline(
        draw,
        (width // 2, height // 3 - 20),
        title,
        title_font,
        text_rgb,
        width - margin * 2,
        line_gap=10,
    )

    # Body
    body = campaign.get("invitation_body", "Join us for an exclusive event.")
    draw_centered_multiline(
        draw,
        (width // 2, height // 2 + 20),
        body,
        body_font,
        (220, 220, 220),
        width - margin * 2,
        line_gap=8,
    )

    # Venue & Date
    venue = campaign.get("invitation_venue", "")
    date_time = campaign.get("invitation_date_time", "")
    details_text = ""
    if venue:
        details_text += f"📍 {venue}"
    if date_time:
        details_text += f"\n📅 {date_time}" if details_text else f"📅 {date_time}"

    if details_text:
        draw_centered_multiline(
            draw,
            (width // 2, height // 2 + height // 5),
            details_text,
            detail_font,
            accent_rgb,
            width - margin * 2,
            line_gap=6,
        )

    # Bottom branding
    brand = campaign.get("business_name", "Samketan Marketing Factory")
    footer_w, footer_h = text_size(draw, brand, small_font)
    draw.rounded_rectangle(
        (width // 2 - footer_w // 2 - 20, height - margin - 50, width // 2 + footer_w // 2 + 20, height - margin - 20),
        radius=6,
        fill=accent_rgb + (200,),
    )
    draw.text((width // 2 - footer_w // 2, height - margin - 46), brand, font=small_font, fill=(255, 255, 255))

    return card.convert("RGB")


def make_proceedings(
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    accent: str,
    text_color: str,
) -> Image.Image:
    width, height = size
    # Create a clean proceedings card
    card = Image.new("RGB", size, (250, 250, 250))
    draw = ImageDraw.Draw(card)

    accent_rgb = tuple(int(accent.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    text_rgb = tuple(int(text_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    margin = max(60, width // 14)
    header_font = get_font(max(48, width // 12), bold=True)
    body_font = get_font(max(26, width // 32))
    item_font = get_font(max(24, width // 36))
    small_font = get_font(max(18, width // 50))

    # Header bar
    draw.rectangle((0, 0, width, 12), fill=accent_rgb)

    # Title
    title = "Event Proceedings"
    draw_centered_multiline(
        draw,
        (width // 2, margin + 40),
        title,
        header_font,
        text_rgb,
        width - margin * 2,
        line_gap=10,
    )

    # Intro
    intro = campaign.get("proceedings_intro", "Welcome to our event proceedings.")
    draw_centered_multiline(
        draw,
        (width // 2, margin + 120),
        intro,
        body_font,
        (80, 80, 80),
        width - margin * 2,
        line_gap=8,
    )

    # Highlights
    highlights = campaign.get("proceedings_highlights", ["Keynote speech", "Product showcase", "Networking"])
    y_pos = margin + 200
    for i, highlight in enumerate(highlights):
        item_text = f"{i + 1}. {highlight}"
        draw.text((margin + 20, y_pos), item_text, font=item_font, fill=text_rgb)
        y_pos += text_size(draw, item_text, item_font)[1] + 16

    # Closing
    closing = campaign.get("proceedings_closing", "Thank you for joining us.")
    draw_centered_multiline(
        draw,
        (width // 2, height - margin - 60),
        closing,
        body_font,
        (80, 80, 80),
        width - margin * 2,
        line_gap=8,
    )

    # Footer
    brand = "Samketan Marketing Factory"
    footer_w, _ = text_size(draw, brand, small_font)
    draw.text((width // 2 - footer_w // 2, height - margin - 10), brand, font=small_font, fill=(150, 150, 150))

    return card


def make_achievement_card(
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    accent: str,
    text_color: str,
) -> Image.Image:
    width, height = size
    card = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(card)

    accent_rgb = tuple(int(accent.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    text_rgb = tuple(int(text_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    margin = max(60, width // 14)
    header_font = get_font(max(44, width // 12), bold=True)
    body_font = get_font(max(26, width // 32))
    small_font = get_font(max(18, width // 50))

    # Decorative header
    draw.rectangle((0, 0, width, 180), fill=accent_rgb)

    # Trophy icon placeholder (text)
    trophy_font = get_font(max(60, width // 14), bold=True)
    trophy_w, _ = text_size(draw, "🏆", trophy_font)
    draw.text((width // 2 - trophy_w // 2, 50), "🏆", font=trophy_font, fill=(255, 255, 255))

    # Title
    title = "Our Achievement"
    draw_centered_multiline(
        draw,
        (width // 2, 240),
        title,
        header_font,
        text_rgb,
        width - margin * 2,
        line_gap=10,
    )

    # Achievement summary
    summary = campaign.get("achievement_summary", "We are proud of our recent milestones.")
    draw_centered_multiline(
        draw,
        (width // 2, height // 2 + 20),
        summary,
        body_font,
        (60, 60, 60),
        width - margin * 2,
        line_gap=10,
    )

    # Social post preview
    social = campaign.get("achievement_social_post", "Exciting news from our team!")
    draw_centered_multiline(
        draw,
        (width // 2, height - margin - 80),
        f'"{social}"',
        small_font,
        (120, 120, 120),
        width - margin * 2,
        line_gap=6,
    )

    # Footer
    brand = "Samketan Marketing Factory"
    footer_w, _ = text_size(draw, brand, small_font)
    draw.text((width // 2 - footer_w // 2, height - margin - 10), brand, font=small_font, fill=(150, 150, 150))

    return card


def make_video_frame(
    image: Image.Image,
    logo: Optional[Image.Image],
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    accent: str,
) -> Image.Image:
    width, height = size
    frame = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), size, method=Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", size, (0, 0, 0, 70))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay)

    # Add logo
    frame = overlay_logo(frame, logo, position="top-right")

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
    logo: Optional[Image.Image],
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    duration: int,
    accent: str,
    audio_path: Optional[str],
) -> str:
    from moviepy.editor import AudioFileClip, ImageClip

    frame = make_video_frame(image, logo, campaign, size, accent)
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


def campaign_text(campaign: Dict[str, Any], product_name: str, business_name: str) -> str:
    hashtags = " ".join(campaign.get("hashtags", []))
    highlights = "\n".join(f"- {h}" for h in campaign.get("proceedings_highlights", []))
    return f"""Business: {business_name}
Campaign: {product_name}
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

Invitation:
Title: {campaign.get("invitation_title", "")}
Body: {campaign.get("invitation_body", "")}
Venue: {campaign.get("invitation_venue", "")}
Date/Time: {campaign.get("invitation_date_time", "")}

Proceedings:
Intro: {campaign.get("proceedings_intro", "")}
Highlights:
{highlights}
Closing: {campaign.get("proceedings_closing", "")}

Achievements:
Summary: {campaign.get("achievement_summary", "")}
Social Post: {campaign.get("achievement_social_post", "")}

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


def social_button_row(campaign: Dict[str, Any], instagram_url: str, facebook_url: str, linkedin_url: str, whatsapp_message: str):
    """Render social media promotion buttons."""
    linkedin_post = campaign.get("linkedin_post", "")
    instagram_caption = campaign.get("instagram_caption", "")
    facebook_post = campaign.get("facebook_post", "")
    hashtags = " ".join(campaign.get("hashtags", []))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if instagram_url and instagram_url.strip():
            st.markdown(f'<a href="{instagram_url}" target="_blank" class="social-btn instagram">📸 Open Instagram</a>', unsafe_allow_html=True)
        st.link_button("Open Instagram", "https://www.instagram.com/")
        st.caption("Paste caption manually")

    with col2:
        if facebook_url and facebook_url.strip():
            st.markdown(f'<a href="{facebook_url}" target="_blank" class="social-btn facebook">📘 Open Facebook</a>', unsafe_allow_html=True)
        st.link_button("Open Facebook", "https://www.facebook.com/")
        st.caption("Paste post manually")

    with col3:
        if linkedin_url and linkedin_url.strip():
            st.markdown(f'<a href="{linkedin_url}" target="_blank" class="social-btn linkedin">💼 Open LinkedIn</a>', unsafe_allow_html=True)
        st.link_button("Open LinkedIn", "https://www.linkedin.com/feed/")
        st.caption("Paste post manually")

    with col4:
        wa_link = f"https://wa.me/?text={quote(whatsapp_message[:500])}"
        st.markdown(f'<a href="{wa_link}" target="_blank" class="social-btn whatsapp">💬 Share on WhatsApp</a>', unsafe_allow_html=True)
        st.caption("Direct WhatsApp link")


# ─── Sidebar Configuration ───────────────────────────────────────────────────

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
    st.caption("Avoid robotics preview models. Use a stable Gemini text/vision model.")

    st.divider()
    st.subheader("Google services")
    if drive_service:
        st.success("Google Drive upload ready")
        st.caption("Service account active for Drive + Text-to-Speech.")
    elif drive_error:
        st.warning(f"Google service setup failed: {drive_error[:140]}")
    else:
        st.info("Add GOOGLE_SERVICE_ACCOUNT in Streamlit Secrets for Drive upload and narration.")

    st.divider()
    st.subheader("About Direct Posting")
    st.markdown("""
    <div class="info-box">
    <b>One-click posting</b> requires official API access for each platform:<br>
    • <b>Instagram:</b> Meta Graph API + Business Account<br>
    • <b>Facebook:</b> Meta Graph API + Page access<br>
    • <b>LinkedIn:</b> LinkedIn Marketing API + OAuth 2.0<br>
    • <b>WhatsApp:</b> WhatsApp Business API<br><br>
    This app provides <b>one-click open links</b> and <b>pre-written copy</b>.
    Background auto-posting needs separate API credentials.
    </div>
    """, unsafe_allow_html=True)


# ─── Main App ────────────────────────────────────────────────────────────────

st.title(APP_NAME)
st.caption("Upload your business details, logo, and photos. Generate posters, videos, invitations, and social copy.")

tabs = st.tabs([
    "🏢 Business Profile",
    "🎯 Campaign",
    "🎬 Video",
    "🖼️ Poster",
    "📨 Invitation & Proceedings",
    "🏆 Achievements",
    "📱 Social & Drive"
])


# ─── Tab 0: Business Profile ─────────────────────────────────────────────────

with tabs[0]:
    st.header("Business Profile")

    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business name *", placeholder="Example: Sri Lakshmi Agro Traders")
        product_name = st.text_input("Product / Service name *", placeholder="Example: Premium Toor Dal from Kalaburagi")
        category = st.selectbox("Product category", CATEGORIES)
    with col2:
        audience = st.selectbox("Target audience", TARGET_AUDIENCES)
        tone = st.selectbox("Campaign tone", ["Trust-building", "Premium", "Festival sale", "Bulk order", "Local brand", "Grand opening", "Achievement"])

    details = st.text_area(
        "Business details",
        placeholder="Add quality points, location, offer, minimum order, delivery area, phone number, website, or any special features.",
        height=110,
    )

    st.subheader("Visual Assets")
    col_logo, col_photos = st.columns(2)

    with col_logo:
        logo_file = st.file_uploader("Upload logo (optional)", type=["png", "jpg", "jpeg", "webp"], help="Transparent PNG works best")
        logo_image = None
        if logo_file:
            logo_image = Image.open(logo_file)
            st.image(logo_image, caption="Logo preview", use_container_width=True)

    with col_photos:
        photo_files = st.file_uploader(
            "Upload 3-4 product/warehouse photos *",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help="Upload clear, well-lit images for best output.",
        )
        uploaded_images = []
        if photo_files:
            for pf in photo_files[:4]:
                img = Image.open(pf)
                uploaded_images.append(img)
            st.image(uploaded_images[:3], caption=[f"Photo {i+1}" for i in range(min(len(uploaded_images), 3))], use_container_width=True)
            if len(uploaded_images) > 3:
                st.caption(f"...and {len(uploaded_images) - 3} more photo(s)")

    st.subheader("Event Details (Optional)")
    event_col1, event_col2 = st.columns(2)
    with event_col1:
        event_type = st.selectbox("Event type", ["None"] + EVENT_TYPES)
    with event_col2:
        event_date = st.date_input("Event date", value=None)
        event_time = st.time_input("Event time", value=None)

    event_venue = st.text_input("Event venue", placeholder="Example: Convention Center, Bangalore")
    event_details_text = st.text_area("Event description", placeholder="Describe the event purpose, special guests, or key activities.", height=80)

    st.subheader("Recent Achievements (Optional)")
    achievements = st.text_area(
        "Achievements / Milestones",
        placeholder="Example: Won Best Exporter Award 2025, Crossed 10,000 MT monthly dispatch, New ISO 22000 certification...",
        height=80,
    )

    st.subheader("Social Media Links")
    social_col1, social_col2 = st.columns(2)
    with social_col1:
        instagram_url = st.text_input("Instagram profile URL", placeholder="https://instagram.com/yourbusiness")
        facebook_url = st.text_input("Facebook page URL", placeholder="https://facebook.com/yourbusiness")
    with social_col2:
        linkedin_url = st.text_input("LinkedIn page URL", placeholder="https://linkedin.com/company/yourbusiness")
        whatsapp_number = st.text_input("WhatsApp business number", placeholder="+91 98765 43210")

    # Store in session state for other tabs
    if business_name:
        st.session_state.business_name = business_name
    if product_name:
        st.session_state.product_name = product_name
    if logo_image is not None:
        st.session_state.logo_image = logo_image
    if uploaded_images:
        st.session_state.uploaded_images = uploaded_images
    if event_type and event_type != "None":
        st.session_state.event_type = event_type
        st.session_state.event_details = event_details_text
        st.session_state.event_venue = event_venue
        dt_parts = []
        if event_date:
            dt_parts.append(event_date.strftime("%B %d, %Y"))
        if event_time:
            dt_parts.append(event_time.strftime("%I:%M %p"))
        st.session_state.event_date_time = " | ".join(dt_parts) if dt_parts else ""
    if achievements:
        st.session_state.achievements = achievements
    if instagram_url:
        st.session_state.instagram_url = instagram_url
    if facebook_url:
        st.session_state.facebook_url = facebook_url
    if linkedin_url:
        st.session_state.linkedin_url = linkedin_url
    if whatsapp_number:
        st.session_state.whatsapp_number = whatsapp_number

    tone_for_prompt = tone
    if tone and tone not in details:
        details_for_prompt = f"{details}\nPreferred tone: {tone}".strip()
    else:
        details_for_prompt = details

    can_generate = bool(gemini_key and uploaded_images and product_name and business_name)
    if st.button("Generate Marketing Kit", type="primary", use_container_width=True, disabled=not can_generate):
        with st.spinner("Generating complete marketing kit with Gemini..."):
            try:
                event_type_val = st.session_state.get("event_type", "")
                event_details_val = st.session_state.get("event_details", "")
                event_date_time_val = st.session_state.get("event_date_time", "")
                achievements_val = st.session_state.get("achievements", "")

                campaign = generate_campaign(
                    api_key=gemini_key,
                    model_name=model_name,
                    business_name=business_name,
                    product_name=product_name,
                    category=category,
                    audience=audience,
                    details=details_for_prompt,
                    tone=tone_for_prompt,
                    event_type=event_type_val,
                    event_details=f"{event_details_val}\nVenue: {st.session_state.get('event_venue', '')}\nDate/Time: {event_date_time_val}".strip(),
                    achievements=achievements_val,
                    images=uploaded_images,
                )
                # Inject business context
                campaign["business_name"] = business_name
                campaign["product_name"] = product_name
                st.session_state.campaign = campaign
                st.session_state.primary_image = uploaded_images[0].copy()
                st.success("Marketing kit generated successfully!")
            except Exception as exc:
                st.error(f"Campaign generation failed: {exc}")
                st.info("Use a current model such as gemini-3.5-flash and confirm your GEMINI_API_KEY is valid.")

    if not can_generate:
        missing = []
        if not gemini_key:
            missing.append("Gemini API key")
        if not uploaded_images:
            missing.append("3-4 product photos")
        if not business_name:
            missing.append("business name")
        if not product_name:
            missing.append("product name")
        st.info("Add " + ", ".join(missing) + " to generate the marketing kit.")


# ─── Tab 1: Campaign ───────────────────────────────────────────────────────────

with tabs[1]:
    st.header("Generated Campaign")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit from the Business Profile tab first.")
    else:
        campaign = st.session_state.campaign

        st.subheader(campaign.get("headline", "Campaign"))
        st.write(campaign.get("image_observations", ""))

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><b>Model</b><br>{campaign.get('_model', model_name)}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><b>Poster CTA</b><br>{campaign.get('poster_cta', '')}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><b>Hashtags</b><br>{len(campaign.get('hashtags', []))}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><b>Event</b><br>{st.session_state.get('event_type', 'None')}</div>", unsafe_allow_html=True)

        st.subheader("Narration Script")
        st.write(campaign.get("narration_script", ""))

        with st.expander("View all social copy"):
            social_text_area("LinkedIn Post", campaign.get("linkedin_post", ""))
            social_text_area("Instagram Caption", campaign.get("instagram_caption", ""))
            social_text_area("Facebook Post", campaign.get("facebook_post", ""))
            social_text_area("WhatsApp Message", campaign.get("whatsapp_message", ""))


# ─── Tab 2: Video ──────────────────────────────────────────────────────────────

with tabs[2]:
    st.header("Create Video")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit first.")
    else:
        campaign = st.session_state.campaign
        image = st.session_state.primary_image
        logo = st.session_state.get("logo_image")

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
                                st.warning("No service account found, creating silent video.")
                        except Exception as exc:
                            st.warning(f"Narration unavailable, creating silent video: {exc}")

                    video_path = create_video(
                        image=image,
                        logo=logo,
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


# ─── Tab 3: Poster ─────────────────────────────────────────────────────────────

with tabs[3]:
    st.header("Create Poster")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit first.")
    else:
        campaign = st.session_state.campaign
        image = st.session_state.primary_image
        logo = st.session_state.get("logo_image")

        col_a, col_b = st.columns(2)
        with col_a:
            poster_choice = st.selectbox("Poster format", list(POSTER_FORMATS.keys()))
        with col_b:
            accent = st.color_picker("Poster accent", "#0f766e")
            text_color = st.color_picker("Poster text", "#ffffff")

        if st.button("Generate poster", type="primary", use_container_width=True):
            with st.spinner("Designing poster..."):
                try:
                    poster = make_poster(image, logo, campaign, POSTER_FORMATS[poster_choice], accent, text_color)
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


# ─── Tab 4: Invitation & Proceedings ──────────────────────────────────────────

with tabs[4]:
    st.header("Event Invitation & Proceedings")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit first.")
    else:
        campaign = st.session_state.campaign
        image = st.session_state.primary_image
        logo = st.session_state.get("logo_image")

        has_event = bool(st.session_state.get("event_type") and st.session_state.get("event_type") != "None")

        if not has_event:
            st.warning("No event was specified in the Business Profile. The invitation will use generic event content.")

        st.subheader("Event Invitation Card")
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            invite_format = st.selectbox("Invitation format", list(INVITATION_FORMATS.keys()))
        with col_inv2:
            invite_accent = st.color_picker("Invitation accent", "#0f766e")
            invite_text = st.color_picker("Invitation text", "#ffffff")

        if st.button("Generate invitation card", type="primary", use_container_width=True):
            with st.spinner("Designing invitation..."):
                try:
                    invitation = make_invitation(image, logo, campaign, INVITATION_FORMATS[invite_format], invite_accent, invite_text)
                    st.session_state.invitation = invitation
                    st.image(invitation, use_container_width=True)

                    invite_buffer = io.BytesIO()
                    invitation.save(invite_buffer, format="PNG")
                    invite_buffer.seek(0)
                    st.download_button(
                        "Download invitation",
                        data=invite_buffer,
                        file_name=f"{safe_filename(st.session_state.product_name)}_invitation.png",
                        mime="image/png",
                    )
                except Exception as exc:
                    st.error(f"Invitation generation failed: {exc}")

        st.divider()
        st.subheader("Event Proceedings Document")

        proc_col1, proc_col2 = st.columns(2)
        with proc_col1:
            proc_format = st.selectbox("Proceedings format", ["Instagram Square - 1080x1080", "A4 Portrait - 2480x3508"])
        with proc_col2:
            proc_accent = st.color_picker("Proceedings accent", "#0f766e")
            proc_text = st.color_picker("Proceedings text", "#1f2937")

        proc_size = (1080, 1080) if "Square" in proc_format else (2480, 3508)

        if st.button("Generate proceedings", type="primary", use_container_width=True):
            with st.spinner("Creating proceedings..."):
                try:
                    proceedings = make_proceedings(campaign, proc_size, proc_accent, proc_text)
                    st.session_state.proceedings = proceedings
                    st.image(proceedings, use_container_width=True)

                    proc_buffer = io.BytesIO()
                    proceedings.save(proc_buffer, format="PNG")
                    proc_buffer.seek(0)
                    st.download_button(
                        "Download proceedings",
                        data=proc_buffer,
                        file_name=f"{safe_filename(st.session_state.product_name)}_proceedings.png",
                        mime="image/png",
                    )
                except Exception as exc:
                    st.error(f"Proceedings generation failed: {exc}")


# ─── Tab 5: Achievements ──────────────────────────────────────────────────────

with tabs[5]:
    st.header("Achievements Showcase")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit first.")
    else:
        campaign = st.session_state.campaign

        has_achievements = bool(st.session_state.get("achievements"))
        if not has_achievements:
            st.warning("No achievements were specified in the Business Profile. The card will use generic content.")

        ach_col1, ach_col2 = st.columns(2)
        with ach_col1:
            ach_format = st.selectbox("Achievement card format", ["Instagram Square - 1080x1080", "LinkedIn Feed - 1200x1200"])
        with ach_col2:
            ach_accent = st.color_picker("Achievement accent", "#d97706")
            ach_text = st.color_picker("Achievement text", "#1f2937")

        ach_size = (1080, 1080) if "Square" in ach_format else (1200, 1200)

        if st.button("Generate achievement card", type="primary", use_container_width=True):
            with st.spinner("Creating achievement showcase..."):
                try:
                    achievement_card = make_achievement_card(campaign, ach_size, ach_accent, ach_text)
                    st.session_state.achievement_card = achievement_card
                    st.image(achievement_card, use_container_width=True)

                    ach_buffer = io.BytesIO()
                    achievement_card.save(ach_buffer, format="PNG")
                    ach_buffer.seek(0)
                    st.download_button(
                        "Download achievement card",
                        data=ach_buffer,
                        file_name=f"{safe_filename(st.session_state.product_name)}_achievement.png",
                        mime="image/png",
                    )
                except Exception as exc:
                    st.error(f"Achievement card generation failed: {exc}")

        st.divider()
        st.subheader("Achievement Social Post")
        achievement_social = campaign.get("achievement_social_post", "Exciting news from our team!")
        social_text_area("Copy this for your social channels", achievement_social, height=120)


# ─── Tab 6: Social & Drive ───────────────────────────────────────────────────

with tabs[6]:
    st.header("Social Promotion & Drive Upload")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit first.")
    else:
        campaign = st.session_state.campaign
        product_name = st.session_state.product_name
        business_name = st.session_state.get("business_name", "")
        full_text = campaign_text(campaign, product_name, business_name)

        st.subheader("One-Click Social Links")

        instagram_url = st.session_state.get("instagram_url", "")
        facebook_url = st.session_state.get("facebook_url", "")
        linkedin_url = st.session_state.get("linkedin_url", "")
        whatsapp_message = campaign.get("whatsapp_message", "")

        social_button_row(campaign, instagram_url, facebook_url, linkedin_url, whatsapp_message)

        st.divider()
        st.subheader("Social Copy")

        col_a, col_b = st.columns(2)
        with col_a:
            social_text_area("LinkedIn", campaign.get("linkedin_post", ""))
            if linkedin_url:
                st.link_button("Open LinkedIn Page", linkedin_url)
        with col_b:
            instagram_caption = campaign.get("instagram_caption", "")
            hashtags = " ".join(campaign.get("hashtags", []))
            social_text_area("Instagram", f"{instagram_caption}\n\n{hashtags}")
            if instagram_url:
                st.link_button("Open Instagram Profile", instagram_url)

        col_c, col_d = st.columns(2)
        with col_c:
            social_text_area("Facebook", campaign.get("facebook_post", ""))
            if facebook_url:
                st.link_button("Open Facebook Page", facebook_url)
        with col_d:
            social_text_area("WhatsApp", whatsapp_message)
            wa_share = f"https://wa.me/?text={quote(whatsapp_message[:500])}"
            st.link_button("Share on WhatsApp", wa_share)

        st.divider()
        st.subheader("Downloads")

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
            if "invitation" in st.session_state:
                invite_buffer = io.BytesIO()
                st.session_state.invitation.save(invite_buffer, format="PNG")
                package.writestr(f"{safe_filename(product_name)}_invitation.png", invite_buffer.getvalue())
            if "proceedings" in st.session_state:
                proc_buffer = io.BytesIO()
                st.session_state.proceedings.save(proc_buffer, format="PNG")
                package.writestr(f"{safe_filename(product_name)}_proceedings.png", proc_buffer.getvalue())
            if "achievement_card" in st.session_state:
                ach_buffer = io.BytesIO()
                st.session_state.achievement_card.save(ach_buffer, format="PNG")
                package.writestr(f"{safe_filename(product_name)}_achievement.png", ach_buffer.getvalue())
        zip_buffer.seek(0)

        st.download_button(
            "Download full package (ZIP)",
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
            folder_name = st.text_input("Drive folder name", value=f"{safe_filename(business_name)}_{datetime.now().strftime('%Y%m%d')}")
            if st.button("Upload full package to Drive", use_container_width=True):
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

                        if "invitation" in st.session_state:
                            invite_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            invite_temp_path = invite_temp.name
                            invite_temp.close()
                            st.session_state.invitation.save(invite_temp_path)
                            upload_binary_file(drive_service, folder_id, f"{folder_name}_invitation.png", invite_temp_path, "image/png")
                            uploaded.append("invitation")

                        if "proceedings" in st.session_state:
                            proc_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            proc_temp_path = proc_temp.name
                            proc_temp.close()
                            st.session_state.proceedings.save(proc_temp_path)
                            upload_binary_file(drive_service, folder_id, f"{folder_name}_proceedings.png", proc_temp_path, "image/png")
                            uploaded.append("proceedings")

                        if "achievement_card" in st.session_state:
                            ach_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            ach_temp_path = ach_temp.name
                            ach_temp.close()
                            st.session_state.achievement_card.save(ach_temp_path)
                            upload_binary_file(drive_service, folder_id, f"{folder_name}_achievement.png", ach_temp_path, "image/png")
                            uploaded.append("achievement card")

                        st.success(f"Uploaded: {', '.join(uploaded)}")
                        st.link_button("Open Drive folder", f"https://drive.google.com/drive/folders/{folder_id}")
                    except Exception as exc:
                        st.error(f"Drive upload failed: {exc}")

st.divider()
st.caption("Built for Samketan. Use stable Gemini models for production; preview and robotics models can be retired without long notice.")
