# bot.py

import os
import sys
import logging
import asyncio
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

from config import BOT_TOKEN, ADMIN_ID, LOG_CHANNEL_ID
from database import (
    init_db, add_user, increment_downloads, log_download,
    is_banned, get_setting, get_user_info, get_total_users,
    get_total_downloads
)
from downloader import download_media, detect_platform, detect_media_type, cleanup, get_media_files
from admin import admin_panel, admin_callback, handle_admin_text, is_admin
from utils import (
    extract_url, is_supported_url, format_file_size,
    get_platform_emoji, get_media_type_emoji, truncate_text
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create downloads directory
os.makedirs("downloads", exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user

    # Add user to database
    add_user(user.id, user.username, user.first_name, user.last_name)

    # Check if banned
    if is_banned(user.id):
        await update.message.reply_text("⛔ You have been banned from using this bot.")
        return

    welcome_msg = get_setting("welcome_message")
    if not welcome_msg:
        welcome_msg = (
            "🌟 **Welcome to Social Media Downloader Bot!**\n\n"
            "Send me any link from:\n\n"
            "📸 **Instagram** - Posts, Stories, Reels, Highlights, Profile\n"
            "📘 **Facebook** - Posts, Stories, Reels, Videos\n"
            "🎵 **TikTok** - Videos\n"
            "🐦 **X (Twitter)** - Tweets, Videos\n"
            "📌 **Pinterest** - Pins, Videos\n"
            "👻 **Snapchat** - Stories\n\n"
            "📦 All files will be sent as a **ZIP** with caption & original link!\n\n"
            "Just paste the link and I'll handle the rest! 🚀"
        )

    keyboard = [
        [
            InlineKeyboardButton("📖 Help", callback_data="help"),
            InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
        ],
        [
            InlineKeyboardButton("🌐 Supported Platforms", callback_data="platforms")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📖 **How to use this bot:**\n\n"
        "1️⃣ Copy the link of the post/story/reel you want to download\n"
        "2️⃣ Paste the link in this chat\n"
        "3️⃣ Wait for the bot to download and send the ZIP file\n\n"
        "**Supported content types:**\n"
        "• 📷 Photos/Images\n"
        "• 📹 Videos\n"
        "• 📱 Stories\n"
        "• 🎬 Reels\n"
        "• ⭐ Highlights\n"
        "• 👤 Profile Pictures\n\n"
        "**Commands:**\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/stats - Show your download statistics\n"
    )

    if is_admin(update.effective_user.id):
        help_text += "\n**Admin Commands:**\n/admin - Open admin panel\n/userinfo <id> - Get user info\n"

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    user = update.effective_user
    user_info = get_user_info(user.id)

    if user_info:
        text = (
            f"📊 **Your Statistics**\n\n"
            f"👤 Name: {user.first_name}\n"
            f"🆔 ID: `{user.id}`\n"
            f"📥 Total Downloads: `{user_info[5]}`\n"
            f"📅 Joined: {user_info[4]}\n"
        )
    else:
        text = "No statistics available yet. Start downloading to see your stats!"

    await update.message.reply_text(text, parse_mode="Markdown")


async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /userinfo command (admin only)."""
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /userinfo <user_id>")
        return

    try:
        target_id = int(context.args[0])
        user_info = get_user_info(target_id)

        if user_info:
            text = (
                f"👤 **User Info**\n\n"
                f"🆔 ID: `{user_info[0]}`\n"
                f"📛 Username: @{user_info[1] or 'N/A'}\n"
                f"👤 Name: {user_info[2] or 'N/A'} {user_info[3] or ''}\n"
                f"📅 Joined: {user_info[4]}\n"
                f"📥 Downloads: `{user_info[5]}`\n"
                f"🚫 Banned: {'Yes' if user_info[6] else 'No'}\n"
            )
        else:
            text = f"❌ User `{target_id}` not found."

        await update.message.reply_text(text, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    # Check if it's an admin callback
    if query.data.startswith("admin_"):
        await admin_callback(update, context)
        return

    if query.data == "help":
        help_text = (
            "📖 **How to use this bot:**\n\n"
            "1️⃣ Copy the link of the post/story/reel\n"
            "2️⃣ Paste the link in this chat\n"
            "3️⃣ Wait for the ZIP file!\n\n"
            "📦 ZIP includes: Media files + Caption + Original link"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "my_stats":
        user = query.from_user
        user_info = get_user_info(user.id)

        if user_info:
            text = (
                f"📊 **Your Statistics**\n\n"
                f"👤 Name: {user.first_name}\n"
                f"🆔 ID: `{user.id}`\n"
                f"📥 Total Downloads: `{user_info[5]}`\n"
                f"📅 Joined: {user_info[4]}\n"
            )
        else:
            text = "No statistics available yet."

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "platforms":
        text = (
            "🌐 **Supported Platforms:**\n\n"
            "📸 **Instagram**\n"
            "   • Posts, Stories, Reels, IGTV\n"
            "   • Highlights, Profile pictures\n\n"
            "📘 **Facebook**\n"
            "   • Public posts, Videos, Reels\n"
            "   • Stories\n\n"
            "🎵 **TikTok**\n"
            "   • Videos (without watermark)\n\n"
            "🐦 **X (Twitter)**\n"
            "   • Tweets with media, Videos\n\n"
            "📌 **Pinterest**\n"
            "   • Pins, Videos\n\n"
            "👻 **Snapchat**\n"
            "   • Public Stories, Spotlight\n"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "back_start":
        welcome_msg = get_setting("welcome_message") or (
            "🌟 **Welcome to Social Media Downloader Bot!**\n\n"
            "Send me any link from supported platforms!\n\n"
            "📦 All files will be sent as a **ZIP** with caption & original link!"
        )

        keyboard = [
            [
                InlineKeyboardButton("📖 Help", callback_data="help"),
                InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
            ],
            [
                InlineKeyboardButton("🌐 Supported Platforms", callback_data="platforms")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle URLs sent by users."""
    user = update.effective_user
    message_text = update.message.text

    # Add user to database
    add_user(user.id, user.username, user.first_name, user.last_name)

    # Check if banned
    if is_banned(user.id):
        await update.message.reply_text("⛔ You have been banned from using this bot.")
        return

    # Check maintenance mode
    if get_setting("maintenance_mode") == "1" and not is_admin(user.id):
        await update.message.reply_text(
            "🔧 Bot is under maintenance. Please try again later!"
        )
        return

    # Check if admin is expecting text input
    if is_admin(user.id):
        handled = await handle_admin_text(update, context)
        if handled:
            return

    # Extract URL
    url = extract_url(message_text)

    if not url:
        await update.message.reply_text(
            "❌ No supported URL found!\n\n"
            "Please send a valid link from Instagram, Facebook, TikTok, X, Pinterest, or Snapchat."
        )
        return

    if not is_supported_url(url):
        await update.message.reply_text(
            "❌ This URL is not supported!\n\n"
            "Send /help to see supported platforms."
        )
        return

    # Detect platform and media type
    platform = detect_platform(url)
    media_type = detect_media_type(url)
    platform_emoji = get_platform_emoji(platform)
    media_emoji = get_media_type_emoji(media_type)

    # Send processing message
    processing_msg = await update.message.reply_text(
        f"⏳ **Downloading...**\n\n"
        f"{platform_emoji} Platform: **{platform.title()}**\n"
        f"{media_emoji} Type: **{media_type.title()}**\n\n"
        f"⏳ Please wait, this may take a moment...",
        parse_mode="Markdown"
    )

    zip_path = None
    download_dir = None

    try:
        # Download media
        zip_path, caption, media_files, download_dir = await download_media(url)

        if not zip_path:
            await processing_msg.edit_text(
                "❌ **Download Failed!**\n\n"
                "Possible reasons:\n"
                "• The content is private\n"
                "• The link is invalid or expired\n"
                "• File is too large (>50MB)\n"
                "• The platform blocked the request\n\n"
                "Please check the link and try again.",
                parse_mode="Markdown"
            )
            log_download(user.id, url, platform, media_type, "failed")
            return

        # Prepare caption for the file
        file_size = os.path.getsize(zip_path)
        formatted_size = format_file_size(file_size)

        file_caption = (
            f"{platform_emoji} **{platform.title()} {media_type.title()}**\n\n"
            f"📝 **Caption:**\n{truncate_text(caption, 800)}\n\n"
            f"🔗 **Original Link:** {url}\n\n"
            f"📦 **File Size:** {formatted_size}\n"
            f"📥 Downloaded by @SocialDLBot"
        )

        # Update processing message
        await processing_msg.edit_text(
            f"✅ **Download Complete!**\n\n"
            f"📦 Preparing ZIP file ({formatted_size})...\n"
            f"⬆️ Uploading...",
            parse_mode="Markdown"
        )

        # Send ZIP file
        with open(zip_path, "rb") as zip_file:
            zip_filename = f"{platform}_{media_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

            sent_doc = await update.message.reply_document(
                document=InputFile(zip_file, filename=zip_filename),
                caption=file_caption,
                parse_mode="Markdown"
            )

        # Update processing message
        await processing_msg.edit_text(
            f"✅ **Done!** {platform_emoji}\n\n"
            f"📦 ZIP file sent successfully!\n"
            f"📥 Contains: {len(media_files) if media_files else 'N/A'} file(s)\n"
            f"📦 Size: {formatted_size}",
            parse_mode="Markdown"
        )

        # Increment download count
        increment_downloads(user.id)
        log_download(user.id, url, platform, media_type, "success")

        # Send to log channel
        try:
            log_text = (
                f"📥 **New Download**\n\n"
                f"👤 User: @{user.username or 'N/A'}\n"
                f"🆔 ID: `{user.id}`\n"
                f"🔗 URL: {url}\n\n"
                f"{platform_emoji} Platform: {platform.title()}\n"
                f"{media_emoji} Type: {media_type.title()}\n"
                f"📦 Size: {formatted_size}\n"
                f"📝 Caption: {truncate_text(caption, 200)}"
            )

            # Send log text to channel
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=log_text,
                parse_mode="Markdown"
            )

            # Forward the actual file to log channel
            if sent_doc and sent_doc.document:
                await context.bot.send_document(
                    chat_id=LOG_CHANNEL_ID,
                    document=sent_doc.document.file_id,
                    caption=f"📹 File from @{user.username or 'N/A'} (ID: {user.id})\n🔗 {url}",
                    parse_mode="Markdown"
                )

            # Also send individual media files if they exist
            if media_files:
                for mf in media_files[:5]:  # Limit to 5 files for log
                    try:
                        ext = os.path.splitext(mf)[1].lower()
                        if ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
                            file_size_check = os.path.getsize(mf)
                            if file_size_check < 50 * 1024 * 1024:
                                with open(mf, 'rb') as f:
                                    await context.bot.send_video(
                                        chat_id=LOG_CHANNEL_ID,
                                        video=InputFile(f),
                                        caption=f"📹 Video from @{user.username or user.id}\n🔗 {url}"
                                    )
                        elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                            with open(mf, 'rb') as f:
                                await context.bot.send_photo(
                                    chat_id=LOG_CHANNEL_ID,
                                    photo=InputFile(f),
                                    caption=f"🖼️ Image from @{user.username or user.id}\n🔗 {url}"
                                )
                    except Exception as e:
                        logger.error(f"Error sending media to log channel: {e}")

        except Exception as e:
            logger.error(f"Error sending to log channel: {e}")

    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        await processing_msg.edit_text(
            f"❌ **Error occurred!**\n\n"
            f"Error: {str(e)[:200]}\n\n"
            f"Please try again or contact support.",
            parse_mode="Markdown"
        )
        log_download(user.id, url, platform or "unknown", media_type or "unknown", "error")

    finally:
        # Cleanup
        if zip_path or download_dir:
            cleanup(zip_path, download_dir)


async def handle_non_url_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-URL text messages."""
    user = update.effective_user

    # Check if admin is expecting text input
    if is_admin(user.id):
        handled = await handle_admin_text(update, context)
        if handled:
            return

    await update.message.reply_text(
        "🔗 Please send me a valid URL from a supported platform.\n\n"
        "Send /help to see supported platforms and how to use the bot."
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Error: {context.error}", exc_info=context.error)

    try:
        if update and update.effective_user:
            # Notify admin
            error_msg = (
                f"⚠️ **Bot Error**\n\n"
                f"👤 User: {update.effective_user.id}\n"
                f"❌ Error: `{str(context.error)[:500]}`"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=error_msg,
                parse_mode="Markdown"
            )
    except:
        pass


async def post_init(application: Application):
    """Set bot commands after initialization."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "How to use this bot"),
        BotCommand("stats", "Your download statistics"),
    ]

    admin_commands = commands + [
        BotCommand("admin", "Admin panel"),
        BotCommand("userinfo", "Get user info"),
    ]

    await application.bot.set_my_commands(commands)

    # Set admin-specific commands
    try:
        from telegram import BotCommandScopeChat
        await application.bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=ADMIN_ID)
        )
    except:
        pass

    logger.info("Bot started successfully!")

    # Notify admin
    try:
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text="✅ **Bot Started Successfully!**\n\n🤖 Social Media Downloader Bot is now online.",
            parse_mode="Markdown"
        )
    except:
        pass


def main():
    """Main function to run the bot."""
    # Initialize database
    init_db()

    # Create application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("userinfo", userinfo_command))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # URL handler - matches messages containing URLs
    url_filter = filters.Regex(
        r'https?://(?:www\.)?(?:instagram\.com|instagr\.am|facebook\.com|fb\.watch|fb\.com|'
        r'tiktok\.com|vm\.tiktok\.com|twitter\.com|x\.com|t\.co|'
        r'pinterest\.com|pin\.it|snapchat\.com|story\.snapchat\.com)'
    )
    application.add_handler(MessageHandler(url_filter & filters.TEXT, handle_url))

    # Non-URL text handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_url_text))

    # Error handler
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info("Starting bot...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
