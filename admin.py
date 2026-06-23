# admin.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import (
    get_total_users, get_total_downloads, get_all_users,
    ban_user, unban_user, get_top_users, get_recent_downloads,
    get_user_info, get_setting, set_setting
)


def is_admin(user_id):
    """Check if user is admin."""
    return user_id == ADMIN_ID


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You are not authorized!")
        return

    total_users = get_total_users()
    total_downloads = get_total_downloads()
    maintenance = get_setting("maintenance_mode") == "1"

    text = (
        "🔧 **Admin Panel**\n\n"
        f"👥 Total Users: `{total_users}`\n"
        f"📥 Total Downloads: `{total_downloads}`\n"
        f"🔧 Maintenance: {'🔴 ON' if maintenance else '🟢 OFF'}\n\n"
        "Use the buttons below to manage the bot:"
    )

    keyboard = [
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🏆 Top Users", callback_data="admin_top_users")
        ],
        [
            InlineKeyboardButton("📋 Recent Downloads", callback_data="admin_recent"),
            InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maintenance")
        ],
        [
            InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
            InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")
        ],
        [
            InlineKeyboardButton("📝 Set Welcome Msg", callback_data="admin_welcome"),
            InlineKeyboardButton("🔄 Restart", callback_data="admin_restart")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel callbacks."""
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("⛔ Not authorized!", show_alert=True)
        return

    data = query.data

    if data == "admin_stats":
        total_users = get_total_users()
        total_downloads = get_total_downloads()

        text = (
            "📊 **Bot Statistics**\n\n"
            f"👥 Total Users: `{total_users}`\n"
            f"📥 Total Downloads: `{total_downloads}`\n"
            f"📈 Avg Downloads/User: `{total_downloads/max(total_users,1):.1f}`\n"
        )

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_top_users":
        top_users = get_top_users(10)
        text = "🏆 **Top Users by Downloads**\n\n"

        for i, (uid, username, first_name, downloads) in enumerate(top_users, 1):
            name = username or first_name or str(uid)
            text += f"{i}. @{name} - `{downloads}` downloads\n"

        if not top_users:
            text += "No users yet."

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_recent":
        recent = get_recent_downloads(10)
        text = "📋 **Recent Downloads**\n\n"

        for uid, username, url, platform, date in recent:
            name = f"@{username}" if username else str(uid)
            short_url = url[:40] + "..." if len(url) > 40 else url
            text += f"• {name} | {platform} | {date}\n  {short_url}\n\n"

        if not recent:
            text += "No downloads yet."

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_maintenance":
        current = get_setting("maintenance_mode")
        new_value = "0" if current == "1" else "1"
        set_setting("maintenance_mode", new_value)

        status = "🔴 ON" if new_value == "1" else "🟢 OFF"
        await query.edit_message_text(
            f"🔧 Maintenance mode is now: {status}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]),
            parse_mode="Markdown"
        )

    elif data == "admin_broadcast":
        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text(
            "📢 **Broadcast Message**\n\nSend me the message you want to broadcast to all users.\n\nSend /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]),
            parse_mode="Markdown"
        )

    elif data == "admin_ban":
        context.user_data["awaiting_ban"] = True
        await query.edit_message_text(
            "🚫 **Ban User**\n\nSend me the User ID to ban.\n\nSend /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]),
            parse_mode="Markdown"
        )

    elif data == "admin_unban":
        context.user_data["awaiting_unban"] = True
        await query.edit_message_text(
            "✅ **Unban User**\n\nSend me the User ID to unban.\n\nSend /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]),
            parse_mode="Markdown"
        )

    elif data == "admin_welcome":
        context.user_data["awaiting_welcome"] = True
        await query.edit_message_text(
            "📝 **Set Welcome Message**\n\nSend me the new welcome message.\n\nSend /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]),
            parse_mode="Markdown"
        )

    elif data == "admin_users":
        total_users = get_total_users()
        text = f"👥 **User Management**\n\nTotal Users: `{total_users}`\n\nUse /userinfo <user_id> to see user details."

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_back":
        total_users = get_total_users()
        total_downloads = get_total_downloads()
        maintenance = get_setting("maintenance_mode") == "1"

        text = (
            "🔧 **Admin Panel**\n\n"
            f"👥 Total Users: `{total_users}`\n"
            f"📥 Total Downloads: `{total_downloads}`\n"
            f"🔧 Maintenance: {'🔴 ON' if maintenance else '🟢 OFF'}\n\n"
            "Use the buttons below to manage the bot:"
        )

        keyboard = [
            [
                InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
                InlineKeyboardButton("👥 Users", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
                InlineKeyboardButton("🏆 Top Users", callback_data="admin_top_users")
            ],
            [
                InlineKeyboardButton("📋 Recent Downloads", callback_data="admin_recent"),
                InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maintenance")
            ],
            [
                InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
                InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")
            ],
            [
                InlineKeyboardButton("📝 Set Welcome Msg", callback_data="admin_welcome"),
                InlineKeyboardButton("🔄 Restart", callback_data="admin_restart")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    elif data == "admin_restart":
        await query.edit_message_text("🔄 Restarting bot...")
        import sys
        os.execv(sys.executable, [sys.executable] + sys.argv)


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin text inputs for broadcast, ban, etc."""
    if not is_admin(update.effective_user.id):
        return False

    user_data = context.user_data

    # Handle broadcast
    if user_data.get("awaiting_broadcast"):
        user_data["awaiting_broadcast"] = False
        message = update.message.text

        if message == "/cancel":
            await update.message.reply_text("❌ Broadcast cancelled.")
            return True

        all_users = get_all_users()
        sent = 0
        failed = 0

        status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(all_users)} users...")

        for user_id in all_users:
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
                sent += 1
            except Exception:
                failed += 1

            if (sent + failed) % 50 == 0:
                await status_msg.edit_text(f"📢 Broadcasting... {sent + failed}/{len(all_users)}")

        await status_msg.edit_text(
            f"📢 **Broadcast Complete**\n\n✅ Sent: `{sent}`\n❌ Failed: `{failed}`",
            parse_mode="Markdown"
        )
        return True

    # Handle ban
    if user_data.get("awaiting_ban"):
        user_data["awaiting_ban"] = False
        text = update.message.text

        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return True

        try:
            target_id = int(text)
            if ban_user(target_id):
                await update.message.reply_text(f"🚫 User `{target_id}` has been banned.", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ User `{target_id}` not found.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        return True

    # Handle unban
    if user_data.get("awaiting_unban"):
        user_data["awaiting_unban"] = False
        text = update.message.text

        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return True

        try:
            target_id = int(text)
            if unban_user(target_id):
                await update.message.reply_text(f"✅ User `{target_id}` has been unbanned.", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ User `{target_id}` not found.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        return True

    # Handle welcome message
    if user_data.get("awaiting_welcome"):
        user_data["awaiting_welcome"] = False
        text = update.message.text

        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return True

        set_setting("welcome_message", text)
        await update.message.reply_text("✅ Welcome message updated!")
        return True

    return False


import os
