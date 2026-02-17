# bots/ardayda_bot/buttons.py
"""
All keyboards and callback data formats.
Defines inline and reply keyboards for the bot.
Callback data encodes intent, not state.
"""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List

# ----------------------------------------------------------------------
# Reply keyboards (main menu)
# ----------------------------------------------------------------------

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu with upload, search, downloads."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📤 Upload PDF"),
        KeyboardButton("🔍 Search PDFs"),
        KeyboardButton("📚 My Downloads")
    )
    return markup

# ----------------------------------------------------------------------
# Tag selection inline keyboards
# ----------------------------------------------------------------------

# Predefined tag structure (can be extended or loaded from config)
SUBJECT_TAGS = [
    "subject:math", "subject:physics", "subject:chemistry",
    "subject:biology", "subject:history", "subject:geography",
    "subject:english", "subject:somali", "subject:arabic",
    "subject:islamic"
]

EXAM_TAGS = ["exam:final", "exam:midterm", "exam:quiz", "exam:assignment"]
YEAR_TAGS = [f"year:{y}" for y in range(2015, 2026)]
CLASS_TAGS = ["class:form1", "class:form2", "class:form3", "class:form4"]

# Group tags by category for better UI (optional, but we can implement a flat list for simplicity)
ALL_TAGS = SUBJECT_TAGS + EXAM_TAGS + YEAR_TAGS + CLASS_TAGS

def tag_selection_keyboard(purpose: str, selected_tags: List[str]) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard for tag selection.
    purpose: 'upload' or 'search' – affects callback data prefix.
    selected_tags: list of currently selected tag strings.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []

    # Add a tag button for each tag in ALL_TAGS
    for tag in ALL_TAGS:
        # Determine emoji: checkmark if selected
        emoji = "✅ " if tag in selected_tags else ""
        callback_data = f"{purpose}_tag_{tag}"
        buttons.append(InlineKeyboardButton(text=f"{emoji}{tag}", callback_data=callback_data))

        # Add to markup in rows of 2
        if len(buttons) == 2:
            markup.row(*buttons)
            buttons = []

    # Add any remaining buttons
    if buttons:
        markup.row(*buttons)

    # Add action buttons: Done/Apply and Cancel
    action_row = []
    if purpose == "upload":
        action_row.append(InlineKeyboardButton("✅ Done", callback_data="upload_done"))
    elif purpose == "search":
        action_row.append(InlineKeyboardButton("🔍 Apply Filters", callback_data="search_apply"))
    action_row.append(InlineKeyboardButton("❌ Cancel", callback_data=f"{purpose}_cancel"))
    markup.row(*action_row)

    return markup

# ----------------------------------------------------------------------
# PDF list pagination keyboard
# ----------------------------------------------------------------------

def pdf_pagination_keyboard(current_page: int, total_items: int, page_size: int = 5) -> InlineKeyboardMarkup:
    """
    Create pagination keyboard for PDF results.
    current_page: 1-indexed page number.
    total_items: total number of PDFs in results.
    page_size: number of items per page.
    """
    markup = InlineKeyboardMarkup(row_width=3)
    total_pages = (total_items + page_size - 1) // page_size

    buttons = []

    # Previous page button
    if current_page > 1:
        buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page_{current_page-1}"))
    else:
        buttons.append(InlineKeyboardButton("◀️", callback_data="noop"))  # disabled look

    # Current page indicator (non-clickable)
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))

    # Next page button
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{current_page+1}"))
    else:
        buttons.append(InlineKeyboardButton("▶️", callback_data="noop"))

    markup.row(*buttons)

    # Back to menu button
    markup.row(InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu"))

    return markup

# ----------------------------------------------------------------------
# PDF detail keyboard
# ----------------------------------------------------------------------

def pdf_detail_keyboard(pdf_id: int, user_liked: bool) -> InlineKeyboardMarkup:
    """
    Keyboard for a single PDF view.
    pdf_id: database ID of the PDF.
    user_liked: whether the current user already liked it.
    """
    markup = InlineKeyboardMarkup(row_width=2)

    # Like button with dynamic text
    like_text = "❤️ Unlike" if user_liked else "🤍 Like"
    markup.add(
        InlineKeyboardButton(like_text, callback_data=f"like_{pdf_id}"),
        InlineKeyboardButton("📥 Download", callback_data=f"download_{pdf_id}")
    )

    # Back to results or menu? We'll provide a back button
    markup.add(InlineKeyboardButton("🔙 Back to Results", callback_data="back_to_results"))

    return markup

# Note: The "back_to_results" callback needs to be handled in handlers.py.
# It should return to the search results page (using cached results).
# If no cache, fallback to menu.

# ----------------------------------------------------------------------
# Utility for no-operation buttons (disabled)
# ----------------------------------------------------------------------

def noop_keyboard() -> InlineKeyboardMarkup:
    """Used for placeholders where no action should occur."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("...", callback_data="noop"))
    return markup