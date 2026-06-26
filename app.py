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
import numpy as np
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


def create_gradient_overlay(size: Tuple[int, int], direction: str = "bottom") -> Image.Image:
    """Create a smooth gradient overlay for better text readability."""
    width, height = size
    gradient = Image.new('RGBA', size, (0, 0, 0, 0))

    for y in range(height):
        if direction == "bottom":
            alpha = int(180 * (y / height) ** 1.5)  # Stronger at bottom
        elif direction == "top":
            alpha = int(180 * ((height - y) / height) ** 1.5)
        elif direction == "center":
            alpha = int(160 * (1 - abs(y - height//2) / (height//2)) ** 2)
        else:
            alpha = 120

        for x in range(width):
            gradient.putpixel((x, y), (0, 0, 0, alpha))

    return gradient


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

    # Enhance image
    base = ImageEnhance.Contrast(base).enhance(1.08)
    base = ImageEnhance.Sharpness(base).enhance(1.1)
    base = ImageEnhance.Color(base).enhance(1.05)

    # Apply gradient overlay for text readability
    gradient = create_gradient_overlay(size, direction="bottom")
    poster = Image.alpha_composite(base.convert("RGBA"), gradient)

    # Add subtle vignette
    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for i in range(max(width, height) // 2, 0, -2):
        alpha = int(30 * (1 - i / (max(width, height) // 2)))
        v_draw.ellipse([width//2 - i, height//2 - i, width//2 + i, height//2 + i], 
                       outline=(0, 0, 0, alpha))
    poster = Image.alpha_composite(poster, vignette)

    # Add logo
    poster = overlay_logo(poster, logo, position="top-right")

    draw = ImageDraw.Draw(poster)

    accent_rgb = tuple(int(accent.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    text_rgb = tuple(int(text_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    margin = max(40, width // 16)

    # Dynamic font sizing based on image size
    title_font = get_font(max(52, width // 10), bold=True)
    tagline_font = get_font(max(32, width // 24))
    cta_font = get_font(max(28, width // 28), bold=True)
    brand_font = get_font(max(22, width // 40), bold=True)

    # Brand badge with shadow effect
    badge_w = max(240, width // 3.5)
    badge_h = 60
    # Shadow
    draw.rounded_rectangle(
        (margin + 3, margin + 3, margin + badge_w + 3, margin + badge_h + 3),
        radius=10,
        fill=(0, 0, 0, 100),
    )
    # Main badge
    draw.rounded_rectangle(
        (margin, margin, margin + badge_w, margin + badge_h),
        radius=10,
        fill=(255, 255, 255, 240),
    )
    draw.text((margin + 20, margin + 16), "SAMKETAN", font=brand_font, fill=(20, 25, 35))

    # Main headline with text shadow for depth
    headline = campaign["poster_main_text"]
    headline_y = height // 2 - height // 10

    # Shadow text
    draw_centered_multiline(
        draw,
        (width // 2 + 2, headline_y + 2),
        headline,
        title_font,
        (0, 0, 0),
        width - margin * 2,
        line_gap=max(8, width // 90),
    )
    # Main text
    draw_centered_multiline(
        draw,
        (width // 2, headline_y),
        headline,
        title_font,
        text_rgb,
        width - margin * 2,
        line_gap=max(8, width // 90),
    )

    # Tagline with accent background
    tagline = campaign.get("poster_tagline", "")
    if tagline:
        tag_w, tag_h = text_size(draw, tagline, tagline_font)
        tag_y = height // 2 + height // 12

        # Shadow
        draw.rounded_rectangle(
            (
                width // 2 - tag_w // 2 - 30 + 2,
                tag_y - 16 + 2,
                width // 2 + tag_w // 2 + 30 + 2,
                tag_y + tag_h + 20 + 2,
            ),
            radius=10,
            fill=(0, 0, 0, 80),
        )
        # Main
        draw.rounded_rectangle(
            (
                width // 2 - tag_w // 2 - 30,
                tag_y - 16,
                width // 2 + tag_w // 2 + 30,
                tag_y + tag_h + 20,
            ),
            radius=10,
            fill=accent_rgb + (235,),
        )
        draw.text((width // 2 - tag_w // 2, tag_y), tagline, font=tagline_font, fill=(255, 255, 255))

    # CTA button with glow effect
    cta = campaign.get("poster_cta", "Order now")
    cta_w, cta_h = text_size(draw, cta, cta_font)
    cta_y = height - margin - 90

    # Glow
    for glow_offset in range(3, 0, -1):
        glow_alpha = 40 - glow_offset * 10
        draw.rounded_rectangle(
            (
                width // 2 - cta_w // 2 - 45 - glow_offset,
                cta_y - glow_offset,
                width // 2 + cta_w // 2 + 45 + glow_offset,
                cta_y + cta_h + 38 + glow_offset,
            ),
            radius=12,
            fill=accent_rgb + (glow_alpha,),
        )

    # Main button
    draw.rounded_rectangle(
        (
            width // 2 - cta_w // 2 - 45,
            cta_y,
            width // 2 + cta_w // 2 + 45,
            cta_y + cta_h + 38,
        ),
        radius=10,
        fill=(255, 255, 255, 245),
    )
    draw.text((width // 2 - cta_w // 2, cta_y + 19), cta, font=cta_font, fill=accent_rgb)

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




def create_background_music(duration: float, tempo: str = "medium") -> str:
    """Generate simple background music using numpy/audio processing."""
    import numpy as np
    from scipy.io.wavfile import write

    sample_rate = 44100
    total_samples = int(duration * sample_rate)

    # Create a simple ambient pad
    t = np.linspace(0, duration, total_samples, False)

    # Base frequencies for ambient feel
    if tempo == "slow":
        base_freq = 220  # A3
        beat_freq = 0.5
    elif tempo == "fast":
        base_freq = 330  # E4
        beat_freq = 2.0
    else:  # medium
        base_freq = 261.63  # C4
        beat_freq = 1.0

    # Layer multiple sine waves for richness
    wave1 = 0.3 * np.sin(2 * np.pi * base_freq * t)
    wave2 = 0.2 * np.sin(2 * np.pi * base_freq * 1.5 * t)  # Perfect fifth
    wave3 = 0.15 * np.sin(2 * np.pi * base_freq * 2 * t)   # Octave
    wave4 = 0.1 * np.sin(2 * np.pi * base_freq * 1.25 * t) # Major third

    # Add slow amplitude modulation (tremolo)
    tremolo = 0.5 + 0.5 * np.sin(2 * np.pi * beat_freq * t)

    # Combine waves
    audio = (wave1 + wave2 + wave3 + wave4) * tremolo

    # Apply fade in/out
    fade_samples = int(2 * sample_rate)  # 2 second fade
    if len(audio) > 2 * fade_samples:
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        audio[:fade_samples] *= fade_in
        audio[-fade_samples:] *= fade_out

    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.3  # Keep volume moderate

    # Convert to 16-bit PCM
    audio_int16 = (audio * 32767).astype(np.int16)

    # Save
    music_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    write(music_file.name, sample_rate, audio_int16)
    music_file.close()
    return music_file.name


def apply_ken_burns(image: Image.Image, size: Tuple[int, int], duration: float, 
                    zoom_direction: str = "in", pan_direction: str = "none") -> list:
    """Generate frames with Ken Burns effect (slow zoom and pan)."""
    from PIL import Image
    import numpy as np

    fps = 24
    total_frames = int(duration * fps)
    frames = []

    # Start and end zoom levels
    if zoom_direction == "in":
        start_scale = 1.0
        end_scale = 1.15
    elif zoom_direction == "out":
        start_scale = 1.15
        end_scale = 1.0
    else:
        start_scale = 1.0
        end_scale = 1.0

    # Pan offsets
    pan_offsets = {
        "none": (0, 0),
        "left": (-0.05, 0),
        "right": (0.05, 0),
        "up": (0, -0.05),
        "down": (0, 0.05),
        "diagonal": (0.03, -0.03)
    }

    start_pan = pan_offsets.get(pan_direction, (0, 0))
    end_pan = (-start_pan[0], -start_pan[1])  # Reverse for smooth motion

    for i in range(total_frames):
        progress = i / (total_frames - 1) if total_frames > 1 else 0

        # Interpolate scale
        scale = start_scale + (end_scale - start_scale) * progress

        # Interpolate pan
        pan_x = start_pan[0] + (end_pan[0] - start_pan[0]) * progress
        pan_y = start_pan[1] + (end_pan[1] - start_pan[1]) * progress

        # Calculate crop box
        new_w = int(size[0] / scale)
        new_h = int(size[1] / scale)

        # Center point with pan offset
        center_x = size[0] // 2 + int(pan_x * size[0])
        center_y = size[1] // 2 + int(pan_y * size[1])

        left = max(0, center_x - new_w // 2)
        top = max(0, center_y - new_h // 2)
        right = min(image.width, left + new_w)
        bottom = min(image.height, top + new_h)

        # Adjust if out of bounds
        if right - left < new_w:
            left = max(0, right - new_w)
        if bottom - top < new_h:
            top = max(0, bottom - new_h)

        # Crop and resize
        cropped = image.crop((left, top, right, bottom))
        frame = cropped.resize(size, Image.Resampling.LANCZOS)
        frames.append(np.array(frame))

    return frames


def create_text_overlay_frame(base_frame: np.ndarray, text: str, subtext: str = "",
                               position: str = "bottom", accent_color: Tuple[int, int, int] = (15, 118, 110),
                               animation_progress: float = 0.5) -> np.ndarray:
    """Add animated text overlay to a frame."""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    img = Image.fromarray(base_frame)
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Font sizes
    title_font = get_font(max(48, width // 14), bold=True)
    sub_font = get_font(max(28, width // 32))

    # Animation: fade in + slide up
    alpha = min(1.0, animation_progress * 2)  # Fade in over first half
    slide_offset = int((1 - alpha) * 30)  # Slide up 30 pixels

    # Text color with alpha
    text_color = (255, 255, 255)

    # Background band
    band_height = max(200, height // 4)
    if position == "bottom":
        band_y = height - band_height
    else:
        band_y = 0

    # Semi-transparent band
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, band_y, width, band_y + band_height), 
                           fill=(0, 0, 0, int(180 * alpha)))

    # Accent line
    line_y = band_y if position == "top" else band_y + band_height - 8
    overlay_draw.rectangle((0, line_y, width, line_y + 8), 
                           fill=accent_color + (int(255 * alpha),))

    # Composite overlay
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    # Draw text
    text_y = band_y + band_height // 2 - 20 + slide_offset

    # Wrap and center text
    max_text_width = width - 80
    wrapped = wrap_text(draw, text, title_font, max_text_width)
    lines = wrapped.split('\n')

    total_text_height = sum(text_size(draw, line, title_font)[1] for line in lines)
    if subtext:
        total_text_height += text_size(draw, subtext, sub_font)[1] + 15

    current_y = text_y - total_text_height // 2

    for line in lines:
        line_w, line_h = text_size(draw, line, title_font)
        draw.text((width // 2 - line_w // 2, current_y), line, 
                  font=title_font, fill=text_color)
        current_y += line_h + 8

    if subtext:
        sub_w, sub_h = text_size(draw, subtext, sub_font)
        draw.text((width // 2 - sub_w // 2, current_y + 10), subtext,
                  font=sub_font, fill=(200, 200, 200))

    return np.array(img)


def create_scene_transition(frame1: np.ndarray, frame2: np.ndarray, 
                            duration: float = 0.5, transition_type: str = "fade") -> list:
    """Create transition frames between two scenes."""
    import numpy as np
    fps = 24
    total_frames = int(duration * fps)
    frames = []

    for i in range(total_frames):
        progress = i / (total_frames - 1) if total_frames > 1 else 0

        if transition_type == "fade":
            # Crossfade
            frame = (1 - progress) * frame1.astype(float) + progress * frame2.astype(float)
            frames.append(frame.astype(np.uint8))
        elif transition_type == "slide":
            # Slide transition
            h, w = frame1.shape[:2]
            offset = int(w * progress)
            result = np.zeros_like(frame1)
            result[:, :w-offset] = frame1[:, offset:]
            result[:, w-offset:] = frame2[:, :offset]
            frames.append(result)
        else:
            frames.append(frame1 if progress < 0.5 else frame2)

    return frames


def create_professional_video(
    images: List[Image.Image],
    logo: Optional[Image.Image],
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    duration: int,
    accent: str,
    audio_path: Optional[str],
    include_music: bool = True,
    music_tempo: str = "medium",
) -> str:
    """Create a professional multi-scene video with effects."""
    from moviepy.editor import AudioFileClip, ImageSequenceClip, CompositeAudioClip
    from moviepy.audio.fx.all import audio_fadein, audio_fadeout
    import numpy as np

    fps = 24
    accent_rgb = tuple(int(accent.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # Prepare images
    prepared_images = []
    for img in images[:4]:  # Use up to 4 images
        prepared = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), 
                                size, method=Image.Resampling.LANCZOS)
        prepared_images.append(prepared)

    # If only one image, duplicate it
    while len(prepared_images) < 2:
        prepared_images.append(prepared_images[0])

    # Scene definitions
    scenes = []
    scene_duration = duration / len(prepared_images)

    headlines = [
        campaign.get("headline", "Premium Quality"),
        campaign.get("poster_main_text", "Trusted Supply"),
        campaign.get("poster_tagline", "Order Now"),
        "Contact Us Today"
    ]

    subtexts = [
        campaign.get("business_name", "Samketan Marketing"),
        campaign.get("product_name", ""),
        campaign.get("poster_cta", ""),
        ""
    ]

    zoom_dirs = ["in", "out", "in", "out"]
    pan_dirs = ["none", "left", "right", "diagonal"]

    all_frames = []

    for idx, (img, headline, subtext, zoom, pan) in enumerate(
        zip(prepared_images, headlines, subtexts, zoom_dirs, pan_dirs)
    ):
        # Generate Ken Burns frames
        kb_frames = apply_ken_burns(img, size, scene_duration, zoom, pan)

        # Add text overlays with animation
        scene_frames = []
        for frame_idx, frame in enumerate(kb_frames):
            anim_progress = frame_idx / len(kb_frames) if kb_frames else 0
            # Delay text appearance slightly
            text_progress = max(0, (anim_progress - 0.1) / 0.9)

            frame_with_text = create_text_overlay_frame(
                frame, headline, subtext,
                position="bottom", accent_color=accent_rgb,
                animation_progress=text_progress
            )

            # Add logo watermark
            if logo is not None:
                pil_frame = Image.fromarray(frame_with_text)
                pil_frame = overlay_logo_watermark(pil_frame, logo)
                frame_with_text = np.array(pil_frame)

            scene_frames.append(frame_with_text)

        all_frames.extend(scene_frames)

        # Add transition to next scene (except for last)
        if idx < len(prepared_images) - 1:
            next_img = prepared_images[idx + 1]
            next_kb = apply_ken_burns(next_img, size, 0.5, zoom_dirs[idx+1], pan_dirs[idx+1])
            first_next = next_kb[0] if next_kb else np.zeros_like(frame)

            transition = create_scene_transition(
                scene_frames[-1], first_next, 0.5, "fade"
            )
            all_frames.extend(transition)

    # Create video clip
    video_clip = ImageSequenceClip(all_frames, fps=fps)

    # Handle audio
    audio_clips = []

    # Background music
    if include_music:
        music_path = create_background_music(video_clip.duration, music_tempo)
        music_clip = AudioFileClip(music_path)
        # Loop music if needed
        if music_clip.duration < video_clip.duration:
            loops = int(video_clip.duration / music_clip.duration) + 1
            music_clip = CompositeAudioClip([music_clip] * loops).subclip(0, video_clip.duration)
        else:
            music_clip = music_clip.subclip(0, video_clip.duration)
        # Lower music volume
        music_clip = music_clip.volumex(0.3)
        music_clip = audio_fadein(music_clip, 2).fx(audio_fadeout, 2)
        audio_clips.append(music_clip)

    # TTS narration
    if audio_path:
        tts_clip = AudioFileClip(audio_path)
        tts_clip = tts_clip.volumex(0.8)
        audio_clips.append(tts_clip)

    # Combine audio
    if audio_clips:
        final_audio = CompositeAudioClip(audio_clips)
        video_clip = video_clip.set_audio(final_audio)

    # Export
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    output.close()
    video_clip.write_videofile(
        output.name,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        verbose=False,
        logger=None,
    )

    video_clip.close()
    for clip in audio_clips:
        clip.close()

    return output.name


def overlay_logo_watermark(base_image: Image.Image, logo: Image.Image, 
                           opacity: float = 0.8) -> Image.Image:
    """Add a subtle logo watermark to the corner."""
    img = base_image.copy().convert("RGBA")
    logo_rgba = ImageOps.exif_transpose(logo).convert("RGBA")

    # Resize logo small
    max_logo_width = max(60, img.width // 10)
    ratio = max_logo_width / logo_rgba.width
    new_size = (max_logo_width, int(logo_rgba.height * ratio))
    logo_rgba = logo_rgba.resize(new_size, Image.Resampling.LANCZOS)

    # Apply opacity
    logo_data = np.array(logo_rgba)
    logo_data[..., 3] = (logo_data[..., 3] * opacity).astype(np.uint8)
    logo_rgba = Image.fromarray(logo_data)

    # Position: top-right
    margin = max(15, img.width // 50)
    pos = (img.width - logo_rgba.width - margin, margin)

    img.paste(logo_rgba, pos, logo_rgba)
    return img.convert("RGB")


# Replace the old create_video function
def create_video(
    image: Image.Image,
    logo: Optional[Image.Image],
    campaign: Dict[str, Any],
    size: Tuple[int, int],
    duration: int,
    accent: str,
    audio_path: Optional[str],
) -> str:
    """Wrapper that uses the professional video engine with multiple images if available."""
    images = [image]
    if "uploaded_images" in st.session_state and st.session_state.uploaded_images:
        images = st.session_state.uploaded_images[:4]

    return create_professional_video(
        images=images,
        logo=logo,
        campaign=campaign,
        size=size,
        duration=duration,
        accent=accent,
        audio_path=audio_path,
        include_music=True,
        music_tempo="medium",
    )


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

        # ── YOUR KIT DASHBOARD ──
        st.divider()
        st.subheader("📦 Your Marketing Kit Dashboard")
        st.caption("Everything generated is stored here. Click any card to jump to that tab.")

        kit_col1, kit_col2, kit_col3, kit_col4 = st.columns(4)

        with kit_col1:
            poster_ready = "poster" in st.session_state
            video_ready = "video_path" in st.session_state
            st.markdown(f"""
            <div class='metric-card' style='border-left: 4px solid {"#10b981" if poster_ready else "#e5e7eb"};'>
                <b>🖼️ Poster</b><br>
                <span style='color: {"#10b981" if poster_ready else "#9ca3af"}; font-size: 0.85rem;'>
                    {"✅ Ready — go to Poster tab" if poster_ready else "⏳ Not generated yet"}
                </span>
            </div>
            <div class='metric-card' style='border-left: 4px solid {"#10b981" if video_ready else "#e5e7eb"}; margin-top: 8px;'>
                <b>🎬 Video</b><br>
                <span style='color: {"#10b981" if video_ready else "#9ca3af"}; font-size: 0.85rem;'>
                    {"✅ Ready — go to Video tab" if video_ready else "⏳ Not generated yet"}
                </span>
            </div>
            """, unsafe_allow_html=True)

        with kit_col2:
            invite_ready = "invitation" in st.session_state
            proc_ready = "proceedings" in st.session_state
            st.markdown(f"""
            <div class='metric-card' style='border-left: 4px solid {"#10b981" if invite_ready else "#e5e7eb"};'>
                <b>📨 Invitation</b><br>
                <span style='color: {"#10b981" if invite_ready else "#9ca3af"}; font-size: 0.85rem;'>
                    {"✅ Ready — go to Invitation tab" if invite_ready else "⏳ Not generated yet"}
                </span>
            </div>
            <div class='metric-card' style='border-left: 4px solid {"#10b981" if proc_ready else "#e5e7eb"}; margin-top: 8px;'>
                <b>📋 Proceedings</b><br>
                <span style='color: {"#10b981" if proc_ready else "#9ca3af"}; font-size: 0.85rem;'>
                    {"✅ Ready — go to Invitation tab" if proc_ready else "⏳ Not generated yet"}
                </span>
            </div>
            """, unsafe_allow_html=True)

        with kit_col3:
            ach_ready = "achievement_card" in st.session_state
            st.markdown(f"""
            <div class='metric-card' style='border-left: 4px solid {"#10b981" if ach_ready else "#e5e7eb"};'>
                <b>🏆 Achievement</b><br>
                <span style='color: {"#10b981" if ach_ready else "#9ca3af"}; font-size: 0.85rem;'>
                    {"✅ Ready — go to Achievements tab" if ach_ready else "⏳ Not generated yet"}
                </span>
            </div>
            """, unsafe_allow_html=True)

        with kit_col4:
            # Quick download all button
            if any(k in st.session_state for k in ["poster", "video_path", "invitation", "proceedings", "achievement_card"]):
                if st.button("📥 Download All Assets", type="primary", use_container_width=True):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as package:
                        product_name = st.session_state.get("product_name", "samketan")
                        full_text = campaign_text(campaign, product_name, st.session_state.get("business_name", ""))
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
                        "⬇️ Click to save ZIP",
                        data=zip_buffer,
                        file_name=f"{safe_filename(st.session_state.get('product_name', 'samketan'))}_full_kit.zip",
                        mime="application/zip",
                    )
            else:
                st.markdown("""
                <div class='metric-card' style='border-left: 4px solid #e5e7eb;'>
                    <b>📦 Full Package</b><br>
                    <span style='color: #9ca3af; font-size: 0.85rem;'>Generate assets first</span>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        st.subheader("Narration Script")
        st.write(campaign.get("narration_script", ""))

        with st.expander("View all social copy"):
            social_text_area("LinkedIn Post", campaign.get("linkedin_post", ""))
            social_text_area("Instagram Caption", campaign.get("instagram_caption", ""))
            social_text_area("Facebook Post", campaign.get("facebook_post", ""))
            social_text_area("WhatsApp Message", campaign.get("whatsapp_message", ""))


# ─── Tab 2: Video ──────────────────────────────────────────────────────────────

with tabs[2]:
    st.header("Create Professional Video")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit first.")
    else:
        campaign = st.session_state.campaign
        image = st.session_state.primary_image
        logo = st.session_state.get("logo_image")

        st.subheader("Video Settings")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            video_choice = st.selectbox("Video format", list(VIDEO_FORMATS.keys()))
            speed = st.slider("Narration speed", 0.85, 1.25, 1.0, 0.05)
        with col_b:
            accent = st.color_picker("Accent color", "#0f766e")
            include_tts = st.checkbox("Add AI narration", value=True)
        with col_c:
            include_music = st.checkbox("Add background music", value=True)
            music_tempo = st.selectbox("Music tempo", ["slow", "medium", "fast"], 
                                       help="Slow = calm ambient, Medium = balanced, Fast = energetic")

        st.info("""
        **What the video includes:**
        - Multiple scenes from your uploaded photos
        - Ken Burns effect (slow zoom & pan)
        - Animated text overlays
        - Smooth fade transitions
        - Logo watermark
        - Background music + AI narration (if enabled)
        """)

        if st.button("Generate professional video", type="primary", use_container_width=True):
            with st.spinner("Building professional video with effects..."):
                try:
                    config = VIDEO_FORMATS[video_choice]
                    audio_path = None
                    if include_tts:
                        try:
                            audio_path = create_tts_audio(campaign["narration_script"], service_account_info, speed)
                            if audio_path:
                                st.success("AI narration generated.")
                            else:
                                st.warning("No service account found, video will have music only.")
                        except Exception as exc:
                            st.warning(f"Narration unavailable: {exc}")

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
                    st.info("Make sure ffmpeg is installed. Streamlit Cloud installs it from packages.txt.")

with tabs[3]:
    st.header("Create Poster")

    if "campaign" not in st.session_state:
        st.info("Generate a marketing kit first.")
    else:
        campaign = st.session_state.campaign
        image = st.session_state.primary_image
        logo = st.session_state.get("logo_image")

        st.subheader("Poster Design")
        col_a, col_b = st.columns(2)
        with col_a:
            poster_choice = st.selectbox("Poster format", list(POSTER_FORMATS.keys()))
            st.caption("Choose the platform where you'll post this.")
        with col_b:
            accent = st.color_picker("Accent color", "#0f766e", 
                                     help="Used for highlights and tagline background")
            text_color = st.color_picker("Text color", "#ffffff",
                                         help="Main headline color")

        # Show preview info
        st.info("""
        **Poster includes:**
        - Your product photo as background
        - Logo watermark (if uploaded)
        - AI-generated headline & tagline
        - Call-to-action button
        - Samketan branding
        """)

        if st.button("Generate poster", type="primary", use_container_width=True):
            with st.spinner("Designing poster..."):
                try:
                    poster = make_poster(image, logo, campaign, POSTER_FORMATS[poster_choice], accent, text_color)
                    st.session_state.poster = poster

                    # Show poster with download
                    st.image(poster, use_container_width=True, caption="Your marketing poster")

                    poster_buffer = io.BytesIO()
                    poster.save(poster_buffer, format="PNG")
                    poster_buffer.seek(0)

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            "📥 Download poster (PNG)",
                            data=poster_buffer,
                            file_name=f"{safe_filename(st.session_state.product_name)}_poster.png",
                            mime="image/png",
                        )
                    with col_dl2:
                        # Also create a JPEG version for smaller file size
                        poster_buffer_jpg = io.BytesIO()
                        poster.convert("RGB").save(poster_buffer_jpg, format="JPEG", quality=90)
                        poster_buffer_jpg.seek(0)
                        st.download_button(
                            "📥 Download poster (JPG)",
                            data=poster_buffer_jpg,
                            file_name=f"{safe_filename(st.session_state.product_name)}_poster.jpg",
                            mime="image/jpeg",
                        )

                except Exception as exc:
                    st.error(f"Poster generation failed: {exc}")

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
