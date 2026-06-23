# downloader.py

import os
import re
import json
import shutil
import asyncio
import zipfile
import logging
import subprocess
import aiohttp
import aiofiles
import uuid
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def detect_platform(url):
    """Detect which platform the URL belongs to."""
    url_lower = url.lower()

    if any(domain in url_lower for domain in ["instagram.com", "instagr.am"]):
        return "instagram"
    elif any(domain in url_lower for domain in ["facebook.com", "fb.watch", "fb.com"]):
        return "facebook"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    elif any(domain in url_lower for domain in ["twitter.com", "x.com", "t.co"]):
        return "twitter"
    elif any(domain in url_lower for domain in ["pinterest.com", "pin.it"]):
        return "pinterest"
    elif any(domain in url_lower for domain in ["snapchat.com", "story.snapchat.com"]):
        return "snapchat"

    return None


def detect_media_type(url):
    """Detect media type from URL."""
    url_lower = url.lower()

    if "stories" in url_lower or "story" in url_lower:
        return "story"
    elif "reel" in url_lower:
        return "reel"
    elif "highlights" in url_lower:
        return "highlight"
    elif "/p/" in url_lower or "photo" in url_lower:
        return "post"
    elif "profile" in url_lower:
        return "profile"
    else:
        return "post"


async def download_with_ytdlp(url, download_dir):
    """Download media using yt-dlp."""
    try:
        output_template = os.path.join(download_dir, "%(title).50s_%(id)s.%(ext)s")

        cmd = [
            "yt-dlp",
            "--no-check-certificates",
            "--no-warnings",
            "-o", output_template,
            "--write-thumbnail",
            "--write-description",
            "--write-info-json",
            "--merge-output-format", "mp4",
            "--max-filesize", "50m",
            "--socket-timeout", "30",
            "--retries", "3",
            url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=120
        )

        if process.returncode == 0:
            return True
        else:
            logger.error(f"yt-dlp error: {stderr.decode()}")
            return False

    except asyncio.TimeoutError:
        logger.error("yt-dlp download timed out")
        return False
    except Exception as e:
        logger.error(f"yt-dlp exception: {e}")
        return False


async def download_with_gallery_dl(url, download_dir):
    """Download media using gallery-dl."""
    try:
        cmd = [
            "gallery-dl",
            "--dest", download_dir,
            "--no-check-certificate",
            "--write-metadata",
            url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=120
        )

        if process.returncode == 0:
            return True
        else:
            logger.error(f"gallery-dl error: {stderr.decode()}")
            return False

    except asyncio.TimeoutError:
        logger.error("gallery-dl download timed out")
        return False
    except Exception as e:
        logger.error(f"gallery-dl exception: {e}")
        return False


