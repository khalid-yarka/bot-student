# bots/ardayda_bot/handlers.py
"""
All conversation logic and state transitions.
Handles registration, upload, search, and view flows.
"""

import logging
from typing import Dict, Any, List, Optional

from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup

import database as db
import text
import buttons
from bot import bot  # circular import? better to pass bot instance

# Configure logging
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# In-memory temporary storage (cleared on cancel/timeout/completion)
# ----------------------------------------------------------------------

# Active PDF upload sessions: user_id -> dict with file_id, file_name, tags list
pdf_upload_stage: Dict[int, Dict[str, Any]] = {}

# Active search filters: user_id -> list of selected tag strings (e.g., ["subject:phy", "exam:2015"])
search_selected_tags: Dict[int, List[str]] = {}

# Cached search results: user_id -> list of pdf_ids (or dicts)
pdf_search_results: Dict[int, List[Dict[str, Any]]] = {}

# ----------------------------------------------------------------------
# Helper functions to render UI
# ----------------------------------------------------------------------

def show_main_menu(user_id: int):
    """Send main menu keyboard."""
    bot.send_message(
        user_id,
        text.MAIN_MENU,
        reply_markup=buttons.main_menu_keyboard()
    )

def show_tag_selection(user_id: int, purpose: str, selected_tags: List[str]):
    """
    Show tag selection inline keyboard.
    purpose: 'upload' or 'search'
    selected_tags: list of currently selected tag strings
    """
    markup = buttons.tag_selection_keyboard(purpose, selected_tags)
    bot.send_message(
        user_id,
        text.TAG_SELECTION_PROMPT,
        reply_markup=markup
    )

def show_pdf_list(user_id: int, pdfs: List[Dict], page: int = 1, page_size: int = 5):
    """Show paginated list of PDFs."""
    total = len(pdfs)
    start = (page - 1) * page_size
    end = start + page_size
    page_pdfs = pdfs[start:end]

    if not page_pdfs:
        bot.send_message(user_id, text.NO_RESULTS)
        return

    message = text.PDF_LIST_HEADER.format(page=page, total=total)
    for pdf in page_pdfs:
        # pdf should contain: id, title (file_name), tags (list), likes_count
        message += f"\n📄 {pdf.get('file_name', 'Untitled')}"
        message += f"\n   🏷️ {', '.join(pdf.get('tags', []))}"
        message += f"\n   ❤️ {pdf.get('likes_count', 0)} likes\n"

    markup = buttons.pdf_pagination_keyboard(page, total, page_size)
    bot.send_message(user_id, message, reply_markup=markup)

def show_pdf_detail(user_id: int, pdf: Dict[str, Any]):
    """Show details of a single PDF."""
    text_msg = text.PDF_DETAIL.format(
        title=pdf.get('file_name', 'Untitled'),
        tags=', '.join(pdf.get('tags', [])),
        likes=pdf.get('likes_count', 0),
        downloads=pdf.get('downloads_count', 0)
    )
    markup = buttons.pdf_detail_keyboard(pdf['id'], user_liked=pdf.get('user_liked', False))
    bot.send_message(user_id, text_msg, reply_markup=markup)

# ----------------------------------------------------------------------
# Handlers for different message types
# ----------------------------------------------------------------------

def start_handler(bot_instance, message: Message):
    """Handle /start command."""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""

    # Check if user exists
    user = db.get_user(user_id)
    if user:
        # Existing user: show main menu
        db.set_user_status(user_id, "sys.menu.idle")
        show_main_menu(user_id)
    else:
        # New user: start registration
        db.create_user(user_id, username, first_name)
        db.set_user_status(user_id, "auth.register.name")
        bot_instance.send_message(user_id, text.REGISTER_NAME)

def text_message_handler(bot_instance, message: Message):
    """Handle text messages based on current status."""
    user_id = message.from_user.id
    text_input = message.text.strip()
    current_status = db.get_user_status(user_id) or ""

    # Registration flow
    if current_status == "auth.register.name":
        db.update_user(user_id, full_name=text_input)
        db.set_user_status(user_id, "auth.register.region")
        bot_instance.send_message(user_id, text.REGISTER_REGION)

    elif current_status == "auth.register.region":
        db.update_user(user_id, region=text_input)
        db.set_user_status(user_id, "auth.register.school")
        bot_instance.send_message(user_id, text.REGISTER_SCHOOL)

    elif current_status == "auth.register.school":
        db.update_user(user_id, school=text_input)
        db.set_user_status(user_id, "auth.register.class")
        bot_instance.send_message(user_id, text.REGISTER_CLASS)

    elif current_status == "auth.register.class":
        db.update_user(user_id, student_class=text_input)
        db.set_user_status(user_id, "sys.menu.idle")
        bot_instance.send_message(user_id, text.REGISTER_COMPLETE)
        show_main_menu(user_id)

    # Main menu idle: handle menu options
    elif current_status == "sys.menu.idle":
        if text_input == "📤 Upload PDF":
            # Start upload flow
            db.set_user_status(user_id, "upload.pdf.file")
            bot_instance.send_message(user_id, text.UPLOAD_PROMPT)
        elif text_input == "🔍 Search PDFs":
            # Start search flow
            db.set_user_status(user_id, "search.filter.select")
            search_selected_tags[user_id] = []
            show_tag_selection(user_id, "search", [])
        elif text_input == "📚 My Downloads":
            # Show downloaded PDFs (could be implemented)
            bot_instance.send_message(user_id, "Coming soon!")
        else:
            bot_instance.send_message(user_id, text.INVALID_OPTION)

    # Other states: text not expected, ignore or show error
    elif current_status.startswith("upload."):
        bot_instance.send_message(user_id, text.UPLOAD_EXPECT_FILE)
    elif current_status.startswith("search."):
        bot_instance.send_message(user_id, text.SEARCH_USE_BUTTONS)
    elif current_status.startswith("view."):
        bot_instance.send_message(user_id, text.VIEW_USE_BUTTONS)
    else:
        # Unknown status – reset to menu
        db.set_user_status(user_id, "sys.menu.idle")
        show_main_menu(user_id)

