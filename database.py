# bots/ardayda_bot/database.py
"""
Persistent storage using SQLite.
Manages users, PDFs, tags, likes, and downloads.
Ensures atomic status updates and idempotent actions.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple

DATABASE_PATH = "ardayda_bot.db"

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Database connection helpers
# ----------------------------------------------------------------------

@contextmanager
def get_db():
    """Context manager for database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,  -- Telegram user_id
                username TEXT,
                full_name TEXT,
                region TEXT,
                school TEXT,
                student_class TEXT,
                status TEXT DEFAULT 'auth.register.name',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pdfs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                likes_count INTEGER DEFAULT 0,
                downloads_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                pdf_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (pdf_id, tag),
                FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                pdf_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (pdf_id, user_id),
                FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                pdf_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (pdf_id, user_id),
                FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id)")

# Initialize database on module import
init_db()

# ----------------------------------------------------------------------
# User functions
# ----------------------------------------------------------------------

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

def create_user(user_id: int, username: str, full_name: str) -> None:
    """Create a new user (status defaults to auth.register.name)."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )

def update_user(user_id: int, **kwargs) -> None:
    """Update user fields (e.g., region, school, student_class, full_name)."""
    allowed = {'full_name', 'region', 'school', 'student_class'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    with get_db() as conn:
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)

def get_user_status(user_id: int) -> Optional[str]:
    """Get current status of user."""
    with get_db() as conn:
        row = conn.execute("SELECT status FROM users WHERE id = ?", (user_id,)).fetchone()
        return row['status'] if row else None

def set_user_status(user_id: int, status: str) -> None:
    """Set user status (atomic update)."""
    with get_db() as conn:
        conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))

# ----------------------------------------------------------------------
# PDF functions
# ----------------------------------------------------------------------

def add_pdf(user_id: int, file_id: str, file_name: str, tags: List[str]) -> int:
    """
    Add a new PDF with associated tags.
    Returns the generated pdf_id.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO pdfs (user_id, file_id, file_name) VALUES (?, ?, ?)",
            (user_id, file_id, file_name)
        )
        pdf_id = cursor.lastrowid

        # Insert tags
        for tag in tags:
            conn.execute(
                "INSERT INTO tags (pdf_id, tag) VALUES (?, ?)",
                (pdf_id, tag)
            )
        return pdf_id

def get_pdfs_by_multilevel_tags(tag_filters: List[str]) -> List[Dict[str, Any]]:
    """
    Find PDFs that match all given tags (AND logic).
    Each tag is a string like "subject:math" or "exam:2020".
    Returns list of PDF dicts with id, file_name, tags, likes_count.
    """
    if not tag_filters:
        return []

    placeholders = ",".join("?" for _ in tag_filters)
    query = f"""
        SELECT p.id, p.file_name, p.likes_count,
               GROUP_CONCAT(t.tag) as tags_str
        FROM pdfs p
        JOIN tags t ON p.id = t.pdf_id
        WHERE t.tag IN ({placeholders})
        GROUP BY p.id
        HAVING COUNT(DISTINCT t.tag) = ?
    """
    with get_db() as conn:
        rows = conn.execute(query, tag_filters + [len(tag_filters)]).fetchall()
        result = []
        for row in rows:
            pdf = dict(row)
            # Convert comma-separated tags back to list
            pdf['tags'] = pdf['tags_str'].split(',') if pdf['tags_str'] else []
            del pdf['tags_str']
            result.append(pdf)
        return result

def get_pdf_details(pdf_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a PDF.
    If user_id is provided, includes whether the user liked it.
    """
    with get_db() as conn:
        row = conn.execute("""
            SELECT p.id, p.file_id, p.file_name, p.likes_count, p.downloads_count,
                   GROUP_CONCAT(t.tag) as tags_str
            FROM pdfs p
            LEFT JOIN tags t ON p.id = t.pdf_id
            WHERE p.id = ?
            GROUP BY p.id
        """, (pdf_id,)).fetchone()

        if not row:
            return None

        pdf = dict(row)
        pdf['tags'] = pdf['tags_str'].split(',') if pdf['tags_str'] else []
        del pdf['tags_str']

        if user_id:
            # Check if user liked this PDF
            like = conn.execute(
                "SELECT 1 FROM likes WHERE pdf_id = ? AND user_id = ?",
                (pdf_id, user_id)
            ).fetchone()
            pdf['user_liked'] = bool(like)
        else:
            pdf['user_liked'] = False

        return pdf

def get_pdf_file_id(pdf_id: int) -> Optional[str]:
    """Get Telegram file_id for a PDF."""
    with get_db() as conn:
        row = conn.execute("SELECT file_id FROM pdfs WHERE id = ?", (pdf_id,)).fetchone()
        return row['file_id'] if row else None

def toggle_like(pdf_id: int, user_id: int) -> bool:
    """
    Toggle like status for a user on a PDF.
    Returns True if liked (after toggle), False if unliked.
    Idempotent: multiple calls with same state will not double-count.
    """
    with get_db() as conn:
        # Check if like exists
        existing = conn.execute(
            "SELECT 1 FROM likes WHERE pdf_id = ? AND user_id = ?",
            (pdf_id, user_id)
        ).fetchone()

        if existing:
            # Unlike: delete like and decrement counter
            conn.execute(
                "DELETE FROM likes WHERE pdf_id = ? AND user_id = ?",
                (pdf_id, user_id)
            )
            conn.execute(
                "UPDATE pdfs SET likes_count = likes_count - 1 WHERE id = ?",
                (pdf_id,)
            )
            return False
        else:
            # Like: insert and increment counter
            conn.execute(
                "INSERT INTO likes (pdf_id, user_id) VALUES (?, ?)",
                (pdf_id, user_id)
            )
            conn.execute(
                "UPDATE pdfs SET likes_count = likes_count + 1 WHERE id = ?",
                (pdf_id,)
            )
            return True

def increment_download(pdf_id: int, user_id: int) -> None:
    """
    Record a download and increment download counter.
    To keep it idempotent per user, we use INSERT OR IGNORE.
    Only the first download by a user increments the counter.
    """
    with get_db() as conn:
        # Try to insert download record; if already exists, ignore.
        conn.execute(
            "INSERT OR IGNORE INTO downloads (pdf_id, user_id) VALUES (?, ?)",
            (pdf_id, user_id)
        )
        # Check if this insertion actually happened (changes > 0)
        if conn.total_changes > 0:
            conn.execute(
                "UPDATE pdfs SET downloads_count = downloads_count + 1 WHERE id = ?",
                (pdf_id,)
            )