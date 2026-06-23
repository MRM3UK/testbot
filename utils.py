# utils.py

import re
from config import SUPPORTED_PLATFORMS


def extract_url(text):
    """Extract URL from text."""
    url_pattern = re.compile(
        r'https?://(?:www\.)?'
        r'(?:instagram\.com|instagr\.am|'
        r'facebook\.com|fb\.watch|fb\.com|'
        r'tiktok\.com|vm\.tiktok\.com|'
        r'twitter\.com|x\.com|t\.co|'
        r'pinterest\.com|pin\.it|'
        r'snapchat\.com|story\.snapchat\.com)'
        r'[^\s<>"\']*',
        re.IGNORECASE
    )

    match = url_pattern.search(text)
    return match.group(0) if match else None


def is_supported_url(url):
    """Check if URL is from a supported platform."""
    if not url:
        return False

    url_lower = url.lower()
    return any(platform in url_lower for platform in SUPPORTED_PLATFORMS)


def format_file_size(size_bytes):
    """Format file size to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_platform_emoji(platform):
    """Get emoji for platform."""
    emojis = {
        "instagram": "📸",
        "facebook": "📘",
        "tiktok": "🎵",
        "twitter": "🐦",
        "pinterest": "📌",
        "snapchat": "👻"
    }
    return emojis.get(platform, "🔗")


def get_media_type_emoji(media_type):
    """Get emoji for media type."""
    emojis = {
        "post": "📷",
        "story": "📱",
        "reel": "🎬",
        "highlight": "⭐",
        "profile": "👤",
        "video": "📹",
        "image": "🖼️"
    }
    return emojis.get(media_type, "📁")


def truncate_text(text, max_length=4000):
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