async def download_with_api(url, download_dir, platform):
    """Download using public API services as fallback."""
    api_urls = {
        "instagram": [
            f"https://api.saveig.app/api/v1/media?url={url}",
        ],
        "tiktok": [
            f"https://api.tiklydown.eu.org/api/download?url={url}",
        ],
        "twitter": [
            f"https://api.vxtwitter.com/{url.split('/')[-1]}" if "status" in url else None,
        ],
        "pinterest": [
            f"https://api.pinterest.com/url/?url={url}",
        ]
    }

    # Try cobalt API (supports many platforms)
    try:
        async with aiohttp.ClientSession() as session:
            cobalt_payload = {
                "url": url,
                "vCodec": "h264",
                "vQuality": "720",
                "aFormat": "mp3",
                "filenamePattern": "basic"
            }

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            async with session.post(
                "https://api.cobalt.tools/api/json",
                json=cobalt_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "stream" or data.get("status") == "redirect":
                        media_url = data.get("url")
                        if media_url:
                            filename = f"media_{uuid.uuid4().hex[:8]}.mp4"
                            filepath = os.path.join(download_dir, filename)
                            async with session.get(media_url) as media_resp:
                                if media_resp.status == 200:
                                    async with aiofiles.open(filepath, "wb") as f:
                                        await f.write(await media_resp.read())
                                    return True
                    elif data.get("status") == "picker":
                        # Multiple media items
                        for i, item in enumerate(data.get("picker", [])):
                            media_url = item.get("url")
                            if media_url:
                                ext = "mp4" if item.get("type") == "video" else "jpg"
                                filename = f"media_{i+1}_{uuid.uuid4().hex[:8]}.{ext}"
                                filepath = os.path.join(download_dir, filename)
                                async with session.get(media_url) as media_resp:
                                    if media_resp.status == 200:
                                        async with aiofiles.open(filepath, "wb") as f:
                                            await f.write(await media_resp.read())
                        return True
    except Exception as e:
        logger.error(f"Cobalt API error: {e}")

    return False


async def download_with_rapid_api(url, download_dir, platform):
    """Download using RapidAPI alternatives."""
    try:
        async with aiohttp.ClientSession() as session:
            # Try saveig/savefrom type services
            if platform == "instagram":
                api_url = f"https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/?url={url}"
            elif platform == "tiktok":
                api_url = f"https://tiktok-downloader-download-tiktok-videos-without-watermark.p.rapidapi.com/vid/index?url={url}"
            elif platform == "facebook":
                api_url = f"https://facebook-reel-and-video-downloader.p.rapidapi.com/app/main.php?url={url}"
            else:
                return False

            # Note: These would require API keys in production
            # This is a fallback structure
            return False

    except Exception as e:
        logger.error(f"RapidAPI error: {e}")
        return False


def extract_caption_from_dir(download_dir):
    """Extract caption/description from downloaded metadata files."""
    caption = ""

    # Check for .description files (yt-dlp)
    for f in os.listdir(download_dir):
        if f.endswith(".description"):
            filepath = os.path.join(download_dir, f)
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    caption = file.read().strip()
                    break
            except:
                pass

    # Check for .info.json files (yt-dlp)
    if not caption:
        for f in os.listdir(download_dir):
            if f.endswith(".info.json"):
                filepath = os.path.join(download_dir, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        caption = data.get("description", "") or data.get("title", "")
                        break
                except:
                    pass

    # Check for gallery-dl metadata
    if not caption:
        for root, dirs, files in os.walk(download_dir):
            for f in files:
                if f.endswith(".json") and "metadata" in f.lower():
                    filepath = os.path.join(root, f)
                    try:
                        with open(filepath, "r", encoding="utf-8") as file:
                            data = json.load(file)
                            caption = data.get("description", "") or data.get("caption", "") or data.get("title", "")
                            break
                    except:
                        pass

    return caption[:4000] if caption else "No caption available"


def get_media_files(download_dir):
    """Get all media files from download directory."""
    media_extensions = {
        ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv",  # Video
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",  # Image
        ".mp3", ".aac", ".ogg", ".wav", ".m4a"  # Audio
    }

    media_files = []

    for root, dirs, files in os.walk(download_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in media_extensions:
                filepath = os.path.join(root, f)
                media_files.append(filepath)

    return media_files


def create_zip(download_dir, zip_path, original_url="", caption=""):
    """Create a ZIP file from downloaded media."""
    media_files = get_media_files(download_dir)

    if not media_files:
        return None

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filepath in media_files:
            arcname = os.path.basename(filepath)
            zipf.write(filepath, arcname)

        # Add info.txt with caption and original URL
        info_content = f"Original URL: {original_url}\n\n"
        info_content += f"Caption:\n{caption}\n\n"
        info_content += f"Downloaded by Social Media Downloader Bot"
        zipf.writestr("info.txt", info_content)

    # Check file size
    file_size = os.path.getsize(zip_path)
    if file_size > 50 * 1024 * 1024:  # 50MB Telegram limit
        return None

    return zip_path


async def download_media(url):
    """
    Main download function. Tries multiple methods.
    Returns: (zip_path, caption, media_files, download_dir) or (None, None, None, None)
    """
    unique_id = uuid.uuid4().hex[:12]
    download_dir = os.path.join("downloads", unique_id)
    os.makedirs(download_dir, exist_ok=True)

    platform = detect_platform(url)
    media_type = detect_media_type(url)

    success = False

    # Method 1: Try yt-dlp
    logger.info(f"Trying yt-dlp for {url}")
    success = await download_with_ytdlp(url, download_dir)

    # Method 2: Try gallery-dl
    if not success:
        logger.info(f"Trying gallery-dl for {url}")
        success = await download_with_gallery_dl(url, download_dir)

    # Method 3: Try API
    if not success:
        logger.info(f"Trying API for {url}")
        success = await download_with_api(url, download_dir, platform)

    # Check if any media files were downloaded
    media_files = get_media_files(download_dir)

    if not media_files:
        # Cleanup
        shutil.rmtree(download_dir, ignore_errors=True)
        return None, None, None, None

    # Extract caption
    caption = extract_caption_from_dir(download_dir)

    # Create ZIP
    zip_filename = f"{platform}_{media_type}_{unique_id}.zip"
    zip_path = os.path.join("downloads", zip_filename)
    zip_result = create_zip(download_dir, zip_path, url, caption)

    if not zip_result:
        # If ZIP is too large, try sending individual files
        shutil.rmtree(download_dir, ignore_errors=True)
        return None, caption, None, None

    return zip_path, caption, media_files, download_dir


def cleanup(zip_path, download_dir):
    """Clean up downloaded files."""
    try:
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
        if download_dir and os.path.exists(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
