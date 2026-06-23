# database.py

import sqlite3
import datetime
from config import DB_FILE


def init_db():
    """Initialize the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT,
            total_downloads INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            platform TEXT,
            media_type TEXT,
            download_date TEXT,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Default settings
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', '0')
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES ('welcome_message',
        '🌟 Welcome to Social Media Downloader Bot!\n\nSend me any link from:\n📸 Instagram\n📘 Facebook\n🎵 TikTok\n🐦 X (Twitter)\n📌 Pinterest\n👻 Snapchat\n\nI will download and send it to you as a ZIP file!')
    ''')

    conn.commit()
    conn.close()


def add_user(user_id, username, first_name, last_name):
    """Add or update a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, join_date, total_downloads, is_banned)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT total_downloads FROM users WHERE user_id = ?), 0),
        COALESCE((SELECT is_banned FROM users WHERE user_id = ?), 0))
    ''', (user_id, username, first_name, last_name,
          datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          user_id, user_id))

    conn.commit()
    conn.close()


def increment_downloads(user_id):
    """Increment download count for a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users SET total_downloads = total_downloads + 1 WHERE user_id = ?
    ''', (user_id,))

    conn.commit()
    conn.close()


def log_download(user_id, url, platform, media_type, status):
    """Log a download."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO downloads (user_id, url, platform, media_type, download_date, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, url, platform, media_type,
          datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status))

    conn.commit()
    conn.close()


def get_total_users():
    """Get total number of users."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_total_downloads():
    """Get total number of downloads."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM downloads WHERE status = "success"')
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_all_users():
    """Get all user IDs."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def ban_user(user_id):
    """Ban a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def unban_user(user_id):
    """Unban a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def is_banned(user_id):
    """Check if user is banned."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0] == 1
    return False


def get_setting(key):
    """Get a setting value."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def set_setting(key, value):
    """Set a setting value."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()


def get_top_users(limit=10):
    """Get top users by download count."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, first_name, total_downloads
        FROM users ORDER BY total_downloads DESC LIMIT ?
    ''', (limit,))
    users = cursor.fetchall()
    conn.close()
    return users


def get_recent_downloads(limit=10):
    """Get recent downloads."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT d.user_id, u.username, d.url, d.platform, d.download_date
        FROM downloads d
        LEFT JOIN users u ON d.user_id = u.user_id
        ORDER BY d.id DESC LIMIT ?
    ''', (limit,))
    downloads = cursor.fetchall()
    conn.close()
    return downloads


def get_user_info(user_id):
    """Get user info."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