def document_handler(bot_instance, message: Message):
    """Handle document uploads (PDF only)."""
    user_id = message.from_user.id
    current_status = db.get_user_status(user_id) or ""

    if current_status != "upload.pdf.file":
        bot_instance.reply_to(message, text.UPLOAD_NOT_EXPECTED)
        return

    # Check if it's a PDF
    document = message.document
    if document.mime_type != "application/pdf":
        bot_instance.reply_to(message, text.UPLOAD_ONLY_PDF)
        return

    # Store file info in temporary session
    pdf_upload_stage[user_id] = {
        "file_id": document.file_id,
        "file_name": document.file_name,
        "tags": []  # will be filled in tag selection
    }

    # Move to tag selection step
    db.set_user_status(user_id, "upload.pdf.tags")
    show_tag_selection(user_id, "upload", [])

def callback_handler(bot_instance, call: CallbackQuery):
    """Handle all callback queries."""
    user_id = call.from_user.id
    data = call.data
    current_status = db.get_user_status(user_id) or ""

    # Answer callback to remove loading indicator
    bot_instance.answer_callback_query(call.id)

    # ------------------------------------------------------------------
    # Upload flow callbacks
    # ------------------------------------------------------------------
    if data.startswith("upload_tag_"):
        if current_status != "upload.pdf.tags":
            bot_instance.send_message(user_id, text.ACTION_NOT_ALLOWED)
            return

        # Format: upload_tag_<tag_string>
        tag = data.replace("upload_tag_", "", 1)
        session = pdf_upload_stage.get(user_id)
        if not session:
            # Session lost – reset to menu
            db.set_user_status(user_id, "sys.menu.idle")
            bot_instance.send_message(user_id, text.SESSION_EXPIRED)
            show_main_menu(user_id)
            return

        # Toggle tag
        if tag in session["tags"]:
            session["tags"].remove(tag)
        else:
            session["tags"].append(tag)

        # Update the inline keyboard (edit the message)
        new_markup = buttons.tag_selection_keyboard("upload", session["tags"])
        bot_instance.edit_message_reply_markup(
            chat_id=user_id,
            message_id=call.message.message_id,
            reply_markup=new_markup
        )

    elif data == "upload_done":
        if current_status != "upload.pdf.tags":
            bot_instance.send_message(user_id, text.ACTION_NOT_ALLOWED)
            return

        session = pdf_upload_stage.get(user_id)
        if not session:
            db.set_user_status(user_id, "sys.menu.idle")
            bot_instance.send_message(user_id, text.SESSION_EXPIRED)
            show_main_menu(user_id)
            return

        # Validate at least one tag
        if not session["tags"]:
            bot_instance.answer_callback_query(call.id, text.TAG_REQUIRED, show_alert=True)
            return

        # Save PDF to database
        pdf_id = db.add_pdf(
            user_id=user_id,
            file_id=session["file_id"],
            file_name=session["file_name"],
            tags=session["tags"]
        )

        # Clear temporary session
        del pdf_upload_stage[user_id]

        # Update status to idle
        db.set_user_status(user_id, "sys.menu.idle")

        # Notify user
        bot_instance.edit_message_text(
            text.UPLOAD_SUCCESS,
            chat_id=user_id,
            message_id=call.message.message_id
        )
        show_main_menu(user_id)

    elif data == "upload_cancel":
        if current_status == "upload.pdf.tags" or current_status == "upload.pdf.file":
            # Clear session
            pdf_upload_stage.pop(user_id, None)
            db.set_user_status(user_id, "sys.menu.idle")
            bot_instance.edit_message_text(
                text.UPLOAD_CANCELLED,
                chat_id=user_id,
                message_id=call.message.message_id
            )
            show_main_menu(user_id)

    # ------------------------------------------------------------------
    # Search flow callbacks
    # ------------------------------------------------------------------
    elif data.startswith("search_tag_"):
        if current_status != "search.filter.select":
            bot_instance.send_message(user_id, text.ACTION_NOT_ALLOWED)
            return

        tag = data.replace("search_tag_", "", 1)
        filters = search_selected_tags.get(user_id, [])

        # Toggle
        if tag in filters:
            filters.remove(tag)
        else:
            filters.append(tag)

        search_selected_tags[user_id] = filters

        # Update keyboard
        new_markup = buttons.tag_selection_keyboard("search", filters)
        bot_instance.edit_message_reply_markup(
            chat_id=user_id,
            message_id=call.message.message_id,
            reply_markup=new_markup
        )

    elif data == "search_apply":
        if current_status != "search.filter.select":
            bot_instance.send_message(user_id, text.ACTION_NOT_ALLOWED)
            return

        filters = search_selected_tags.get(user_id, [])
        if not filters:
            bot_instance.answer_callback_query(call.id, text.SEARCH_REQUIRED_TAG, show_alert=True)
            return

        # Query database
        results = db.get_pdfs_by_multilevel_tags(filters)
        pdf_search_results[user_id] = results

        if not results:
            bot_instance.edit_message_text(
                text.NO_RESULTS,
                chat_id=user_id,
                message_id=call.message.message_id
            )
            # Optionally go back to tag selection or menu
            search_selected_tags.pop(user_id, None)
            db.set_user_status(user_id, "sys.menu.idle")
            show_main_menu(user_id)
            return

        # Set status to results page
        db.set_user_status(user_id, "search.results.page")

        # Show first page
        show_pdf_list(user_id, results, page=1)

        # Delete the tag selection message (optional)
        bot_instance.delete_message(user_id, call.message.message_id)

    elif data == "search_cancel":
        if current_status == "search.filter.select":
            search_selected_tags.pop(user_id, None)
            db.set_user_status(user_id, "sys.menu.idle")
            bot_instance.edit_message_text(
                text.SEARCH_CANCELLED,
                chat_id=user_id,
                message_id=call.message.message_id
            )
            show_main_menu(user_id)

    # ------------------------------------------------------------------
    # Pagination callbacks
    # ------------------------------------------------------------------
    elif data.startswith("page_"):
        if current_status != "search.results.page":
            bot_instance.send_message(user_id, text.ACTION_NOT_ALLOWED)
            return

        parts = data.split("_")
        if len(parts) != 2:
            return
        try:
            page = int(parts[1])
        except ValueError:
            return

        results = pdf_search_results.get(user_id, [])
        if not results:
            # No results cached – maybe reset
            db.set_user_status(user_id, "sys.menu.idle")
            show_main_menu(user_id)
            return

        show_pdf_list(user_id, results, page=page)

    # ------------------------------------------------------------------
    # PDF view callbacks
    # ------------------------------------------------------------------
    elif data.startswith("view_"):
        # Format: view_<pdf_id>
        pdf_id_str = data.replace("view_", "", 1)
        try:
            pdf_id = int(pdf_id_str)
        except ValueError:
            return

        # Fetch PDF details
        pdf = db.get_pdf_details(pdf_id, user_id)
        if not pdf:
            bot_instance.send_message(user_id, text.PDF_NOT_FOUND)
            return

        # Set status to view.pdf.page (though we may not need step granularity)
        db.set_user_status(user_id, "view.pdf.page")

        # Show PDF detail
        show_pdf_detail(user_id, pdf)

    elif data.startswith("like_"):
        pdf_id_str = data.replace("like_", "", 1)
        try:
            pdf_id = int(pdf_id_str)
        except ValueError:
            return

        # Toggle like
        liked = db.toggle_like(pdf_id, user_id)

        # Update the message's like button
        pdf = db.get_pdf_details(pdf_id, user_id)
        if pdf:
            # Edit the message to reflect new like status
            new_markup = buttons.pdf_detail_keyboard(pdf_id, user_liked=liked)
            bot_instance.edit_message_reply_markup(
                chat_id=user_id,
                message_id=call.message.message_id,
                reply_markup=new_markup
            )
            # Optionally update like count text
            # Could also edit full message, but keep simple
            bot_instance.answer_callback_query(call.id, text.LIKE_UPDATED)

    elif data.startswith("download_"):
        pdf_id_str = data.replace("download_", "", 1)
        try:
            pdf_id = int(pdf_id_str)
        except ValueError:
            return

        # Get file_id from database
        file_id = db.get_pdf_file_id(pdf_id)
        if file_id:
            # Increment download count (optional)
            db.increment_download(pdf_id, user_id)
            # Send document
            bot_instance.send_document(user_id, file_id)
        else:
            bot_instance.send_message(user_id, text.PDF_NOT_FOUND)

    # ------------------------------------------------------------------
    # Navigation callbacks
    # ------------------------------------------------------------------
    elif data == "back_to_menu":
        # Clear any temporary data for this user
        pdf_upload_stage.pop(user_id, None)
        search_selected_tags.pop(user_id, None)
        pdf_search_results.pop(user_id, None)

        db.set_user_status(user_id, "sys.menu.idle")
        show_main_menu(user_id)

        # Delete the current message (optional)
        bot_instance.delete_message(user_id, call.message.message_id)

    else:
        # Unknown callback – ignore
        logger.warning(f"Unhandled callback data: {data} from user {user_id}")